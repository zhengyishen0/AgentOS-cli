"""System event handlers for AgentOS."""

from typing import Dict, Any
from ..event_registry import register_event_schema
from ..event_bus import Event


@register_event_schema("user.input")
async def user_input(event: Event) -> None:
    """User input received"""
    message = event.data.get('message', '')
    thread_id = event.data.get('thread_id')
    
    # Mock: Log user input
    print(f"[User] {message}")
    return None


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