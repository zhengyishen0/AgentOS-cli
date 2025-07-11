"""Event bus implementation for inter-module communication.

Provides a concurrent event bus with optional persistence for loosely coupled communication between modules.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional, Type
from pydantic import BaseModel, ValidationError

from modules.persistence import EventStorage
from .models import Event

logger = logging.getLogger(__name__)


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
    
    def register(self, name: str, schema: Optional[Type[BaseModel]] = None):
        """Decorator to register event handlers with optional schema validation.
        
        Args:
            name: The event name to handle (e.g., "task.schedule")
            schema: Optional Pydantic schema for input validation
            
        Returns:
            Decorator function
        """
        def decorator(handler_func: Callable):
            self._handlers[name].append(handler_func)
            if schema:
                self._schemas[name] = schema
            logger.info(f"Registered {handler_func.__name__} for {name}")
            return handler_func
        return decorator

    async def publish(self, name: str, data: dict[str, Any], source: str = "system") -> dict[str, Any]:
        """Publish an event to all subscribers and return handler results.

        Args:
            name: Name of event (e.g., "user.created")
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
        if name in self._schemas:
            try:
                schema = self._schemas[name]
                validated_data = schema(**data)
                # Convert back to dict for storage/transmission
                data = validated_data.model_dump()
                logger.debug(f"Event data validated for {name}")
            except ValidationError as e:
                logger.error(f"Event validation failed for {name}: {e}")
                raise
        else:
            logger.warning(
                f"No schema registered for event type: {name}. Publishing without validation."
            )

        event = Event(name=name, data=data, source=source)

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
            
        # Persist initial event to storage if configured
        if self._storage:
            await self._storage.save_event(event.model_dump())

        # Log event
        logger.info(f"Publishing event: {name} from {source}")

        # Get handlers for this event type
        handlers = self._handlers.get(name, [])

        # Execute handlers concurrently and collect results
        handler_results = {}
        start_time = asyncio.get_event_loop().time()
        
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
                        f"Handler {handler_name} failed for event {name}: {result}"
                    )
                    handler_results[handler_name] = {"error": str(result)}
                else:
                    handler_results[handler_name] = result

        # Combine thread_id from first result if not set
        if event.thread_id is None and results[0] is not None:
            event.thread_id = results[0].get("thread_id", None)
        event.completed_at = datetime.now(timezone.utc)
        event.execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Determine final result and status
        if len(handler_results) == 0:
            event.result = {}
            event.status = "completed"
        elif len(handler_results) == 1:
            result = next(iter(handler_results.values()))
            if isinstance(result, dict) and "error" in result:
                event.status = "failed"
                event.error = result["error"]
                event.result = result
            else:
                event.status = "completed"
                event.result = result
        else:
            # Check if any handler failed
            has_errors = any(isinstance(r, dict) and "error" in r for r in handler_results.values())
            event.status = "failed" if has_errors else "completed"
            event.result = handler_results

        # Persist completed event to storage if configured
        if self._storage:
            await self._storage.save_event(event.model_dump())

        # Save event to thread
        from modules import thread_manager
        if event.thread_id is not None:
            await thread_manager.add_event_to_thread(event.thread_id, event)

        # Return results based on number of handlers
        if len(handler_results) == 0:
            return {}
        elif len(handler_results) == 1:
            # Single handler - return its result directly
            return next(iter(handler_results.values()))
        else:
            # Multiple handlers - return dict with handler names as keys
            return handler_results

    async def subscribe(self, name: str, handler: Callable) -> None:
        """Subscribe to events of a specific type.

        Args:
            name: Name of event to subscribe to
            handler: Async or sync function to handle the event
        """
        self._handlers[name].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {name}")

    async def unsubscribe(self, name: str, handler: Callable) -> None:
        """Unsubscribe from events.

        Args:
            name: Name of event to unsubscribe from
            handler: Handler function to remove
        """
        if name in self._handlers and handler in self._handlers[name]:
            self._handlers[name].remove(handler)
            logger.info(f"Unsubscribed {handler.__name__} from {name}")

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

    def get_event_history(self, name: str | None = None) -> list[Event]:
        """Get event history, optionally filtered by type."""
        if name:
            return [e for e in self._event_history if e.name == name]
        return self._event_history.copy()

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
    
    def list_events(self) -> dict[str, list[str]]:
        """List all events and their handlers."""
        return {event: [h.__name__ for h in handlers] 
                for event, handlers in self._handlers.items()}
    
    def get_schema(self, name: str) -> Optional[dict]:
        """Get json schema for an event type."""
        try:
            return self._schemas.get(name).model_json_schema()
        except Exception as e:
            logger.error(f"Error getting schema for {name}: {e}")
            return None
    
    def list_schemas(self, brief: bool = False) -> dict[str, dict]:
        """List all event schemas."""
        if brief:
            return {event: self.get_schema(event)["description"] for event in self._schemas}
        else:
            return {event: self.get_schema(event) for event in self._schemas}
    
    def has_handler(self, name: str) -> bool:
        """Check if handlers exist for an event type."""
        return name in self._handlers and len(self._handlers[name]) > 0

