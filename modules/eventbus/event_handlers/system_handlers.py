"""System event handlers for AgentOS."""

from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field
from ..event_registry import register_event_schema
from ..event_bus import Event


class UserInputInput(BaseModel):
    """Input schema for user.input event."""
    text: str = Field(description="User input text")


@register_event_schema("user.input", input_model=UserInputInput)
async def user_input(event: Event) -> Dict[str, Any]:
    """User input received"""
    # Validate input data
    input_data = UserInputInput(**event.data)
    
    # Return processed user input with metadata
    return {
        "text": input_data.text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "length": len(input_data.text),
        "processed": True
    }


@register_event_schema("user.notify")
async def user_notify(event: Event) -> None:
    """Send notification to user"""
    message = event.data.get('message', '')
    notify_type = event.data.get('type', 'info')
    
    # Mock: Print notification
    print(f"[{notify_type.upper()}] {message}")
    return None


@register_event_schema("web.search")
async def web_search(event: Event) -> Dict[str, Any]:
    """Search the web"""
    query = event.data.get('query', '')
    
    # Mock: Return search results
    return {
        "results": [
            {
                "title": f"Result for: {query}",
                "url": "https://example.com/result",
                "snippet": "This is a mock search result"
            }
        ]
    }