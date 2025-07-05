"""Event schemas for AgentOS using Pydantic models."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel, Field
from .event_registry import register_event_schema
from .event_bus import Event
from modules.agents.agent_config import load_agent_config
from modules.agents.llm_provider import complete

# Core Agent Events

@register_event_schema("agent.think")
async def agent_think(event: Event) -> Dict[str, Any]:
    """Strategic planning and complex reasoning - uses Heavy model"""
    thread_id = event.data.get('thread_id')
    prompt = event.data.get('prompt', 'Analyzing request...')
    
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
    """Parameter completion and simple decisions - uses Ultra-light model
    Params - event:
        event: The name of the event being evaluated
        params: The parameters to pass to the condition
        schema: The schema of the event being evaluated
    Returns - decision: 
        action: 'continue' | 'skip'
        params: the updated params
        reason: 'reason for skipping'
    """
    prompt = event.data.get('prompt', '')
    params = event.data.get('params', {})
    schema = event.data.get('schema', {})
    
    agent_config = load_agent_config('decide')
    response = await complete(
        provider=agent_config['provider'],
        model=agent_config['model'],
        messages=[{"role": "user", "content": prompt}],
        system=agent_config['system_prompt'],
        response_format=agent_config['output_type']
    )
    # Mock: Always continue with provided params
    return {
        "action": "continue",
        "params": params
    }

@register_event_schema("agent.reply")
async def agent_reply(event: Event) -> None:
    """Send message to user"""
    message = event.data.get('message', '')
    thread_id = event.data.get('thread_id')
    
    # Mock: Just print the message
    print(f"[Thread {thread_id}] Agent: {message}")
    return None

# Thread Management Events

@register_event_schema("thread.match")
async def thread_match(event: Event) -> Dict[str, Any]:
    """Determine which thread a message belongs to"""
    message = event.data.get('message', '')
    thread_id = event.data.get('thread_id')
    
    # Mock: Always continue with current thread
    return {
        "action": "continue",
        "thread_id": thread_id or "default_thread"
    }

@register_event_schema("thread.summarize")
async def thread_summarize(event: Event) -> Dict[str, Any]:
    """Update thread summary"""
    thread_id = event.data.get('thread_id')
    
    # Mock: Return a simple summary
    return {
        "summary": f"Thread {thread_id} processed",
        "keywords": ["mock", "summary"]
    }

@register_event_schema("thread.create")
async def thread_create(event: Event) -> Dict[str, Any]:
    """Create a new thread"""
    thread_id = event.data.get('thread_id')
    initial_message = event.data.get('initial_message', '')
    metadata = event.data.get('metadata', {})
    
    # Mock: Create thread and return info
    import uuid
    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    
    return {
        "thread_id": thread_id,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@register_event_schema("thread.created")
async def thread_created(event: Event) -> None:
    """Thread creation event - auto-generated after thread.create"""
    thread_id = event.data.get('thread_id')
    initial_message = event.data.get('initial_message', '')
    
    # Mock: Log thread creation
    print(f"[System] Thread created: {thread_id}")
    return None

@register_event_schema("thread.archived")
async def thread_archived(event: Event) -> None:
    """Thread archival event"""
    thread_id = event.data.get('thread_id')
    reason = event.data.get('reason', 'Completed')
    
    # Mock: Log thread archival
    print(f"[System] Thread archived: {thread_id} - {reason}")
    return None

# Memory Operations

@register_event_schema("memory.append")
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

@register_event_schema("memory.search")
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

@register_event_schema("memory.digest")
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

# Task Management

@register_event_schema("task.schedule")
async def task_schedule(event: Event) -> Dict[str, Any]:
    """Create all types of tasks"""
    task_type = event.data.get('type', 'once')
    at = event.data.get('at')
    action = event.data.get('action', [])
    
    # Mock: Return task ID
    import uuid
    return {
        "task_id": f"task_{uuid.uuid4().hex[:8]}",
        "type": task_type,
        "status": "scheduled"
    }

@register_event_schema("task.register")
async def task_register(event: Event) -> Dict[str, Any]:
    """Hook-based task registration"""
    trigger = event.data.get('trigger', '')
    condition = event.data.get('condition', '')
    action = event.data.get('action', [])
    
    # Mock: Return registration ID
    import uuid
    return {
        "hook_id": f"hook_{uuid.uuid4().hex[:8]}",
        "trigger": trigger,
        "status": "registered"
    }

@register_event_schema("task.list")
async def task_list(event: Event) -> Dict[str, Any]:
    """List tasks"""
    filter_params = event.data.get('filter', {})
    status = event.data.get('status', 'all')
    
    # Mock: Return empty task list
    return {
        "tasks": [
            {"task_id": "task_mock1", "type": "once", "status": status}
        ]
    }

# Tool Events

@register_event_schema("tools.now")
async def tools_now(event: Event) -> Dict[str, Any]:
    """Get current date/time"""
    now = datetime.now(timezone.utc)
    
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.isoformat()
    }

@register_event_schema("tools.date_calc")
async def tools_date_calc(event: Event) -> Dict[str, Any]:
    """Date calculations"""
    from_date = event.data.get('from', datetime.now(timezone.utc))
    add = event.data.get('add')
    subtract = event.data.get('subtract')
    find = event.data.get('find')
    format_type = event.data.get('format')
    
    # Mock: Return current date in requested format
    result_date = datetime.now(timezone.utc)
    
    if format_type == "week_range":
        return {"start": "2024-01-15", "end": "2024-01-21"}
    else:
        return {"date": result_date.strftime("%Y-%m-%d")}

# Communication Events

@register_event_schema("email.search")
async def email_search(event: Event) -> Dict[str, Any]:
    """Search emails"""
    from_addr = event.data.get('from')
    to_addr = event.data.get('to')
    subject = event.data.get('subject')
    query = event.data.get('query')
    
    # Mock: Return empty matches
    return {
        "matches": [
            {
                "id": "email_123",
                "from": from_addr or "mock@example.com",
                "subject": subject or "Mock Email",
                "date": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

@register_event_schema("email.send")
async def email_send(event: Event) -> Dict[str, Any]:
    """Send email"""
    to = event.data.get('to', [])
    subject = event.data.get('subject', '')
    body = event.data.get('body', '')
    
    # Mock: Return success
    return {
        "status": "sent",
        "message_id": "mock_msg_123",
        "recipients": to if isinstance(to, list) else [to]
    }

@register_event_schema("email.received")
async def email_received(event: Event) -> None:
    """Email received trigger"""
    email_id = event.data.get('id')
    from_addr = event.data.get('from')
    subject = event.data.get('subject')
    
    # Mock: Log email receipt
    print(f"[System] Email received: {subject} from {from_addr}")
    return None

# Calendar Events

@register_event_schema("calendar.check")
async def calendar_check(event: Event) -> Dict[str, Any]:
    """Check calendar"""
    date = event.data.get('date', 'today')
    date_range = event.data.get('date_range')
    query = event.data.get('query')
    
    # Mock: Return empty events
    return {
        "events": [
            {
                "id": "cal_123",
                "title": "Mock Meeting",
                "date": datetime.now(timezone.utc).isoformat(),
                "duration": "1h"
            }
        ]
    }

@register_event_schema("calendar.create")
async def calendar_create(event: Event) -> Dict[str, Any]:
    """Create calendar event"""
    event_type = event.data.get('type', 'event')
    title = event.data.get('title', '')
    at = event.data.get('at')
    duration = event.data.get('duration', '1h')
    
    # Mock: Return created event
    import uuid
    return {
        "event_id": f"cal_{uuid.uuid4().hex[:8]}",
        "title": title,
        "type": event_type,
        "status": "created"
    }

@register_event_schema("calendar.availability")
async def calendar_availability(event: Event) -> Dict[str, Any]:
    """Find available time slots"""
    people = event.data.get('people', [])
    date_range = event.data.get('date_range', {})
    duration = event.data.get('duration', '30m')
    
    # Mock: Return available slots
    return {
        "slots": [
            {"start": "2024-01-15T10:00:00Z", "end": "2024-01-15T11:00:00Z"},
            {"start": "2024-01-15T14:00:00Z", "end": "2024-01-15T15:00:00Z"}
        ]
    }

@register_event_schema("calendar.search")
async def calendar_search(event: Event) -> Dict[str, Any]:
    """Search calendar events"""
    team = event.data.get('team')
    person = event.data.get('person')
    date_range = event.data.get('date_range')
    query = event.data.get('query')
    
    # Mock: Return search results
    return {
        "events": [
            {
                "id": "cal_search1",
                "title": f"Team {team} Event" if team else "Personal Event",
                "date": datetime.now(timezone.utc).isoformat(),
                "duration": "1h",
                "type": "meeting"
            }
        ]
    }

# Team/People Events

@register_event_schema("team.members")
async def team_members(event: Event) -> Dict[str, Any]:
    """Get team members"""
    team = event.data.get('team', '')
    
    # Mock: Return team members
    return {
        "members": [
            {"id": "user_1", "name": "Alice", "email": "alice@example.com", "role": "Developer"},
            {"id": "user_2", "name": "Bob", "email": "bob@example.com", "role": "Designer"}
        ]
    }

@register_event_schema("people.info")
async def people_info(event: Event) -> Dict[str, Any]:
    """Get person information"""
    name = event.data.get('name', '')
    
    # Mock: Return person info
    return {
        "id": "user_123",
        "name": name,
        "email": f"{name.lower()}@example.com",
        "preferences": {"timezone": "UTC"}
    }

# Document Events

@register_event_schema("document.create")
async def document_create(event: Event) -> Dict[str, Any]:
    """Create document"""
    doc_type = event.data.get('type', 'document')
    title = event.data.get('title', '')
    content = event.data.get('content', '')
    
    # Mock: Return document info
    import uuid
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    return {
        "document_id": doc_id,
        "url": f"https://docs.example.com/{doc_id}",
        "type": doc_type
    }

@register_event_schema("document.search")
async def document_search(event: Event) -> Dict[str, Any]:
    """Search documents"""
    query = event.data.get('query', '')
    doc_type = event.data.get('type')
    
    # Mock: Return search results
    return {
        "documents": [
            {
                "id": "doc_123",
                "title": f"Document matching: {query}",
                "type": doc_type or "document",
                "url": "https://docs.example.com/doc_123"
            }
        ]
    }

# System Events

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