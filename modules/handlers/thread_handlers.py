"""Thread management event handlers for AgentOS."""

from datetime import datetime, timezone
from typing import Dict, Any
import uuid
from modules.eventbus.schemas import ThreadMatchInput, ThreadSummarizeInput, ThreadCreateInput, ThreadArchivedInput, AgentThreadOutput
from modules.eventbus import Event
from modules import eventbus, thread_manager


# TODO: might be better to merge this with agent.thread
@eventbus.register("thread.match", schema=ThreadMatchInput)
async def thread_match(event: Event) -> Dict[str, Any]:
    """Determine which thread a message belongs to"""

    # Validate input data
    confidence_threshold = 0.5
    input_data = ThreadMatchInput(**event.data)
    thread_data = await thread_manager.thread_summary()
    
    thread_model = await eventbus.publish(
        "agent.thread",
        {"input": input_data.input, "thread_data": thread_data}
    )

    # Access the thread_confidence attribute directly
    thread_confidence = thread_model.thread_confidence
    
    if input_data.thread_id and thread_confidence.get(input_data.thread_id, 0) > confidence_threshold:
        # Continue in the existing thread
        thread_id = input_data.thread_id
    else:
        # Find the thread with highest confidence
        max_confidence = 0
        best_thread_id = None
        
        for _thread_id, confidence in thread_confidence.items():
            if confidence > max_confidence:
                max_confidence = confidence
                best_thread_id = _thread_id
        
        if best_thread_id and max_confidence > confidence_threshold:
            # Switch to the thread with highest confidence
            thread_id = best_thread_id
        else:
            # Create a new thread if no good match found
            new_thread = await thread_manager.create_thread(summary=f"New Thread")
            thread_id = new_thread.thread_id
    
    # Add event to thread
    await thread_manager.add_event_to_thread(thread_id, Event(
        type="agent.think",
        data={"thread_id": thread_id, "prompt": input_data.input},
        result={"thread_id": thread_id, "prompt": input_data.input},
        status="completed",
        source="thread_handler"
    ))
    
    # Publish the event
    await eventbus.publish("agent.think", {"thread_id": thread_id, "prompt": input_data.input})


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