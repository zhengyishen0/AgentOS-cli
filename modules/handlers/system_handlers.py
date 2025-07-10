"""System event handlers for AgentOS."""

from datetime import datetime, timezone
from typing import Dict, Any
from modules.eventbus.schemas import WebSearchInput, WebFetchInput
from modules.eventbus import Event
from modules import eventbus


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

@eventbus.register("web.fetch", schema=WebFetchInput)
async def web_fetch(event: Event) -> Dict[str, Any]:
    """Fetch a web page"""
    url = event.data.get('url', '')
    
    # Mock: Return fetched page
    return {
        "content": f"Content of {url}"
    }