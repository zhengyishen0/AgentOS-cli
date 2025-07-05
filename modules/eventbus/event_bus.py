"""Event bus implementation for inter-module communication.

Provides a simple in-memory event bus for loosely coupled communication between modules.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .event_registry import get_event_schema, validate_event_data

logger = logging.getLogger(__name__)



@dataclass
class Event:
    """Represents an event in the system."""

    type: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


class InMemoryEventBus():
    """In-memory implementation of EventBus for development and testing.

    For production, consider using Redis Pub/Sub, RabbitMQ, or Kafka.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._event_history: list[Event] = []
        self._max_history_size = 1000

    async def publish(self, event_type: str, data: dict[str, Any], source: str = "system") -> dict[str, Any]:
        """Publish an event to all subscribers and return handler results.

        Args:
            event_type: Type of event (e.g., "user.created")
            data: Event data payload
            source: Source of the event

        Returns:
            Dict with handler results. If single handler, returns its result directly.
            If multiple handlers, returns dict with handler names as keys.

        Raises:
            ValueError: If event type is not registered
            ValidationError: If data doesn't match the registered schema
        """
        # Validate event data against registered schema
        schema = get_event_schema(event_type)
        if schema:
            try:
                validated_data = validate_event_data(event_type, data)
                # Convert back to dict for storage/transmission
                data = validated_data.model_dump()
                logger.debug(f"Event data validated for {event_type}")
            except Exception as e:
                logger.error(f"Event validation failed for {event_type}: {e}")
                raise
        else:
            logger.warning(
                f"No schema registered for event type: {event_type}. Publishing without validation."
            )

        event = Event(type=event_type, data=data, source=source)

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)

        # Log event
        logger.info(f"Publishing event: {event_type} from {source}")

        # Get handlers for this event type
        handlers = self._handlers.get(event_type, [])

        # Execute handlers concurrently and collect results
        handler_results = {}
        
        if handlers:
            tasks = []
            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(self._execute_handler(handler, event))
                else:
                    # Wrap sync handlers
                    tasks.append(self._execute_sync_handler(handler, event))

            # Wait for all handlers to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                handler_name = handlers[i].__name__
                if isinstance(result, Exception):
                    logger.error(
                        f"Handler {handler_name} failed for event {event_type}: {result}"
                    )
                    handler_results[handler_name] = {"error": str(result)}
                else:
                    handler_results[handler_name] = result

        # Return results based on number of handlers
        if len(handler_results) == 0:
            return {}
        elif len(handler_results) == 1:
            # Single handler - return its result directly
            return next(iter(handler_results.values()))
        else:
            # Multiple handlers - return dict with handler names as keys
            return handler_results

    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async or sync function to handle the event
        """
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type}")

    async def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from events.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.info(f"Unsubscribed {handler.__name__} from {event_type}")

    async def _execute_handler(self, handler: Callable, event: Event) -> Any:
        """Execute an async handler with error handling."""
        try:
            return await handler(event)
        except Exception as e:
            logger.error(f"Async handler {handler.__name__} failed: {e}")
            raise

    async def _execute_sync_handler(self, handler: Callable, event: Event) -> Any:
        """Execute a sync handler in a thread pool with error handling."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, handler, event)
        except Exception as e:
            logger.error(f"Sync handler {handler.__name__} failed: {e}")
            raise

    def get_event_history(self, event_type: str | None = None) -> list[Event]:
        """Get event history, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            List of events
        """
        if event_type:
            return [e for e in self._event_history if e.type == event_type]
        return self._event_history.copy()

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
