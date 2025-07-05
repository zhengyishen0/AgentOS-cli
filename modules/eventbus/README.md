# AgentOS EventBus Architecture

This module provides a flexible event-driven architecture for AgentOS, supporting both static and dynamic event handler registration with automatic schema validation.

## Quick Start

```python
from modules.eventbus import eventbus, TaskScheduleInput

# Publish an event
result = await eventbus.publish("task.schedule", {
    "type": "once",
    "action": ["send_email", "update_calendar"]
})
```

## Architecture Overview

The EventBus system consists of:
- **EventBus**: Core pub/sub system with validation
- **Event Schemas**: Pydantic models for type safety
- **Handler Registration**: Two methods for different use cases

## Event Registration Patterns

### 1. Static Registration (Recommended)

Use `@eventbus.register` decorator for permanent handlers defined at module load:

```python
from modules.eventbus import eventbus, Event
from modules.eventbus.event_schemas import TaskScheduleInput

@eventbus.register("task.schedule", schema=TaskScheduleInput)
async def task_schedule(event: Event) -> Dict[str, Any]:
    """Handle task scheduling with automatic validation."""
    # event.data is already validated against TaskScheduleInput schema
    input_data = TaskScheduleInput(**event.data)
    
    return {
        "task_id": f"task_{uuid.uuid4().hex[:8]}",
        "status": "scheduled",
        "type": input_data.type
    }
```

**Benefits:**
- ✅ Automatic input validation with Pydantic schemas
- ✅ Type safety and better IDE support  
- ✅ Schema documentation is co-located
- ✅ Consistent handler registration across the codebase

### 2. Dynamic Registration

Use `subscribe/unsubscribe` for runtime handler management:

```python
async def setup_user_session(user_id: str):
    """Register user-specific handlers at runtime."""
    
    async def user_notification_handler(event: Event):
        # User-specific notification logic
        return {"user": user_id, "notified": True}
    
    # Add handler dynamically
    await eventbus.subscribe(f"user.{user_id}.notify", user_notification_handler)
    
    # Later, remove when session ends
    await eventbus.unsubscribe(f"user.{user_id}.notify", user_notification_handler)
```

**Use Cases:**
- ✅ User session-specific handlers
- ✅ Feature flag-based handler swapping
- ✅ A/B testing different handler implementations
- ✅ Plugin systems with runtime handler loading

## Event Publishing

### Basic Publishing

```python
# Simple event without validation
result = await eventbus.publish("system.heartbeat", {"timestamp": "2024-01-01T10:00:00Z"})

# Event with schema validation (if registered)
result = await eventbus.publish("task.schedule", {
    "type": "once",
    "at": "2024-01-01T15:00:00Z", 
    "action": ["send_reminder"]
})
```

### Publishing with Source Tracking

```python
result = await eventbus.publish(
    event_type="user.action",
    data={"action": "login", "user_id": "123"},
    source="auth_service"
)
```

## Schema Validation

All event schemas are defined in `event_schemas.py`:

```python
from modules.eventbus.event_schemas import (
    TaskScheduleInput,
    AgentThinkInput, 
    MemorySearchInput,
    # ... all other schemas
)

# Schemas are automatically validated when using @eventbus.register
# Manual validation (if needed):
try:
    validated_data = TaskScheduleInput(**raw_data)
except ValidationError as e:
    print(f"Invalid data: {e}")
```

## Available Event Schemas

### Task Events
- `TaskScheduleInput` - Schedule tasks with type, timing, and actions
- `TaskRegisterInput` - Register event-driven tasks/hooks  
- `TaskListInput` - List and filter tasks

### Agent Events
- `AgentChainInput` - Convert plans to executable event chains
- `AgentThinkInput` - Strategic planning and reasoning
- `AgentDecideInput` - Parameter completion and decisions

### Thread Events  
- `ThreadMatchInput` - Match messages to conversation threads
- `ThreadSummarizeInput` - Summarize thread conversations
- `ThreadCreateInput` - Create new conversation threads
- `ThreadArchivedInput` - Archive completed threads

### Memory Events
- `MemoryAppendInput` - Append content to memory/journal
- `MemorySearchInput` - Search across stored memories
- `MemoryDigestInput` - Process and organize memories

### System Events
- `UserInputInput` - Handle user input messages
- `UserNotifyInput` - Send notifications to users
- `WebSearchInput` - Perform web searches

## EventBus Utilities

### Inspect Registered Events

```python
# List all registered events and their handlers
events = eventbus.list_events()
print(events)
# Output: {"task.schedule": ["task_schedule"], "agent.think": ["agent_think"]}

# Check if handler exists
has_handler = eventbus.has_handler("task.schedule")  # True

# Get schema for an event type
schema = eventbus.get_schema("task.schedule")  # Returns TaskScheduleInput class
```

### Event History

```python
# Get event history (for debugging/monitoring)
all_events = eventbus.get_event_history()
task_events = eventbus.get_event_history("task.schedule")

# Clear history 
eventbus.clear_history()
```

## Error Handling

### Validation Errors

```python
from pydantic import ValidationError

try:
    result = await eventbus.publish("task.schedule", {
        "type": "invalid_type",  # Should be "once", "recurring", etc.
        "action": "not_a_list"   # Should be a list
    })
except ValidationError as e:
    print(f"Schema validation failed: {e}")
    # Handle invalid input
```

### Handler Errors

```python
# Handler exceptions are caught and returned in results
result = await eventbus.publish("problematic.event", {})

if "error" in result:
    print(f"Handler failed: {result['error']}")
    # Handle handler failure
```

## Advanced Patterns

### Multiple Handlers per Event

```python
# Multiple handlers can subscribe to the same event
@eventbus.register("user.created")
async def send_welcome_email(event: Event):
    # Email service handles this
    return {"email_sent": True}

@eventbus.register("user.created") 
async def create_user_profile(event: Event):
    # Profile service handles this
    return {"profile_created": True}

# Both handlers execute when event is published
result = await eventbus.publish("user.created", {"user_id": "123"})
# result = {"send_welcome_email": {"email_sent": True}, "create_user_profile": {"profile_created": True}}
```

### Handler Registration in Classes

```python
class UserService:
    def __init__(self):
        # Register handlers in constructor
        eventbus.register("user.create", schema=UserCreateInput)(self.create_user)
        eventbus.register("user.delete", schema=UserDeleteInput)(self.delete_user)
    
    async def create_user(self, event: Event):
        # Handler implementation
        pass
    
    async def delete_user(self, event: Event):
        # Handler implementation  
        pass
```

## Best Practices

### 1. Schema Design
- ✅ Use descriptive field names with clear types
- ✅ Provide field descriptions for documentation
- ✅ Use appropriate default values
- ✅ Group related schemas logically

### 2. Handler Implementation
- ✅ Keep handlers focused on single responsibility
- ✅ Use meaningful return values for debugging
- ✅ Handle errors gracefully with try/catch
- ✅ Log important events for monitoring

### 3. Event Naming
- ✅ Use hierarchical naming: `domain.action` (e.g., `task.schedule`)
- ✅ Be consistent across related events
- ✅ Use verbs for actions: `user.created`, `task.completed`

### 4. Error Recovery
- ✅ Validate input data early in handlers
- ✅ Return meaningful error information
- ✅ Consider implementing retry logic for transient failures
- ✅ Monitor event history for debugging

## Migration Guide

If upgrading from the old registry system:

```python
# OLD - Don't use anymore
from modules.eventbus.event_registry import register_event_schema

@register_event_schema("task.schedule", input_model=TaskScheduleInput)
async def task_schedule(event: Event):
    pass

# NEW - Use this pattern
from modules.eventbus import eventbus
from modules.eventbus.event_schemas import TaskScheduleInput

@eventbus.register("task.schedule", schema=TaskScheduleInput)
async def task_schedule(event: Event):
    pass
```

The new system provides the same functionality with simpler architecture and better flexibility.