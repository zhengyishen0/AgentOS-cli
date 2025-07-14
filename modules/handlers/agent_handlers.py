"""Agent-related event handlers for AgentOS."""

import logging
from openai import OpenAI
import json
from typing import Dict, Any
from modules.eventbus.models import Event
from modules.eventbus.schemas import (
    AgentChainInput, AgentChainOutput, AgentThinkInput, AgentThinkOutput, 
    AgentDecideInput, AgentThreadInput, AgentThreadOutput
)
from modules import eventbus, thread_manager, executor
from modules.cli.provider import get_global_cli_provider
from pprint import pprint


logger = logging.getLogger(__name__)
client = OpenAI()


@eventbus.register("agent.think", schema=AgentThinkInput)
async def agent_think(event: Event) -> Dict[str, Any]:
    """Strategic planning and complex reasoning - uses Heavy model.
    
    This handler performs high-level reasoning and planning, deciding whether to:
    1. Reply directly to the user (for simple requests)
    2. Ask the user to choose from options (for decisions requiring user input)
    3. Create a detailed plan for complex multi-step operations (chain)
    """

    # Validate input data
    input_data = AgentThinkInput(**event.data)
    registered_schemas = eventbus.list_schemas(brief=True)

    # Get thread context for full conversation history
    thread = await thread_manager.get_thread(input_data.thread_id)
    
    if thread is None:
        logger.error(f"Thread {input_data.thread_id} not found")
        cli_provider = get_global_cli_provider()
        if cli_provider:
            cli_provider.console.print(f"[red]Error: Thread {input_data.thread_id} not found. Please try again.[/red]")
        return {
            "event": "reply",
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

    # Handle different action types internally
    cli_provider = get_global_cli_provider()
    
    if output['event'] == 'reply':
        # Direct reply - display immediately
        if cli_provider:
            cli_provider.console.print(f"[green]🤖 Agent:[/green] {output['message']}")
        return output
    elif output['event'] == 'ask':
        # Ask user for choice
        if cli_provider and output.get('options'):
            user_choice = await cli_provider.get_user_choice(output['message'], output['options'])
            if user_choice == "exit":
                cli_provider.console.print("[yellow]Operation cancelled by user[/yellow]")
                return {"event": "reply", "message": "Operation cancelled by user"}
            else:
                # Continue with the chosen option - trigger another agent.think with the choice
                cli_provider.console.print(f"[cyan]You chose: {user_choice}[/cyan]")
                
                # Create a user choice event and add it to the thread
                user_choice_event = Event(
                    name="user.choice",
                    data={
                        "thread_id": input_data.thread_id,
                        "choice": user_choice,
                        "options": output.get('options', []),
                        "context": output.get('context', '')
                    },
                    result={"choice": user_choice},
                    status="completed",
                    source="cli"
                )
                
                # Add the user choice event to the thread
                await thread_manager.add_event_to_thread(input_data.thread_id, user_choice_event)
                
                # Create a new prompt that includes the user's choice and original context
                original_context = output.get('context', '')
                if original_context:
                    choice_prompt = f"User selected: {user_choice}. Context: {original_context}. Please continue with this choice."
                else:
                    choice_prompt = f"User selected: {user_choice}. Please continue with this choice."
                
                # Trigger another agent.think event with the choice context
                await eventbus.publish("agent.think", {
                    "thread_id": input_data.thread_id,
                    "prompt": choice_prompt
                })
                
                return {"event": "reply", "message": f"Processing your choice: {user_choice}"}
        else:
            # Fallback if no options provided
            if cli_provider:
                cli_provider.console.print(f"[green]🤖 Agent:[/green] {output['message']}")
            return {"event": "reply", "message": output['message']}
    elif output['event'] == 'chain':
        # Chain execution - publish the chain event
        data = {
            "thread_id": input_data.thread_id,
            "message": output['message']
        }
        await eventbus.publish("agent.chain", data)
        return output
    else:
        # Unknown event type - fallback to reply
        if cli_provider:
            cli_provider.console.print(f"[green]🤖 Agent:[/green] {output['message']}")
        return {"event": "reply", "message": output['message']}


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
- "event": Either "reply", "chain", or "ask"
- "message": A string containing your response
- "context": String containing a summary of what happened and current state (MANDATORY)
- "options": Array of strings (only required for "ask")

For SIMPLE requests that can be answered directly:
- Return: {{"event": "reply", "message": "your direct answer here", "context": "summary_of_what_happened"}}

For COMPLEX requests requiring multiple steps:
- Return: {{"event": "chain", "message": "step-by-step pseudocode plan", "context": "summary_of_what_happened"}}

For CHOICES requiring user input:
- Return: {{"event": "ask", "message": "question for user", "options": ["option1", "option2", "option3"], "context": "summary_of_what_happened"}}

Available event schemas:
{json.dumps(registered_schemas, indent=2)}

IMPORTANT RULES:
- Always return valid JSON with exactly "event", "message", and "context" fields
- The "message" field must be a string, not an object
- The "context" field is MANDATORY for all responses
- For "ask", include "options" array with 2-5 clear choices
- For "chain", provide clear step-by-step pseudocode that can be mechanically translated
- Keep plans focused and efficient

CONTEXT FIELD (MANDATORY FOR ALL RESPONSES):
The "context" field should contain a structured summary with these sections:
- "Background: what happened before"
- "User: what user said in the input" 
- "Response: what the LLM did/said"
- "Next: what we should do next"

Examples:
- "Background: First interaction. User: Asked about the weather. Response: Provided current conditions. Next: Conversation complete."
- "Background: New conversation. User: Wanted to play a number guessing game. Response: Chose number 7 as the answer and asked them to guess from 3, 7, 9. Next: Wait for user's guess and check if they picked 7."
- "Background: We've been playing a number guessing game, user has guessed 3 times. User: Selected option 7 from the choices. Response: Confirmed they guessed correctly (answer was 7). Next: Continue the number-guess game and ask if they want to play again."
- "Background: User requested data analysis. User: Asked for project approach options. Response: Provided quick, thorough, and balanced choices. User selected 'thorough' approach. Next: Proceed with detailed planning using the thorough approach."

CRITICAL RULES:
1. ALWAYS follow the exact format: "Background: ... User: ... Response: ... Next: ..."
2. Keep each section clear and separate
3. Make the Next section specific and actionable
4. Don't mix information between sections

Use this structured format to provide clear context for the next call.

ALWAYS USE "ask" WHEN:
- Presenting multiple options for user to choose from
- Playing games where user needs to pick from choices
- Asking user to select from a list of alternatives
- Requiring user confirmation or preference
- Any scenario where user must make a selection

Examples of when to use "ask":
- "Choose your preferred option: A, B, or C"
- "Pick a number from these options: 1, 2, 3"
- "Which approach would you like: quick, thorough, or balanced?"
- "Select your favorite color: red, blue, green"
- Games requiring user choice or selection

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
- Group independent tasks in parallel arrays: [[event1, event2], event3]
- Always end chains with agent.think

EXAMPLES:

Simple chain:
{{
  "chain": [
    {{"name": "agent.think", "data": {{"thread_id": "current", "prompt": "say hello"}}}}
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
