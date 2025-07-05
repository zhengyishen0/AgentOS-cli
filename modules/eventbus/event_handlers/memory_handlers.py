"""Memory operation event handlers for AgentOS."""

from typing import Dict, Any
from ..event_schemas import MemoryAppendInput, MemorySearchInput, MemoryDigestInput
from ..event_bus import Event, eventbus


@eventbus.register("memory.append", schema=MemoryAppendInput)
async def memory_append(event: Event) -> Dict[str, Any]:
    """Add to daily journal with keywords"""
    thread_id = event.data.get('thread_id')
    content = event.data.get('content', '')
    
    # Mock: Extract simple keywords
    keywords = content.lower().split()[:5]  # First 5 words as keywords
    return {
        "status": "appended",
        "keywords": keywords
    }


@eventbus.register("memory.search", schema=MemorySearchInput)
async def memory_search(event: Event) -> Dict[str, Any]:
    """Search across journals/knowledge"""
    query = event.data.get('query', '')
    scope = event.data.get('scope', 'recent')
    search_type = event.data.get('type', 'any')
    
    # Mock: Return empty matches
    return {
        "matches": [
            {"content": f"Mock result for: {query}", "score": 0.8, "type": search_type}
        ]
    }


@eventbus.register("memory.digest", schema=MemoryDigestInput)
async def memory_digest(event: Event) -> Dict[str, Any]:
    """Process journals into organized knowledge"""
    period = event.data.get('period', 'daily')
    
    # Mock: Return processed digest
    return {
        "people": [],
        "projects": [],
        "preferences": [],
        "period": period
    }