"""AgentOS modules package."""

from .event_bus import InMemoryEventBus, Event
from .event_registry import (
    register_event_schema,
    get_event_schema,
    validate_event_data,
    list_registered_events,
    publishes_event,
    subscribes_to_event,
)

# Create a singleton event bus instance
event_bus = InMemoryEventBus()

# Import schemas to register them
from . import event_schemas

__all__ = [
    "event_bus",
    "Event",
    "InMemoryEventBus",
    "register_event_schema",
    "get_event_schema",
    "validate_event_data",
    "list_registered_events",
    "publishes_event",
    "subscribes_to_event",
]