"""Task management event handlers for AgentOS."""

from typing import Dict, Any
import uuid
from modules.eventbus.schemas import TaskScheduleInput, TaskRegisterInput, TaskListInput
from modules.eventbus import Event
from modules import eventbus


@eventbus.register("task.schedule", schema=TaskScheduleInput)
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


@eventbus.register("task.register", schema=TaskRegisterInput)
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


@eventbus.register("task.list", schema=TaskListInput)
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