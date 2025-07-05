"""Thread management event handlers for AgentOS."""

from datetime import datetime, timezone
from typing import Dict, Any
import uuid
from ..event_schemas import ThreadMatchInput, ThreadSummarizeInput, ThreadCreateInput, ThreadArchivedInput
from ..event_bus import Event, eventbus
from ..thread_manager import ThreadManager


@eventbus.register("thread.match", schema=ThreadMatchInput)
async def thread_match(event: Event) -> Dict[str, Any]:
    """Determine which thread a message belongs to"""
    # Validate input data
    input_data = ThreadMatchInput(**event.data)
    
    thread_manager = ThreadManager()
    
    # Search for existing threads that match the input
    threads = await thread_manager.search_threads(input_data.input)
    
    if threads:
        # Found matching thread - return the most relevant one
        best_match = threads[0]
        return {
            "action": "continue",
            "thread_id": best_match.id,
            "confidence": 0.8,
            "summary": best_match.summary
        }
    else:
        # No matching thread found - create a new one
        new_thread = await thread_manager.create_thread(
            summary=f"Discussion about: {input_data.input[:50]}..."
        )
        return {
            "action": "new",
            "thread_id": new_thread.id,
            "confidence": 1.0,
            "summary": new_thread.summary
        }


@eventbus.register("thread.summarize", schema=ThreadSummarizeInput)
async def thread_summarize(event: Event) -> Dict[str, Any]:
    """Update thread summary"""
    thread_id = event.data.get('thread_id')
    
    # Mock: Return a simple summary
    return {
        "summary": f"Thread {thread_id} processed",
        "keywords": ["mock", "summary"]
    }


@eventbus.register("thread.create", schema=ThreadCreateInput)
async def thread_create(event: Event) -> Dict[str, Any]:
    """Create a new thread"""
    thread_id = event.data.get('thread_id')
    initial_message = event.data.get('initial_message', '')
    metadata = event.data.get('metadata', {})
    
    # Mock: Create thread and return info
    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    
    return {
        "thread_id": thread_id,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


@eventbus.register("thread.archived", schema=ThreadArchivedInput)
async def thread_archived(event: Event) -> None:
    """Thread archival event"""
    thread_id = event.data.get('thread_id')
    reason = event.data.get('reason', 'Completed')
    
    # Mock: Log thread archival
    print(f"[System] Thread archived: {thread_id} - {reason}")
    return None