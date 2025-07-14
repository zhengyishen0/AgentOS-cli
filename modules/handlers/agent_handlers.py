"""Agent-related event handlers for AgentOS."""

import logging
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

    # Get thread context for full conversation history
    thread = await thread_manager.get_thread(input_data.thread_id)
    
    if thread is None:
        logger.error(f"Thread {input_data.thread_id} not found")
        return {
            "event": "agent.reply",
            "message": f"Error: Thread {input_data.thread_id} not found. Please try again."
        }

    thread_context = f"Thread [{thread.thread_id}] {thread.title}: {thread.summary}"
    if len(thread.events) > 0:
        thread_context += f"\nEvents: {len(thread.events)}"

    message_content = f"""PROMPT: {input_data.prompt}\nTHREAD CONTEXT: {thread_context}"""
    
    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {"role": "system", "content": agent_think_instruction(registered_schemas)},
            {"role": "user", "content": message_content}
        ],
        text_format=AgentThinkOutput
    )
    
    output = response.output_parsed.model_dump()
    print('\nagent.think output:')
    pprint(output)
    print('\n\n')

    data = {
        "thread_id": input_data.thread_id,
        "message": output['message']
    }
    
    print(f"data: {data}")
    await eventbus.publish(output['event'], data)

    return output


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

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": agent_chain_instruction(registered_schemas)},
            {"role": "user", "content": f"PLAN: {input_data.message}"}
        ],
        response_format={"type": "json_object"}
    )

    data = response.choices[0].message.content
    chain = json.loads(data).get('chain', [])
    chain_events = _convert_chain_to_events(chain)

    print('\nagent.chain output:')
    pprint(chain_events)
    print('\n\n')

    # Execute the chain
    execution_result = await executor.execute_chain(
        chain=chain_events,
        thread_id=input_data.thread_id
    )
    
    # Return the execution result
    return {
        'success': execution_result.success,
        'events': [e.model_dump(mode='json') for e in execution_result.events],
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
    
    # Validate all dependencies and return them or an error response
    result = await _validate_and_get_dependencies(input_data)
    if "action" in result:  # Error case
        return result
    
    thread, event_schema = result["thread"], result["event_schema"]

    message_content = f"""
TASK: {input_data.prompt}
- Event Schema: {json.dumps(event_schema.model_json_schema(), indent=2)}
- Current Parameters: {input_data.params}
- Thread Context: {thread}
"""

    response =  client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": agent_decide_instruction()},
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


# Helper functions

def _convert_chain_to_events(chain_items):
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

async def _validate_and_get_dependencies(input_data: AgentDecideInput) -> Dict[str, Any]:
    """Validate all dependencies and return them or an error response.
    
    Returns:
        Either an error dict with "action", "params", "reason" keys,
        or a success dict with "thread" and "event_schema" keys.
    """
    # Check thread
    thread = await thread_manager.get_thread(input_data.thread_id)
    if thread is None:
        logger.error(f"agent.decide: Thread {input_data.thread_id} not found")
        return {
            "action": "skip",
            "params": input_data.params,
            "reason": f"Thread {input_data.thread_id} not found"
        }
    
    # Check event schema
    event_schema = eventbus.get_schema(input_data.event_name)
    if event_schema is None:
        logger.error(f"agent.decide: Event schema {input_data.event_name} not found")
        return {
            "action": "skip",
            "params": input_data.params,
            "reason": f"Event schema {input_data.event_name} not found"
        }
    
    # Success case - return the dependencies
    return {"thread": thread, "event_schema": event_schema}


# Agent instructions

def agent_think_instruction(registered_schemas: Dict[str, Any]) -> str:
    return f"""
You are a strategic planning AI agent. Your role is to analyze user requests and decide the best approach.

RESPONSE FORMAT:
You must respond with a JSON object containing exactly these fields:
- "event": Either "agent.reply" or "agent.chain"
- "message": A string containing your response

For SIMPLE requests that can be answered directly:
- Return: {{"event": "agent.reply", "message": "your direct answer here"}}

For COMPLEX requests requiring multiple steps:
- Return: {{"event": "agent.chain", "message": "step-by-step pseudocode plan"}}

Available event schemas:
{json.dumps(registered_schemas, indent=2)}

IMPORTANT RULES:
- Always return valid JSON with exactly "event" and "message" fields
- The "message" field must be a string, not an object
- For agent.chain, provide clear step-by-step pseudocode that can be mechanically translated
- Keep plans focused and efficient

Examples of complex requests:
- Tasks involving multiple data sources
- Multi-step calculations or transformations  
- Operations requiring coordination between teams/systems
- Time-based scheduling or planning
"""

def agent_chain_instruction(registered_schemas: Dict[str, Any]) -> str:
    return f"""
You are a mechanical translation AI that converts plans into event chains. You have full knowledge of available events and their schemas.

RESPONSE FORMAT:
You must respond with a JSON object containing exactly this field:
- "chain": An array of events or parallel event arrays

Your task is to:
1. Parse the pseudocode plan
2. Map each step to appropriate events
3. Use parameter interpolation for data flow
4. Group parallel operations in arrays
5. Always append agent.think at the end

Available event schemas:
{json.dumps(registered_schemas, indent=2)}

EVENT FORMAT:
Each event must have exactly these fields:
- "name": The event name (e.g., "agent.think", "agent.reply")
- "data": Object containing event parameters

PARAMETER INTERPOLATION:
Use these patterns to reference previous event results:
- {{event_name.result}} - full result object
- {{event_name.result.message}} - specific field from result
- {{event_name.result[0]}} - array access

IMPORTANT RULES:
- No reasoning or interpretation - just mechanical translation
- Use exact event names and parameter structures from schemas
- Always use "thread_id": "current" for thread context
- For agent.reply events, use {{event_name.result.message}} to get the message string
- Group independent tasks in parallel arrays: [[event1, event2], event3]
- Always end chains with agent.think

EXAMPLES:

Simple chain:
{{
  "chain": [
    {{"name": "agent.think", "data": {{"thread_id": "current", "prompt": "say hello"}}}},
    {{"name": "agent.reply", "data": {{"thread_id": "current", "message": "{{agent.think.result.message}}"}}}}
  ]
}}

Chain with parameter flow:
{{
  "chain": [
    {{"name": "tools.now", "data": {{}}}},
    {{"name": "tools.date_calc", "data": {{"from": "{{tools.now.result}}", "add": "7 days"}}}},
    {{"name": "agent.think", "data": {{"thread_id": "current"}}}}
  ]
}}

Parallel operations:
{{
  "chain": [
    [
      {{"name": "team.members", "data": {{"team": "marketing"}}}},
      {{"name": "team.members", "data": {{"team": "engineering"}}}}
    ],
    {{"name": "agent.think", "data": {{"thread_id": "current"}}}}
  ]
}}
"""

def agent_decide_instruction() -> str:
    return f"""
You are a precise decision-making AI agent. Your role is to analyze event parameters and conditions, then provide clear, well-reasoned decisions in the exact JSON format specified.

RESPONSE FORMAT:
You must respond with a JSON object containing exactly these fields:
- "action": Either "continue" or "skip"
- "params": Object containing the updated/completed parameters
- "reason": String explanation (required if action is "skip")

Your task is to:
1. Analyze the provided context and parameters
2. Complete any missing required parameters based on the schema
3. Evaluate any conditional logic (if present)
4. Decide whether to continue or skip the event

IMPORTANT RULES:
- If required parameters can be completed, return "continue"
- If required parameters cannot be completed, return "skip"
- Do not make up parameters that are not in the schema or context
- Always return valid JSON with exactly the specified fields

EXAMPLES:

Parameters complete:
{{
  "action": "continue",
  "params": {{"thread_id": "thread_123", "message": "Hello world"}}
}}

Parameters missing but can be completed:
{{
  "action": "continue", 
  "params": {{"thread_id": "thread_123", "message": "Default message"}}
}}

Conditions not met:
{{
  "action": "skip",
  "params": {{"thread_id": "thread_123"}},
  "reason": "Required field 'message' cannot be determined from context"
}}
"""
