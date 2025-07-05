"""Agent-related event handlers for AgentOS."""

from typing import Dict, Any, Literal, Optional
from pydantic import BaseModel, Field
from ..event_registry import register_event_schema
from ..event_bus import Event
from modules.agents.agent_config import load_agent_config
from modules.agents.llm_provider import complete
from modules.eventbus.thread_manager import get_thread


class AgentDecideResponse(BaseModel):
    """Output from agent.decide event."""
    action: Literal["continue", "skip"] = Field(description="Whether to continue or skip the event")
    params: Dict[str, Any] = Field(description="The updated/completed parameters")
    reason: Optional[str] = Field(default=None, description="Reason for skipping (if action is skip)")


@register_event_schema("agent.think")
async def agent_think(event: Event) -> Dict[str, Any]:
    """Strategic planning and complex reasoning - uses Heavy model"""
    thread_id = event.data.get('thread_id')
    prompt = event.data.get('prompt', 'Analyzing request...')

    thread = await get_thread(thread_id)
    
    # Mock: Return a simple reply for now
    return {
        "event": "agent.reply",
        "params": {"message": f"Thought about: {prompt}"}
    }


@register_event_schema("agent.chain")
async def agent_chain(event: Event) -> Dict[str, Any]:
    """Convert natural language plans to executable event chains - uses Fast model"""
    plan = event.data.get('plan', '')
    
    # Mock: Return a simple chain
    return {
        "chain": [
            {"event": "tools.now", "params": {}},
            {"event": "agent.reply", "params": {"message": "Chain executed"}}
        ]
    }


@register_event_schema("agent.decide")
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
- If parameters are complete and conditions are met: {{"action": "continue", "params": {{...}}}}
- If parameters are missing but can be completed: {{"action": "continue", "params": {{"completed_param": "value", ...}}}}
- If conditions are not met: {{"action": "skip", "params": {{...}}, "reason": "Condition not met: ..."}}

"""

    schema = event.data.get('schema', {})
    prompt = event.data.get('prompt', '')
    params = event.data.get('params', {})

    # Build a comprehensive message template for decision-making
    message_content = f"""
TASK: {prompt}
- Event Schema: {schema}
- Current Parameters: {params}
"""

    response = await complete(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message_content}],
        system=system_prompt,
        response_format=AgentDecideResponse
    )
    
    return response
