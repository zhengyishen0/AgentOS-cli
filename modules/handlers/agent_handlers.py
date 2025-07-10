"""Agent-related event handlers for AgentOS."""

import logging
from datetime import datetime, timezone
from openai import OpenAI
import json
from typing import Dict, Any
from modules.eventbus.models import Event
from modules.eventbus.schemas import (
    AgentChainInput, AgentChainOutput, AgentThinkInput, AgentThinkOutput, 
    AgentDecideInput, AgentReplyInput, AgentThreadInput, AgentThreadOutput
)
from modules import eventbus, thread_manager, executor, cli_provider
from pprint import pprint

logger = logging.getLogger(__name__)
client = OpenAI()


@eventbus.register("agent.think", schema=AgentThinkInput)
async def agent_think(event: Event) -> Dict[str, Any]:
    """Strategic planning and complex reasoning - uses Heavy model.
    
    This handler performs high-level reasoning and planning, deciding whether to:
    1. Reply directly to the user (for simple requests)
    2. Create a detailed plan for complex multi-step operations
    """

    # Validate input data
    input_data = AgentThinkInput(**event.data)

    registered_schemas = eventbus.list_schemas(brief=True)

    system_prompt = f"""
You are a strategic planning AI agent. Your role is to analyze user requests and decide the best approach.

For SIMPLE requests that can be answered directly:
- Return: {{"event": "agent.reply", "message": {{"your direct answer"}}}}

For COMPLEX requests requiring multiple steps:
- Return: {{"event": "agent.chain", "message": {{"pseudocode plan in bullet points"}}}}

We have a list of tools you can use. This is their schemas:
{json.dumps(registered_schemas, indent=2)}

IMPORTANT:
- The plan should be clear, step-by-step pseudocode that can be mechanically translated into events.

Examples of complex requests:
- Tasks involving multiple data sources
- Multi-step calculations or transformations  
- Operations requiring coordination between teams/systems
- Time-based scheduling or planning

Keep plans focused and efficient. Use parallel execution where possible.
"""
    
    # Get thread context for full conversation history
    thread = await thread_manager.get_thread(input_data.thread_id)
    
    # Format thread context for the LLM
    thread_context = f"Thread {thread.thread_id}: {thread.summary}"
    if len(thread.events) > 0:
        thread_context += f"\nEvents: {len(thread.events)}"

    message_content = f"""PROMPT: {input_data.prompt}\nTHREAD CONTEXT: {thread_context}"""
    
    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_content}
        ],
        text_format=AgentThinkOutput
    )
    
    output = response.output_parsed.model_dump()
    print('agent.think output:')
    pprint(output)

    # Add event to thread
    think_event = Event(
        name=output['event'],
        data={"input": input_data.prompt},
        result={"message": output['message']},
        status="completed",
        source="agent.think"
    )
    await thread_manager.add_event_to_thread(input_data.thread_id, think_event)

    data = {
        "thread_id": input_data.thread_id,
        "message": output['message']
    }
    
    await eventbus.publish(output['event'], data)


@eventbus.register("agent.chain", schema=AgentChainInput)
async def agent_chain(event: Event) -> Dict[str, Any]:
    """Convert natural language plans to executable event chains - uses Fast model.
    
    This handler mechanically translates pseudocode plans into executable event chains.
    It has full knowledge of available events and their schemas but performs no
    complex reasoning - just pattern matching and translation.
    """

    # Validate input data
    input_data = AgentChainInput(**event.data)

    registered_schemas = eventbus.list_schemas()

    system_prompt = f"""
You are a mechanical translation AI that converts plans into event chains. You have full knowledge of available events and their schemas.

Your task is to:
1. Parse the pseudocode plan
2. Map each step to appropriate events
3. Use parameter interpolation for data flow ({{event.result}} syntax)
4. Group parallel operations in arrays
5. Always append agent.think at the end

Registered tools you can use and their schemas:
{json.dumps(registered_schemas, indent=2)}

Output format: List(Union[Event, List[Event]])
Event: {{"name": "event_name", "data": {{"param": "value"}}, "source": "event_source"}},
Sequential Events: [Event, Event, ...]
Parallel Events: [[Event, Event, ...], [Event, Event, ...], ...]

IMPORTANT RULES:
- No reasoning or interpretation - just mechanical translation
- Use exact event names and parameter structures
- Preserve the plan's intent without optimization
- Support these interpolation patterns:
  - {{event_name.result}} - full result
  - {{event_name.result.field}} - specific field
  - {{event_name.result[0]}} - array access
- You would make tasks parallel if you see multiple tasks in the plan, such as read 10 given url links, or any task that do not depend on each other
- Make sure you use the result from the previous event in the next event if needed

Example translation:
Plan: "1. Get current date\\n2. Add 7 days\\n3. Format as ISO string"
Chain: [
  {{"name": "tools.now", "data": {{}}}},
  {{"name": "tools.date_calc", "data": {{"from": "{{tools.now.result}}", "add": "7 days"}}}},
  {{"name": "tools.format", "data": {{"date": "{{tools.date_calc.result}}", "format": "ISO"}}}},
  {{"name": "agent.think", "data": {{"thread_id": "current"}}}}
]

For parallel operations:
Plan: "Get both marketing and engineering team members"  
Chain: [
  [
    {{"name": "team.members", "data": {{"team": "marketing"}}}},
    {{"name": "team.members", "data": {{"team": "engineering"}}}}
  ],
  {{"name": "agent.think", "data": {{"thread_id": "current"}}}}
]

Example json format output:
{{
  "chain": [
    {{"name": "tools.now", "data": {{}}}},
    [  # parallel execution
      {{"name": "tools.date_calc", "data": {{"from": "tools.now.result", "add": "7 days"}}}},
      {{"name": "tools.format", "data": {{"date": "tools.date_calc.result", "format": "ISO"}}}}
    ],
    {{"name": "agent.think", "data": {{"thread_id": "current"}}}}
  ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"PLAN: {input_data.message}"}
        ],
        response_format={"type": "json_object"}
    )

    data = response.choices[0].message.content
    chain = json.loads(data).get('chain', [])
    
    print('agent.chain output:')
    pprint(chain)

    # Convert chain to proper Event objects, handling nested lists for parallel execution
    def convert_chain_to_events(chain_items):
        """Recursively convert chain items to Event objects, preserving nested list structure."""
        converted_chain = []
        for item in chain_items:
            if isinstance(item, list):
                # This is a parallel execution group - convert each item in the sublist
                parallel_events = [Event(**event) for event in item]
                converted_chain.append(parallel_events)
            else:
                # This is a single event
                converted_chain.append(Event(**item))
        return converted_chain

    chain_events = convert_chain_to_events(chain)

    
    # Execute the chain
    execution_result = await executor.execute_chain(
        chain=chain_events,
        thread_id=input_data.thread_id
    )
    
    # Return the execution result
    return {
        'success': execution_result.success,
        'events': [e.model_dump() for e in execution_result.events],
        'total_execution_time_ms': execution_result.total_execution_time_ms,
        'error': execution_result.error,
        'chain_definition': chain  # Include original chain for reference
    }


@eventbus.register("agent.decide", schema=AgentDecideInput)
async def agent_decide(event: Event) -> Dict[str, Any]:
    """Parameter completion and simple decisions - uses Ultra-light model.
    
    This handler evaluates conditions and completes missing parameters for event chains.
    It's called in two scenarios:
    1. When a 'decide' field is present in an event spec for conditional logic
    2. When parameter validation fails and parameters need completion
    """

    # Validate input data
    input_data = AgentDecideInput(**event.data)

    thread = await thread_manager.get_thread(input_data.thread_id)

    # TODO: Add a "break" option to the action

    system_prompt = """
You are a precise decision-making AI agent. Your role is to analyze event parameters and conditions, then provide clear, well-reasoned decisions in the exact JSON format specified.

Key principles:
- Be thorough in parameter completion
- Evaluate conditions carefully
- Provide clear reasoning for skip decisions
- Always return valid JSON matching the expected schema
- When completing parameters, use sensible defaults or infer from context

INSTRUCTIONS:
You are a decision-making AI agent responsible for parameter completion and conditional logic evaluation.

Your task is to:
1. Analyze the provided context and parameters
2. Complete any missing required parameters based on the schema
3. Evaluate any conditional logic (if present)
4. Decide whether to continue or skip the event if the required parameters can be completed

IMPORTANT:
- If the required parameters can be completed, you must continue the event
- If the required parameters cannot be completed, you must skip the event
- Do not make up parameters that are not in the schema or context

RESPONSE FORMAT:
You must respond with a JSON object containing:
- "action": Either "continue" or "skip"
- "params": The updated/completed parameters (even if unchanged)
- "reason": Explanation for your decision (required if action is "skip")

EXAMPLES:
- If parameters are complete and conditions are met: {"action": "continue", "params": {...}}
- If parameters are missing but can be completed: {"action": "continue", "params": {"completed_param": "value", ...}}
- If conditions are not met: {"action": "skip", "params": {...}, "reason": "Condition not met: ..."}

"""

    # Build a comprehensive message template for decision-making
    message_content = f"""
TASK: {input_data.prompt}
- Event Schema: {input_data.event_schema}
- Current Parameters: {input_data.params}
- Thread Context: {thread}
"""

    response =  client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_content}
        ],
        response_format={"type": "json_object"}
    )

    output = response.choices[0].message.content
    
    # Parse the JSON response
    try:
        parsed_output = json.loads(output)
        return parsed_output
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent.decide response as JSON: {e}")
        logger.error(f"Raw response: {output}")
        # Return a safe fallback
        return {
            "action": "continue",
            "params": input_data.params,
            "reason": "Failed to parse decision response"
        }


@eventbus.register("agent.thread", schema=AgentThreadInput)
async def agent_thread(event: Event) -> Dict[str, Any]:
    """Determine which thread a message belongs to"""
    input_data = AgentThreadInput(**event.data)

    # TODO: Replace with LLM
    # agent.thread (input, thread_id) -> thread_id
    # it will determine if the input belongs to the given thread_id or one of the active threads with confidence level

    output = AgentThreadOutput(
        thread_confidence={
            "thread_id_1": 0.1,
            "thread_id_2": 0.1
        }
    )
    
    return output.model_dump()


@eventbus.register("agent.reply", schema=AgentReplyInput)
async def agent_reply(event: Event) -> None:
    """Send a reply to the user"""
    input_data = AgentReplyInput(**event.data)
    cli_provider.display_output(input_data.message, "agent")