"""System event handlers for AgentOS."""

from datetime import datetime, timezone
from typing import Dict, Any
from ..eventbus.event_schemas import UserInputInput, UserNotifyInput, WebSearchInput
from ..eventbus.event_bus import Event, eventbus
from ..providers.cli_provider import CLIProvider


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