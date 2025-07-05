"""Task management event handlers for AgentOS."""

from typing import Dict, Any, List, Optional
import uuid
from pydantic import BaseModel, Field
from ..event_registry import register_event_schema
from ..event_bus import Event


class TaskScheduleInput(BaseModel):
    """Input schema for task.schedule event."""
    type: str = Field(default="once", description="Task type: 'once', 'recurring', or 'conditional'")
    at: Optional[str] = Field(default=None, description="When to run the task (ISO format or cron expression)")
    action: List[str] = Field(default_factory=list, description="List of actions to execute")


class TaskRegisterInput(BaseModel):
    """Input schema for task.register event."""
    trigger: str = Field(description="Event trigger pattern")
    condition: str = Field(default="", description="Condition for task execution")
    action: List[str] = Field(default_factory=list, description="List of actions to execute")


class TaskListInput(BaseModel):
    """Input schema for task.list event."""
    filter: Dict[str, Any] = Field(default_factory=dict, description="Filter parameters")
    status: str = Field(default="all", description="Status filter: 'all', 'pending', 'completed', 'failed'")


@register_event_schema("task.schedule", input_model=TaskScheduleInput)
async def task_schedule(event: Event) -> Dict[str, Any]:
    """Create all types of tasks"""
    # Validate input data
    input_data = TaskScheduleInput(**event.data)
    
    # Mock: Return task ID
    return {
        "task_id": f"task_{uuid.uuid4().hex[:8]}",
        "type": input_data.type,
        "at": input_data.at,
        "action": input_data.action,
        "status": "scheduled"
    }


@register_event_schema("task.register", input_model=TaskRegisterInput)
async def task_register(event: Event) -> Dict[str, Any]:
    """Hook-based task registration"""
    # Validate input data
    input_data = TaskRegisterInput(**event.data)
    
    # Mock: Return registration ID
    return {
        "hook_id": f"hook_{uuid.uuid4().hex[:8]}",
        "trigger": input_data.trigger,
        "condition": input_data.condition,
        "action": input_data.action,
        "status": "registered"
    }


@register_event_schema("task.list", input_model=TaskListInput)
async def task_list(event: Event) -> Dict[str, Any]:
    """List tasks"""
    # Validate input data
    input_data = TaskListInput(**event.data)
    
    # Mock: Return empty task list
    return {
        "tasks": [
            {"task_id": "task_mock1", "type": "once", "status": input_data.status}
        ],
        "filter": input_data.filter
    }