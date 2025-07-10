"""Tests for EventBus implementation with event_registry integration."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel, ValidationError

from modules.eventbus.event_bus import Event, InMemoryEventBus
from modules.eventbus.event_registry import (
    register_event_schema, 
    get_event_schema,
    validate_event_data,
    list_registered_events,
    publishes_event,
    subscribes_to_event,
    EVENT_REGISTRY
)


# Test event schemas
@register_event_schema("test.user.created", publisher="UserService", description="User registration completed")
class UserCreatedEvent(BaseModel):
    user_id: int
    username: str
    email: str


@register_event_schema("test.calculation.completed", publisher="CalculatorService")
class CalculationCompletedEvent(BaseModel):
    operation: str
    result: float
    operands: list[float]


@register_event_schema("test.order.placed", publisher="OrderService")
class OrderPlacedEvent(BaseModel):
    order_id: str
    customer_id: int
    items: list[dict]
    total: float


class TestEvent:
    """Test cases for Event class."""
    
    def test_event_creation_with_defaults(self):
        """Test creating an event with default values."""
        event = Event(name="test.event", data={"key": "value"})
        
        assert event.name == "test.event"
        assert event.data == {"key": "value"}
        assert event.source == "system"
        assert isinstance(event.timestamp, datetime)
    
    def test_event_creation_with_custom_values(self):
        """Test creating an event with custom values."""
        custom_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        event = Event(
            name="custom.event",
            data={"message": "hello"},
            timestamp=custom_timestamp,
            source="test_service"
        )
        
        assert event.name == "custom.event"
        assert event.data == {"message": "hello"}
        assert event.source == "test_service"
        assert event.timestamp == custom_timestamp
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        event = Event(
            name="test.event",
            data={"key": "value"},
            timestamp=timestamp,
            source="test_source"
        )
        
        result = event.to_dict()
        expected = {
            "type": "test.event",
            "data": {"key": "value"},
            "timestamp": "2023-01-01T12:00:00",
            "source": "test_source"
        }
        
        assert result == expected


class TestInMemoryEventBus:
    """Test cases for InMemoryEventBus class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.event_bus = InMemoryEventBus()
        # Note: EVENT_REGISTRY is populated by the decorators above
    
    def test_initialization(self):
        """Test EventBus initialization."""
        bus = InMemoryEventBus()
        
        assert bus._handlers == {}
        assert bus._event_history == []
        assert bus._max_history_size == 1000
    
    @pytest.mark.asyncio
    async def test_publish_without_subscribers(self):
        """Test publishing event with no subscribers."""
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert result == {}
        assert len(self.event_bus._event_history) == 1
        assert self.event_bus._event_history[0].type == "test.event"
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish_single_handler(self):
        """Test subscribing and publishing with single handler."""
        handler_called = False
        received_event = None
        
        async def test_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event
            return {"processed": True}
        
        await self.event_bus.subscribe("test.event", test_handler)
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert handler_called
        assert received_event.type == "test.event"
        assert received_event.data == {"key": "value"}
        assert result == {"processed": True}
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish_multiple_handlers(self):
        """Test publishing with multiple handlers."""
        handler1_called = False
        handler2_called = False
        
        async def handler1(event):
            nonlocal handler1_called
            handler1_called = True
            return {"handler": "1"}
        
        async def handler2(event):
            nonlocal handler2_called
            handler2_called = True
            return {"handler": "2"}
        
        await self.event_bus.subscribe("test.event", handler1)
        await self.event_bus.subscribe("test.event", handler2)
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert handler1_called
        assert handler2_called
        assert "handler1" in result
        assert "handler2" in result
        assert result["handler1"] == {"handler": "1"}
        assert result["handler2"] == {"handler": "2"}
    
    @pytest.mark.asyncio
    async def test_sync_handler_execution(self):
        """Test execution of synchronous handlers."""
        handler_called = False
        
        def sync_handler(event):
            nonlocal handler_called
            handler_called = True
            return {"sync": True}
        
        await self.event_bus.subscribe("test.event", sync_handler)
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert handler_called
        assert result == {"sync": True}
    
    @pytest.mark.asyncio
    async def test_mixed_sync_async_handlers(self):
        """Test mixing sync and async handlers."""
        async def async_handler(event):
            return {"type": "async"}
        
        def sync_handler(event):
            return {"type": "sync"}
        
        await self.event_bus.subscribe("test.event", async_handler)
        await self.event_bus.subscribe("test.event", sync_handler)
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert "async_handler" in result
        assert "sync_handler" in result
        assert result["async_handler"] == {"type": "async"}
        assert result["sync_handler"] == {"type": "sync"}
    
    @pytest.mark.asyncio
    async def test_handler_exception_handling(self):
        """Test handling of exceptions in handlers."""
        async def failing_handler(event):
            raise ValueError("Handler failed")
        
        async def working_handler(event):
            return {"success": True}
        
        await self.event_bus.subscribe("test.event", failing_handler)
        await self.event_bus.subscribe("test.event", working_handler)
        
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert "failing_handler" in result
        assert "working_handler" in result
        assert "error" in result["failing_handler"]
        assert "Handler failed" in result["failing_handler"]["error"]
        assert result["working_handler"] == {"success": True}
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing from events."""
        handler_called = False
        
        async def test_handler(event):
            nonlocal handler_called
            handler_called = True
            return {"called": True}
        
        # Subscribe then unsubscribe
        await self.event_bus.subscribe("test.event", test_handler)
        await self.event_bus.unsubscribe("test.event", test_handler)
        
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        assert not handler_called
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a handler that wasn't subscribed."""
        async def test_handler(event):
            return {"called": True}
        
        # This should not raise an error
        await self.event_bus.unsubscribe("test.event", test_handler)
        
        # Event should still work normally
        result = await self.event_bus.publish("test.event", {"key": "value"})
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_event_validation_success(self):
        """Test successful event validation with registered schema."""
        valid_data = {
            "user_id": 123,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        async def test_handler(event):
            return {"received": event.data}
        
        await self.event_bus.subscribe("test.user.created", test_handler)
        result = await self.event_bus.publish("test.user.created", valid_data)
        
        assert result["received"] == valid_data
    
    @pytest.mark.asyncio
    async def test_event_validation_failure(self):
        """Test event validation failure with registered schema."""
        invalid_data = {
            "user_id": "not_an_integer",  # Should be int
            "username": "testuser",
            "email": "test@example.com"
        }
        
        with pytest.raises(ValidationError):
            await self.event_bus.publish("test.user.created", invalid_data)
    
    @pytest.mark.asyncio
    async def test_event_validation_missing_fields(self):
        """Test event validation with missing required fields."""
        incomplete_data = {
            "user_id": 123,
            # Missing username and email
        }
        
        with pytest.raises(ValidationError):
            await self.event_bus.publish("test.user.created", incomplete_data)
    
    @pytest.mark.asyncio
    async def test_event_without_schema(self):
        """Test publishing event without registered schema."""
        with patch('modules.eventbus.event_bus.logger') as mock_logger:
            result = await self.event_bus.publish("unregistered.event", {"key": "value"})
            
            assert result == {}
            mock_logger.warning.assert_called_once()
            assert "No schema registered" in mock_logger.warning.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_complex_event_validation(self):
        """Test validation of complex event data."""
        valid_order_data = {
            "order_id": "ORD-123",
            "customer_id": 456,
            "items": [
                {"product_id": "PROD-1", "quantity": 2, "price": 10.50},
                {"product_id": "PROD-2", "quantity": 1, "price": 25.00}
            ],
            "total": 46.00
        }
        
        async def order_handler(event):
            return {"order_processed": True}
        
        await self.event_bus.subscribe("test.order.placed", order_handler)
        result = await self.event_bus.publish("test.order.placed", valid_order_data)
        
        assert result == {"order_processed": True}
    
    def test_event_history_storage(self):
        """Test event history storage."""
        # Publish a few events
        asyncio.run(self.event_bus.publish("event1", {"data": "1"}))
        asyncio.run(self.event_bus.publish("event2", {"data": "2"}))
        asyncio.run(self.event_bus.publish("event1", {"data": "3"}))
        
        history = self.event_bus.get_event_history()
        assert len(history) == 3
        assert history[0].type == "event1"
        assert history[1].type == "event2"
        assert history[2].type == "event1"
    
    def test_event_history_filtering(self):
        """Test filtering event history by type."""
        # Publish events of different types
        asyncio.run(self.event_bus.publish("event1", {"data": "1"}))
        asyncio.run(self.event_bus.publish("event2", {"data": "2"}))
        asyncio.run(self.event_bus.publish("event1", {"data": "3"}))
        
        event1_history = self.event_bus.get_event_history("event1")
        assert len(event1_history) == 2
        assert all(e.type == "event1" for e in event1_history)
        
        event2_history = self.event_bus.get_event_history("event2")
        assert len(event2_history) == 1
        assert event2_history[0].type == "event2"
    
    def test_event_history_max_size(self):
        """Test event history size limit."""
        # Set a small max size for testing
        self.event_bus._max_history_size = 3
        
        # Publish more events than the limit
        for i in range(5):
            asyncio.run(self.event_bus.publish(f"event{i}", {"data": str(i)}))
        
        history = self.event_bus.get_event_history()
        assert len(history) == 3
        # Should keep the latest events
        assert history[0].type == "event2"
        assert history[1].type == "event3"
        assert history[2].type == "event4"
    
    def test_clear_history(self):
        """Test clearing event history."""
        # Publish some events
        asyncio.run(self.event_bus.publish("event1", {"data": "1"}))
        asyncio.run(self.event_bus.publish("event2", {"data": "2"}))
        
        assert len(self.event_bus.get_event_history()) == 2
        
        self.event_bus.clear_history()
        assert len(self.event_bus.get_event_history()) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_handler_execution(self):
        """Test that handlers execute concurrently."""
        execution_order = []
        
        async def slow_handler(event):
            execution_order.append("slow_start")
            await asyncio.sleep(0.1)
            execution_order.append("slow_end")
            return {"handler": "slow"}
        
        async def fast_handler(event):
            execution_order.append("fast_start")
            await asyncio.sleep(0.05)
            execution_order.append("fast_end")
            return {"handler": "fast"}
        
        await self.event_bus.subscribe("test.event", slow_handler)
        await self.event_bus.subscribe("test.event", fast_handler)
        
        result = await self.event_bus.publish("test.event", {"key": "value"})
        
        # Both handlers should have executed
        assert "slow_handler" in result
        assert "fast_handler" in result
        
        # Fast handler should complete before slow handler
        assert execution_order.index("fast_end") < execution_order.index("slow_end")
    
    @pytest.mark.asyncio
    async def test_event_source_tracking(self):
        """Test that event source is properly tracked."""
        received_events = []
        
        async def test_handler(event):
            received_events.append(event)
            return {"received": True}
        
        await self.event_bus.subscribe("test.event", test_handler)
        await self.event_bus.publish("test.event", {"key": "value"}, source="test_service")
        
        assert len(received_events) == 1
        assert received_events[0].source == "test_service"
    
    @pytest.mark.asyncio
    async def test_complex_event_data(self):
        """Test handling of complex event data structures."""
        complex_data = {
            "nested": {
                "list": [1, 2, 3],
                "dict": {"key": "value"},
                "boolean": True,
                "null": None
            },
            "array": ["a", "b", "c"]
        }
        
        received_data = None
        
        async def test_handler(event):
            nonlocal received_data
            received_data = event.data
            return {"processed": True}
        
        await self.event_bus.subscribe("test.event", test_handler)
        await self.event_bus.publish("test.event", complex_data)
        
        assert received_data == complex_data
    
    @pytest.mark.asyncio
    async def test_handler_return_values(self):
        """Test various handler return value types."""
        async def string_handler(event):
            return "string_result"
        
        async def dict_handler(event):
            return {"key": "value"}
        
        async def list_handler(event):
            return [1, 2, 3]
        
        async def none_handler(event):
            return None
        
        await self.event_bus.subscribe("test.event", string_handler)
        result = await self.event_bus.publish("test.event", {})
        assert result == "string_result"
        
        # Clear and test multiple handlers
        await self.event_bus.unsubscribe("test.event", string_handler)
        await self.event_bus.subscribe("test.event", dict_handler)
        await self.event_bus.subscribe("test.event", list_handler)
        await self.event_bus.subscribe("test.event", none_handler)
        
        result = await self.event_bus.publish("test.event", {})
        assert result["dict_handler"] == {"key": "value"}
        assert result["list_handler"] == [1, 2, 3]
        assert result["none_handler"] is None


class TestEventRegistryIntegration:
    """Test cases for event registry integration."""
    
    def test_get_registered_schema(self):
        """Test retrieving registered event schemas."""
        schema = get_event_schema("test.user.created")
        assert schema is not None
        assert schema.name == "test.user.created"
        assert schema.model == UserCreatedEvent
        assert schema.publisher == "UserService"
        assert schema.description == "User registration completed"
    
    def test_get_nonexistent_schema(self):
        """Test retrieving non-existent schema."""
        schema = get_event_schema("nonexistent.event")
        assert schema is None
    
    def test_validate_event_data_success(self):
        """Test successful event data validation."""
        valid_data = {
            "user_id": 123,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        result = validate_event_data("test.user.created", valid_data)
        assert isinstance(result, UserCreatedEvent)
        assert result.user_id == 123
        assert result.username == "testuser"
        assert result.email == "test@example.com"
    
    def test_validate_event_data_failure(self):
        """Test event data validation failure."""
        invalid_data = {
            "user_id": "not_an_integer",
            "username": "testuser",
            "email": "test@example.com"
        }
        
        with pytest.raises(ValidationError):
            validate_event_data("test.user.created", invalid_data)
    
    def test_validate_unregistered_event(self):
        """Test validation of unregistered event type."""
        with pytest.raises(ValueError, match="No schema registered"):
            validate_event_data("unregistered.event", {"key": "value"})
    
    def test_list_registered_events(self):
        """Test listing all registered events."""
        events = list_registered_events()
        assert "test.user.created" in events
        assert "test.calculation.completed" in events
        assert "test.order.placed" in events
    
    def test_publishes_event_decorator(self):
        """Test @publishes_event decorator."""
        @publishes_event("test.user.created")
        @publishes_event("test.user.updated")
        async def create_user(user_data):
            return user_data
        
        assert hasattr(create_user, "_publishes_events")
        assert "test.user.created" in create_user._publishes_events
        assert "test.user.updated" in create_user._publishes_events
    
    def test_subscribes_to_event_decorator(self):
        """Test @subscribes_to_event decorator."""
        @subscribes_to_event("test.user.created")
        @subscribes_to_event("test.user.deleted")
        async def handle_user_events(event):
            return event
        
        assert hasattr(handle_user_events, "_subscribes_to_events")
        assert "test.user.created" in handle_user_events._subscribes_to_events
        assert "test.user.deleted" in handle_user_events._subscribes_to_events


class TestEndToEndIntegration:
    """Test complete end-to-end event flow."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.event_bus = InMemoryEventBus()
    
    @pytest.mark.asyncio
    async def test_complete_event_flow(self):
        """Test complete event flow from schema registration to handler execution."""
        # Create a handler with decorators
        @subscribes_to_event("test.user.created")
        async def user_created_handler(event):
            return {
                "user_id": event.data["user_id"],
                "processed_at": event.timestamp.isoformat(),
                "source": event.source
            }
        
        # Subscribe handler
        await self.event_bus.subscribe("test.user.created", user_created_handler)
        
        # Publish valid event
        user_data = {
            "user_id": 123,
            "username": "newuser",
            "email": "new@example.com"
        }
        
        result = await self.event_bus.publish("test.user.created", user_data, source="UserService")
        
        # Verify result
        assert result["user_id"] == 123
        assert result["source"] == "UserService"
        assert "processed_at" in result
        
        # Verify event in history
        history = self.event_bus.get_event_history("test.user.created")
        assert len(history) == 1
        assert history[0].data == user_data
    
    @pytest.mark.asyncio
    async def test_mixed_validated_unvalidated_events(self):
        """Test mixing validated and unvalidated events."""
        results = []
        
        async def universal_handler(event):
            results.append(event.type)
            return {"handled": event.type}
        
        # Subscribe to both types
        await self.event_bus.subscribe("test.user.created", universal_handler)
        await self.event_bus.subscribe("unregistered.event", universal_handler)
        
        # Publish validated event
        await self.event_bus.publish("test.user.created", {
            "user_id": 123,
            "username": "testuser",
            "email": "test@example.com"
        })
        
        # Publish unvalidated event (should log warning)
        with patch('modules.eventbus.event_bus.logger'):
            await self.event_bus.publish("unregistered.event", {"key": "value"})
        
        # Both should be handled
        assert "test.user.created" in results
        assert "unregistered.event" in results
    
    @pytest.mark.asyncio
    async def test_validation_error_blocks_handlers(self):
        """Test that validation errors prevent handler execution."""
        handler_called = False
        
        async def should_not_be_called(event):
            nonlocal handler_called
            handler_called = True
            return {"called": True}
        
        await self.event_bus.subscribe("test.user.created", should_not_be_called)
        
        # Try to publish invalid data
        with pytest.raises(ValidationError):
            await self.event_bus.publish("test.user.created", {
                "user_id": "invalid",  # Should be int
                "username": "testuser",
                "email": "test@example.com"
            })
        
        # Handler should not have been called
        assert not handler_called
        
        # No event should be in history
        history = self.event_bus.get_event_history("test.user.created")
        assert len(history) == 0