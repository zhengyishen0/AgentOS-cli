# AgentOS EventBus Event Specification

## Event Naming Convention
- Format: `{domain}.{action}`
- Examples: `user.message`, `memory.stored`, `calendar.event_created`

## Event Flow Patterns
- **Request/Response**: `calendar.query` → `calendar.query_result`
- **Action/Confirmation**: `task.create` → `task.created`
- **Broadcast**: `thread.updated` (multiple agents might care)

## Core Event Categories

### 1. User Interaction Events

```python
# User inputs
"user.message"                  # User sent a message
{
    "content": str,            # What user said
    "thread_id": str,          # Current conversation
    "timestamp": datetime,
    "mode": "text|voice"       # Input mode
}

"user.command"                 # User issued a CLI command
{
    "command": str,            # e.g., "memory search"
    "args": list,
    "kwargs": dict
}

"user.feedback"                # User provided feedback
{
    "message_id": str,
    "feedback": "positive|negative|correction",
    "content": str             # Optional correction
}

"user.interrupt"               # User interrupted agent
{
    "reason": str,
    "thread_id": str
}
```

### 2. Thread/Conversation Events

```python
"thread.created"               # New conversation started
{
    "thread_id": str,
    "title": str,              # Auto-generated or user-provided
    "metadata": dict
}

"thread.message_added"         # Message added to thread
{
    "thread_id": str,
    "message": Message,
    "role": "user|assistant|system"
}

"thread.context_requested"     # Agent needs thread context
{
    "thread_id": str,
    "max_tokens": int,
    "requesting_agent": str
}

"thread.completed"             # Conversation ended
{
    "thread_id": str,
    "summary": str,
    "duration": int
}

"thread.switched"              # User switched threads
{
    "from_thread_id": str,
    "to_thread_id": str
}
```

### 3. Routing Events

```python
"router.classify"              # Router analyzing message
{
    "message": str,
    "thread_id": str
}

"router.classified"            # Classification complete
{
    "intent": str,             # "calendar_query", "memory_search", etc.
    "confidence": float,
    "entities": dict,          # Extracted entities
    "suggested_agent": str
}

"router.delegate"              # Delegating to specific agent
{
    "to_agent": str,
    "reason": str,
    "context": dict
}

"router.no_handler"            # No agent can handle this
{
    "message": str,
    "attempted_classification": str
}
```

### 4. Memory Events

```python
"memory.store"                 # Store information
{
    "type": "fact|event|preference|relationship",
    "content": str,
    "entities": list,          # People, places, things mentioned
    "source_thread_id": str,
    "timestamp": datetime
}

"memory.stored"                # Confirmation of storage
{
    "memory_id": str,
    "location": str,           # File path
}

"memory.search"                # Search request
{
    "query": str,
    "filters": dict,           # type, date range, entities
    "max_results": int
}

"memory.search_results"        # Search results
{
    "query": str,
    "results": list,           # List of memories
    "total_count": int
}

"memory.extract_knowledge"     # Extract from conversation
{
    "thread_id": str,
    "focus": list              # ["tasks", "facts", "people"]
}

"memory.knowledge_extracted"   # Extraction complete
{
    "facts": list,
    "tasks": list,
    "relationships": list,
    "questions": list          # Things to follow up on
}

"memory.update"                # Update existing memory
{
    "memory_id": str,
    "updates": dict
}

"memory.delete"                # Delete memory
{
    "memory_id": str,
    "reason": str
}
```

### 5. Task Events

```python
"task.identified"              # Task spotted in conversation
{
    "description": str,
    "due_date": datetime,
    "priority": str,
    "mentioned_by": str,
    "context": str
}

"task.create"                  # Create task
{
    "title": str,
    "description": str,
    "due_date": datetime,
    "assigned_to": str,
    "tags": list
}

"task.created"                 # Task created confirmation
{
    "task_id": str,
    "title": str
}

"task.update"                  # Update task
{
    "task_id": str,
    "updates": dict
}

"task.complete"                # Mark task done
{
    "task_id": str,
    "completed_by": str,
    "notes": str
}

"task.reminder"                # Task reminder triggered
{
    "task_id": str,
    "task": dict,
    "reminder_type": "due|overdue|followup"
}

"task.query"                   # Query tasks
{
    "filter": dict,            # status, assignee, date range
    "sort": str
}

"task.query_results"           # Task query results
{
    "tasks": list,
    "count": int
}
```

### 6. Calendar Events

```python
"calendar.query"               # Request calendar info
{
    "date_range": dict,        # start, end
    "calendar_ids": list,      # Which calendars
    "query": str               # Natural language query
}

"calendar.query_results"       # Calendar results
{
    "events": list,
    "summary": str,            # Human-readable summary
}

"calendar.create_event"        # Create calendar event
{
    "title": str,
    "start": datetime,
    "end": datetime,
    "attendees": list,
    "location": str,
    "description": str
}

"calendar.event_created"       # Event created
{
    "event_id": str,
    "calendar_id": str,
    "link": str
}

"calendar.update_event"        # Update event
{
    "event_id": str,
    "updates": dict
}

"calendar.delete_event"        # Delete event
{
    "event_id": str,
    "reason": str
}

"calendar.availability_check"  # Check free/busy
{
    "participants": list,
    "duration": int,           # minutes
    "date_range": dict
}

"calendar.availability_results"
{
    "slots": list,             # Available time slots
}
```

### 7. LLM Events

```python
"llm.process"                  # Send to LLM
{
    "prompt": str,
    "thread_context": str,
    "model_preference": str,   # "local", "powerful", "auto"
    "max_tokens": int,
    "temperature": float
}

"llm.response"                 # LLM response
{
    "content": str,
    "model_used": str,
    "tokens_used": dict,       # input, output
    "cost": float
}

"llm.error"                    # LLM error
{
    "error": str,
    "model": str,
    "fallback_available": bool
}

"llm.switch_model"             # Switch between local/cloud
{
    "from_model": str,
    "to_model": str,
    "reason": str              # "complexity", "cost", "error"
}
```

### 8. Pattern Recognition Events

```python
"pattern.detected"             # Pattern found
{
    "pattern_type": str,       # "behavior", "schedule", "preference"
    "description": str,
    "confidence": float,
    "occurrences": list
}

"pattern.suggest_automation"   # Suggest automation
{
    "pattern_id": str,
    "suggestion": str,
    "trigger": dict,           # When to run
    "action": dict             # What to do
}

"pattern.automation_response"  # User response to suggestion
{
    "pattern_id": str,
    "accepted": bool,
    "modifications": dict      # User's changes
}

"pattern.automation_created"   # Automation created
{
    "automation_id": str,
    "trigger": dict,
    "action": dict,
    "enabled": bool
}
```

### 9. Integration Events (MCP)

```python
"mcp.connect"                  # Connect to MCP server
{
    "server_type": str,        # "google_calendar", "notion", etc.
    "config": dict
}

"mcp.connected"                # Connection established
{
    "server_type": str,
    "capabilities": list,      # What this server can do
    "status": str
}

"mcp.disconnect"               # Disconnect from server
{
    "server_type": str,
    "reason": str
}

"mcp.error"                    # MCP error
{
    "server_type": str,
    "error": str,
    "retry_possible": bool
}

"mcp.capability_request"       # Request MCP capability
{
    "server_type": str,
    "capability": str,
    "parameters": dict
}

"mcp.capability_response"      # MCP response
{
    "server_type": str,
    "capability": str,
    "result": any
}
```

### 10. System Events

```python
"system.startup"               # System starting
{
    "version": str,
    "config": dict,
    "agents_loaded": list
}

"system.ready"                 # System ready
{
    "agents_active": list,
    "mcp_connected": list,
    "memory_loaded": bool
}

"system.shutdown"              # System shutting down
{
    "reason": str,
    "save_state": bool
}

"system.error"                 # System error
{
    "component": str,
    "error": str,
    "severity": str,           # "critical", "warning", "info"
    "recovery_action": str
}

"system.health_check"          # Health check request
{
    "components": list         # Which components to check
}

"system.health_status"         # Health check results
{
    "status": dict,            # Component: status
    "issues": list
}
```

### 11. Agent Lifecycle Events

```python
"agent.starting"               # Agent starting up
{
    "agent_name": str,
    "capabilities": list
}

"agent.ready"                  # Agent ready
{
    "agent_name": str,
    "subscribed_events": list
}

"agent.error"                  # Agent error
{
    "agent_name": str,
    "error": str,
    "can_continue": bool
}

"agent.stopping"               # Agent shutting down
{
    "agent_name": str,
    "reason": str
}

"agent.handoff"                # Agent handing off to another
{
    "from_agent": str,
    "to_agent": str,
    "context": dict,
    "reason": str
}
```

### 12. UI/Output Events

```python
"ui.display"                   # Display to user
{
    "content": str,
    "format": str,             # "text", "markdown", "table"
    "priority": str            # "normal", "important", "urgent"
}

"ui.prompt"                    # Prompt user for input
{
    "prompt": str,
    "type": str,               # "text", "confirm", "choice"
    "options": list,           # For choice prompts
    "default": any
}

"ui.progress"                  # Show progress
{
    "task": str,
    "current": int,
    "total": int,
    "message": str
}

"ui.notification"              # Send notification
{
    "title": str,
    "message": str,
    "type": str,               # "info", "success", "warning", "error"
    "actions": list            # Possible user actions
}
```

## Event Flow Examples

### Example 1: Simple Question
```
user.message → router.classify → router.classified 
→ memory.search → memory.search_results 
→ llm.process → llm.response → ui.display
```

### Example 2: Create Task from Conversation
```
user.message → router.classify → task.identified 
→ ui.prompt (confirm task details) → task.create 
→ task.created → memory.store → ui.notification
```

### Example 3: Complex Calendar Scheduling
```
user.message → router.classify → calendar.availability_check 
→ calendar.availability_results → llm.process (pick best time)
→ calendar.create_event → calendar.event_created 
→ memory.store → ui.display
```

### Example 4: Pattern Detection Flow
```
thread.completed → memory.extract_knowledge 
→ pattern.detected → pattern.suggest_automation 
→ ui.prompt → pattern.automation_response 
→ pattern.automation_created
```

## Event Best Practices

1. **Always include thread_id** when relevant
2. **Include timestamps** for temporal events
3. **Use past tense for confirmations** (created, stored, completed)
4. **Include enough context** for agents to act independently
5. **Design for async** - don't assume immediate responses
6. **Version your events** if they might change
7. **Include error events** for every action event

## Special Event Patterns

### Request-Response Pattern
```python
# Always pair request with response events
"service.action" → "service.action_result"
"service.action" → "service.action_error"
```

### Broadcast Pattern
```python
# Some events inform multiple agents
"thread.updated" → (memory agent, task agent, pattern agent all listen)
```

### Chain Pattern
```python
# Events that naturally lead to others
"task.identified" → "task.create" → "task.created" → "memory.store"
```

### Fallback Pattern
```python
# When primary fails, try secondary
"llm.error" → "llm.switch_model" → "llm.process"
```

This comprehensive event system enables complete decoupling while maintaining rich communication between agents.