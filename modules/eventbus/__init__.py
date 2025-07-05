"""EventBus module for AgentOS EventChain architecture."""

from .event_bus import InMemoryEventBus, Event
from .event_registry import (
    register_event_schema,
    get_event_schema,
    validate_event_data,
    list_registered_events,
    publishes_event,
    subscribes_to_event,
)
# from .event_schemas import *  # Will contain all core event schemas

__all__ = [
    "InMemoryEventBus",
    "Event",
    "register_event_schema",
    "get_event_schema",
    "validate_event_data",
    "list_registered_events",
    "publishes_event",
    "subscribes_to_event",
]