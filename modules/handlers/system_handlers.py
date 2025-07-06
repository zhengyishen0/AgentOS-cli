"""System event handlers for AgentOS."""

from datetime import datetime, timezone
from typing import Dict, Any
from ..eventbus.event_schemas import UserInputInput, UserNotifyInput, WebSearchInput
from ..eventbus.event_bus import Event, eventbus
from ..providers.cli_provider import CLIProvider


@eventbus.register("user.input", schema=UserInputInput)
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


@eventbus.register("user.notify", schema=UserNotifyInput)
async def user_notify(event: Event) -> None:
    """Send notification to user"""
    message = event.data.get('message', '')
    notify_type = event.data.get('type', 'info')
    
    # Use CLI provider for notifications
    cli_provider = CLIProvider()
    cli_provider.display_output(message, notify_type)
    return None


@eventbus.register("web.search", schema=WebSearchInput)
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