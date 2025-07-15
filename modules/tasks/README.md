# AgentOS Task System

The task system provides both time-based scheduling and event-driven task execution for AgentOS.

## Components

### TaskManager (`manager.py`)
The main integration point that combines all task system components. It handles:
- Task creation via events (`task.schedule`, `task.hook`)
- Task listing and management
- Integration with the EventBus

### TaskScheduler (`scheduler.py`)
Manages time-based task execution using APScheduler:
- Interval tasks (run every N seconds)
- One-time tasks (run at specific datetime)
- Cron-based scheduling (future enhancement)

### HookManager (`hooks.py`)
Manages event-driven tasks:
- Pattern matching for event names (supports wildcards)
- Executes tasks when matching events occur
- Pre/post hook positioning (future enhancement)

### TaskStorage (`storage.py`)
Persists tasks as JSON files:
- Save/load individual tasks
- List all tasks
- Automatic task restoration on startup

## Usage

```python
from modules import eventbus
from modules.tasks import TaskManager

# Initialize
task_manager = TaskManager()
await task_manager.start()

# Schedule a recurring task
await eventbus.publish("task.schedule", {
    "name": "Daily Report",
    "trigger": {"type": "interval", "seconds": 86400},
    "event_chain": [
        {"event": "report.generate", "data": {"type": "daily"}},
        {"event": "email.send", "data": {"to": "admin@example.com"}}
    ]
})

# Register an event hook
await eventbus.publish("task.hook", {
    "name": "Error Logger",
    "pattern": "*.error",
    "event_chain": [
        {"event": "logger.error", "data": {"severity": "high"}},
        {"event": "alert.send", "data": {"channel": "ops"}}
    ]
})
```

## Task Storage

Tasks are stored in `./data/tasks/` as JSON files:
- Scheduled tasks: `sched_*.json`
- Hook tasks: `hook_*.json`

## Future Enhancements

1. **Cron Expression Support**: More flexible scheduling
2. **Task Dependencies**: Execute tasks in sequence
3. **Retry Policies**: Automatic retry on failure
4. **Task Groups**: Organize related tasks
5. **Pre/Post Hooks**: Execute before/after events
6. **Conditional Execution**: Based on event data
7. **Real Event Chain Execution**: Currently just prints

## Example

See `example.py` for a complete demonstration of the task system capabilities.