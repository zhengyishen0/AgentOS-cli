"""Agent-related event handlers for AgentOS."""

from typing import Dict, Any
from ..event_schemas import (
    AgentChainInput, AgentThinkInput, AgentDecideInput,
    AgentChainOutput, AgentThinkOutput, AgentDecideOutput
)
from ..event_bus import Event, eventbus
from modules.agents.llm_provider import complete
from modules.eventbus.thread_manager import ThreadManager


@eventbus.register("agent.chain", schema=AgentChainInput)
async def agent_chain(event: Event) -> Dict[str, Any]:
    """Convert natural language plans to executable event chains - uses Fast model.
    
    This handler mechanically translates pseudocode plans into executable event chains.
    It has full knowledge of available events and their schemas but performs no
    complex reasoning - just pattern matching and translation.
    
    Args:
        event: Event containing:
            - plan: The pseudocode plan to convert into an event chain
        
    Returns:
        AgentChainOutput as dict with chain of events to execute
    """

    # Validate input data
    input_data = AgentChainInput(**event.data)

    system_prompt = """
You are a mechanical translation AI that converts plans into event chains. You have full knowledge of available events and their schemas.

Your task is to:
1. Parse the pseudocode plan
2. Map each step to appropriate events
3. Use parameter interpolation for data flow ({event.result} syntax)
4. Group parallel operations in arrays
5. Always append agent.think at the end

IMPORTANT RULES:
- No reasoning or interpretation - just mechanical translation
- Use exact event names and parameter structures
- Preserve the plan's intent without optimization
- Support these interpolation patterns:
  - {event_name.result} - full result
  - {event_name.result.field} - specific field
  - {event_name.result[0]} - array access

Example translation:
Plan: "1. Get current date\n2. Add 7 days\n3. Format as ISO string"
Chain: [
  {"event": "tools.now", "params": {}},
  {"event": "tools.date_calc", "params": {"from": "{tools.now.result}", "add": "7 days"}},
  {"event": "tools.format", "params": {"date": "{tools.date_calc.result}", "format": "ISO"}},
  {"event": "agent.think", "params": {"thread_id": "current"}}
]

For parallel operations:
Plan: "Get both marketing and engineering team members"  
Chain: [
  [
    {"event": "team.members", "params": {"team": "marketing"}},
    {"event": "team.members", "params": {"team": "engineering"}}
  ],
  {"event": "agent.think", "params": {"thread_id": "current"}}
]
"""

    response = await complete(
        provider="openai",
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": f"PLAN: {input_data.plan}"}],
        system=system_prompt,
        response_format=AgentChainOutput
    )
    
    return response


@eventbus.register("agent.think", schema=AgentThinkInput)
async def agent_think(event: Event) -> Dict[str, Any]:
    """Strategic planning and complex reasoning - uses Heavy model.
    
    This handler performs high-level reasoning and planning, deciding whether to:
    1. Reply directly to the user (for simple requests)
    2. Create a detailed plan for complex multi-step operations
    
    Args:
        event: Event containing:
            - thread_id: The thread context identifier
            - prompt: Specific prompt for mid-chain reasoning
        
    Returns:
        AgentThinkOutput as dict with next event and params
    """

    # Validate input data
    input_data = AgentThinkInput(**event.data)

    system_prompt = """
You are a strategic planning AI agent. Your role is to analyze user requests and decide the best approach.

For SIMPLE requests that can be answered directly:
- Return: {"event": "agent.reply", "params": {"message": "your direct answer"}}

For COMPLEX requests requiring multiple steps:
- Return: {"event": "agent.chain", "params": {"plan": "detailed pseudocode plan"}}

The plan should be clear, step-by-step pseudocode that can be mechanically translated into events.

Examples of complex requests:
- Tasks involving multiple data sources
- Multi-step calculations or transformations  
- Operations requiring coordination between teams/systems
- Time-based scheduling or planning

Keep plans focused and efficient. Use parallel execution where possible.
"""
    
    # Get thread context for full conversation history
    thread_manager = ThreadManager()
    thread = await thread_manager.get_thread(input_data.thread_id)
    
    # Format thread context for the LLM
    if thread:
        thread_context = f"Thread {thread.thread_id}: {thread.summary}\nEvents: {len(thread.events)}"
    else:
        thread_context = f"New thread {input_data.thread_id}"

    message_content = f"""{thread_context}\nPROMPT: {input_data.prompt}"""
    
    response = await complete(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message_content}],
        system=system_prompt,
        response_format=AgentThinkOutput
    )
    
    return response


@eventbus.register("agent.decide", schema=AgentDecideInput)
async def agent_decide(event: Event) -> Dict[str, Any]:
    """Parameter completion and simple decisions - uses Ultra-light model.
    
    This handler evaluates conditions and completes missing parameters for event chains.
    It's called in two scenarios:
    1. When a 'decide' field is present in an event spec for conditional logic
    2. When parameter validation fails and parameters need completion
    
    Args:
        event: Event containing:
            - schema: The schema of the event being evaluated
            - prompt: The prompt for the decision
            - params: The parameters to pass to the condition
        
    Returns:
        AgentDecideOutput as dict with action, params, and optional reason
    """

    # Validate input data
    input_data = AgentDecideInput(**event.data)

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
4. Decide whether to continue or skip the event

RESPONSE FORMAT:
You must respond with a JSON object containing:
- "action": Either "continue" or "skip"
- "params": The updated/completed parameters (even if unchanged)
- "reason": Optional explanation for your decision (required if action is "skip")

EXAMPLES:
- If parameters are complete and conditions are met: {"action": "continue", "params": {...}}
- If parameters are missing but can be completed: {"action": "continue", "params": {"completed_param": "value", ...}}
- If conditions are not met: {"action": "skip", "params": {...}, "reason": "Condition not met: ..."}

"""

    # Build a comprehensive message template for decision-making
    message_content = f"""
TASK: {input_data.prompt}
- Event Schema: {input_data.schema}
- Current Parameters: {input_data.params}
"""

    response = await complete(
        provider="openai",
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": message_content}],
        system=system_prompt,
        response_format=AgentDecideOutput
    )
    
    return response