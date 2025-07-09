"""Event bus implementation for inter-module communication.

Provides a concurrent event bus with optional persistence for loosely coupled communication between modules.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Type
from pydantic import BaseModel, ValidationError

from modules.persistence import EventStorage

logger = logging.getLogger(__name__)



@dataclass
class Event:
    """Represents an event in the system."""

    type: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


class ConcurrentEventBus():
    """Concurrent event bus with optional time-series persistence.
    
    Features:
    - Concurrent handler execution for the same event type
    - Same handler can process multiple events simultaneously
    - Optional daily-partitioned event persistence
    - Schema validation with Pydantic models
    
    For distributed systems, consider Redis Pub/Sub, RabbitMQ, or Kafka.
    """

    def __init__(self, 
                 persistence_enabled: bool = False,
                 persistence_path: str = "data/events",
                 max_history_size: int = 1000,
                 retention_days: Optional[int] = 30):
        """Initialize the concurrent event bus.
        
        Args:
            persistence_enabled: Enable time-series persistence
            persistence_path: Path to directory for event storage
            max_history_size: Maximum number of events to keep in memory
            retention_days: Number of days to retain events (None for no cleanup)
        """
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._schemas: dict[str, Type[BaseModel]] = {}
        self._event_history: list[Event] = []
        self._max_history_size = max_history_size
        
        # Initialize event storage for persistence
        self._storage = None
        if persistence_enabled:
            self._storage = EventStorage(
                storage_path=persistence_path,
                daily_partitions=True,
                retention_days=retention_days
            )
    
    def register(self, event_type: str, schema: Optional[Type[BaseModel]] = None):
        """Decorator to register event handlers with optional schema validation.
        
        Args:
            event_type: The event type to handle (e.g., "task.schedule")
            schema: Optional Pydantic schema for input validation
            
        Returns:
            Decorator function
        """
        def decorator(handler_func: Callable):
            self._handlers[event_type].append(handler_func)
            if schema:
                self._schemas[event_type] = schema
            logger.info(f"Registered {handler_func.__name__} for {event_type}")
            return handler_func
        return decorator

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
        if event_type in self._schemas:
            try:
                schema = self._schemas[event_type]
                validated_data = schema(**data)
                # Convert back to dict for storage/transmission
                data = validated_data.model_dump()
                logger.debug(f"Event data validated for {event_type}")
            except ValidationError as e:
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
            
        # Persist event to storage if configured
        if self._storage:
            await self._storage.save_event(event)

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
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self._event_history if e.type == event_type]
        return self._event_history.copy()

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
    
    def list_events(self) -> dict[str, list[str]]:
        """List all events and their handlers."""
        return {event: [h.__name__ for h in handlers] 
                for event, handlers in self._handlers.items()}
    
    def get_schema(self, event_type: str) -> Optional[dict]:
        """Get json schema for an event type."""
        try:
            return self._schemas.get(event_type).model_json_schema()
        except Exception as e:
            logger.error(f"Error getting schema for {event_type}: {e}")
            return None
    
    def list_schemas(self, brief: bool = False) -> dict[str, dict]:
        """List all event schemas."""
        if brief:
            return {event: self.get_schema(event)["description"] for event in self._schemas}
        else:
            return {event: self.get_schema(event) for event in self._schemas}
    
    def has_handler(self, event_type: str) -> bool:
        """Check if handlers exist for an event type."""
        return event_type in self._handlers and len(self._handlers[event_type]) > 0

