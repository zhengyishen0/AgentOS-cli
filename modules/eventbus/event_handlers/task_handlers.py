"""Task management event handlers for AgentOS."""

from typing import Dict, Any
import uuid
from ..event_registry import register_event_schema
from ..event_bus import Event


@register_event_schema("task.schedule")
async def task_schedule(event: Event) -> Dict[str, Any]:
    """Create all types of tasks"""
    task_type = event.data.get('type', 'once')
    at = event.data.get('at')
    action = event.data.get('action', [])
    
    # Mock: Return task ID
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