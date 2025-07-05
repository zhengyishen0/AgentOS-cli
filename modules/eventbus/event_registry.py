"""Event registry with decorator-based registration and Pydantic validation.

This module provides a centralized registry for event schemas using decorators
and Pydantic models for type safety and automatic validation.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class EventSchema:
    """Metadata about a registered event schema."""

    name: str
    handler: Callable  # The actual handler function
    input_model: type[BaseModel] | None = None  # Input validation schema
    output_model: type[BaseModel] | None = None  # Output schema (optional)
    publisher: str | None = None
    description: str | None = None


# Global registry of all event schemas
EVENT_REGISTRY: dict[str, EventSchema] = {}


def register_event_schema(
    event_name: str, 
    input_model: type[BaseModel] | None = None,
    publisher: str | None = None, 
    description: str | None = None
):
    """Decorator to register an event handler with optional input/output schemas.

    Args:
        event_name: The event type name (e.g., "task.schedule")
        input_model: Optional Pydantic model for input validation
        publisher: Optional name of the publishing service
        description: Optional description of when this event is published

    Returns:
        Decorator function that registers the handler

    Example:
        @register_event_schema("task.schedule", input_model=TaskScheduleInput)
        async def task_schedule(event: Event) -> Dict[str, Any]:
            # Handler implementation
    """

    def decorator(handler_func: Callable) -> Callable:
        if event_name in EVENT_REGISTRY:
            logger.warning(f"Overriding existing event schema: {event_name}")

        EVENT_REGISTRY[event_name] = EventSchema(
            name=event_name,
            handler=handler_func,
            input_model=input_model,
            publisher=publisher, 
            description=description
        )

        logger.debug(f"Registered event schema: {event_name} -> {handler_func.__name__}")
        return handler_func

    return decorator


def get_event_schema(event_name: str) -> EventSchema | None:
    """Get the schema for an event type.

    Args:
        event_name: The event type name

    Returns:
        EventSchema if registered, None otherwise
    """
    return EVENT_REGISTRY.get(event_name)


def validate_event_data(event_name: str, data: dict[str, Any]) -> BaseModel:
    """Validate event data against registered input schema.

    Args:
        event_name: The event type name
        data: The event data to validate

    Returns:
        Validated Pydantic model instance

    Raises:
        ValueError: If event type is not registered or has no input schema
        ValidationError: If data doesn't match schema
    """
    schema = get_event_schema(event_name)
    if not schema:
        raise ValueError(f"No schema registered for event type: {event_name}")
    
    if not schema.input_model:
        raise ValueError(f"No input schema defined for event type: {event_name}")

    return schema.input_model(**data)


def list_registered_events() -> dict[str, EventSchema]:
    """Get all registered event schemas.

    Returns:
        Dictionary mapping event names to their schemas
    """
    return EVENT_REGISTRY.copy()


def publishes_event(event_name: str):
    """Decorator to mark a method as publishing an event.

    This is primarily for documentation and tooling purposes.
    The actual event publishing still needs to be done manually.

    Args:
        event_name: The event type that this method publishes

    Example:
        @publishes_event("calculation.completed")
        async def calculate(self, operation: str, a: float, b: float):
            result = self._perform_calculation(operation, a, b)
            await self.event_bus.publish("calculation.completed", {
                "operation": operation,
                "result": result,
                "timestamp": datetime.utcnow()
            })
            return result
    """

    def decorator(func: Callable) -> Callable:
        # Add metadata to the function for introspection
        if not hasattr(func, "_publishes_events"):
            func._publishes_events = []
        func._publishes_events.append(event_name)
        return func

    return decorator


def subscribes_to_event(event_name: str):
    """Decorator to mark a method as subscribing to an event.

    This is primarily for documentation and tooling purposes.
    The actual event subscription still needs to be done manually.

    Args:
        event_name: The event type that this method subscribes to

    Example:
        @subscribes_to_event("calculation.completed")
        async def handle_calculation_completed(self, event):
            logger.info(f"Calculation completed: {event.data}")
    """

    def decorator(func: Callable) -> Callable:
        # Add metadata to the function for introspection
        if not hasattr(func, "_subscribes_to_events"):
            func._subscribes_to_events = []
        func._subscribes_to_events.append(event_name)
        return func

    return decorator
