"""
Comprehensive tests for the event_registry module.

Tests cover:
- Event schema registration with decorators
- Schema retrieval and validation
- Data validation against schemas
- Decorator metadata functionality
- Edge cases and error handling
"""

import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ValidationError

from modules.eventbus.event_registry import (
    EventSchema,
    EVENT_REGISTRY,
    register_event_schema,
    get_event_schema,
    validate_event_data,
    list_registered_events,
    publishes_event,
    subscribes_to_event
)


# Test Models
class SimpleEventModel(BaseModel):
    """Simple event model for basic tests"""
    message: str
    count: int


class UserEventModel(BaseModel):
    """User event model with optional fields"""
    user_id: str
    username: str
    email: str
    age: Optional[int] = None
    active: bool = True


class NestedEventModel(BaseModel):
    """Nested model for complex tests"""
    class Address(BaseModel):
        street: str
        city: str
        country: str
    
    event_id: str
    user: UserEventModel
    address: Address
    tags: List[str]
    metadata: Dict[str, Any]


class TimestampedEventModel(BaseModel):
    """Model with datetime field"""
    name: str
    occurred_at: datetime
    duration_ms: float


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the event registry before each test"""
    EVENT_REGISTRY.clear()
    yield
    EVENT_REGISTRY.clear()


class TestEventSchemaRegistration:
    """Test event schema registration functionality"""
    
    def test_basic_registration(self):
        """Test basic schema registration with decorator"""
        @register_event_schema("test.simple")
        class TestEvent(BaseModel):
            value: str
        
        assert "test.simple" in EVENT_REGISTRY
        schema = EVENT_REGISTRY["test.simple"]
        assert schema.name == "test.simple"
        assert schema.model == TestEvent
        assert schema.publisher is None
        assert schema.description is None
    
    def test_registration_with_metadata(self):
        """Test registration with publisher and description"""
        @register_event_schema(
            "user.created",
            publisher="UserService",
            description="Emitted when a new user is created"
        )
        class UserCreatedEvent(BaseModel):
            user_id: str
            email: str
        
        schema = EVENT_REGISTRY["user.created"]
        assert schema.publisher == "UserService"
        assert schema.description == "Emitted when a new user is created"
    
    def test_multiple_registrations(self):
        """Test registering multiple schemas"""
        @register_event_schema("event.one")
        class EventOne(BaseModel):
            field: str
        
        @register_event_schema("event.two")
        class EventTwo(BaseModel):
            value: int
        
        assert len(EVENT_REGISTRY) == 2
        assert "event.one" in EVENT_REGISTRY
        assert "event.two" in EVENT_REGISTRY
    
    def test_override_existing_schema(self, caplog):
        """Test overriding an existing schema logs warning"""
        @register_event_schema("duplicate.event")
        class FirstVersion(BaseModel):
            v1: str
        
        @register_event_schema("duplicate.event")
        class SecondVersion(BaseModel):
            v2: str
        
        # Should have the second version
        schema = EVENT_REGISTRY["duplicate.event"]
        assert schema.model == SecondVersion
        
        # Should have logged a warning
        assert "Overriding existing event schema: duplicate.event" in caplog.text
    
    def test_unicode_event_names(self):
        """Test registration with unicode event names"""
        @register_event_schema("test.événement")
        class UnicodeEvent(BaseModel):
            données: str
        
        assert "test.événement" in EVENT_REGISTRY
    
    def test_complex_nested_models(self):
        """Test registration of complex nested models"""
        @register_event_schema("complex.nested")
        class ComplexEvent(NestedEventModel):
            pass
        
        schema = EVENT_REGISTRY["complex.nested"]
        assert schema.model == ComplexEvent


class TestSchemaRetrieval:
    """Test schema retrieval functions"""
    
    def test_get_existing_schema(self):
        """Test retrieving an existing schema"""
        @register_event_schema("test.event")
        class TestEvent(BaseModel):
            value: str
        
        schema = get_event_schema("test.event")
        assert schema is not None
        assert schema.name == "test.event"
        assert schema.model == TestEvent
    
    def test_get_nonexistent_schema(self):
        """Test retrieving non-existent schema returns None"""
        schema = get_event_schema("does.not.exist")
        assert schema is None
    
    def test_list_all_schemas(self):
        """Test listing all registered schemas"""
        # Register multiple schemas
        @register_event_schema("event.a")
        class EventA(BaseModel):
            a: str
        
        @register_event_schema("event.b", publisher="ServiceB")
        class EventB(BaseModel):
            b: int
        
        @register_event_schema("event.c", description="Event C")
        class EventC(BaseModel):
            c: bool
        
        all_schemas = list_registered_events()
        assert len(all_schemas) == 3
        assert "event.a" in all_schemas
        assert "event.b" in all_schemas
        assert "event.c" in all_schemas
        
        # Verify it returns a copy
        all_schemas.clear()
        assert len(EVENT_REGISTRY) == 3  # Original unchanged


class TestDataValidation:
    """Test event data validation"""
    
    def test_validate_simple_data(self):
        """Test validating simple data against schema"""
        @register_event_schema("simple.event")
        class SimpleEvent(SimpleEventModel):
            pass
        
        data = {"message": "Hello", "count": 42}
        validated = validate_event_data("simple.event", data)
        
        assert isinstance(validated, SimpleEventModel)
        assert validated.message == "Hello"
        assert validated.count == 42
    
    def test_validate_with_optional_fields(self):
        """Test validation with optional fields and defaults"""
        @register_event_schema("user.event")
        class UserEvent(UserEventModel):
            pass
        
        # Without optional field
        data = {
            "user_id": "123",
            "username": "testuser",
            "email": "test@example.com"
        }
        validated = validate_event_data("user.event", data)
        assert validated.age is None
        assert validated.active is True  # Default value
        
        # With optional field
        data["age"] = 25
        data["active"] = False
        validated = validate_event_data("user.event", data)
        assert validated.age == 25
        assert validated.active is False
    
    def test_validate_nested_data(self):
        """Test validating nested data structures"""
        @register_event_schema("nested.event")
        class NestedEvent(NestedEventModel):
            pass
        
        data = {
            "event_id": "evt123",
            "user": {
                "user_id": "usr456",
                "username": "testuser",
                "email": "test@example.com"
            },
            "address": {
                "street": "123 Main St",
                "city": "Test City",
                "country": "Testland"
            },
            "tags": ["important", "user-event"],
            "metadata": {"source": "api", "version": 2}
        }
        
        validated = validate_event_data("nested.event", data)
        assert validated.event_id == "evt123"
        assert validated.user.username == "testuser"
        assert validated.address.city == "Test City"
        assert len(validated.tags) == 2
        assert validated.metadata["version"] == 2
    
    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        @register_event_schema("required.event")
        class RequiredEvent(BaseModel):
            required_field: str
            optional_field: Optional[str] = None
        
        data = {"optional_field": "value"}  # Missing required_field
        
        with pytest.raises(ValidationError) as exc_info:
            validate_event_data("required.event", data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("required_field",)
        assert errors[0]["type"] == "missing"
    
    def test_validate_wrong_types(self):
        """Test validation fails for wrong types"""
        @register_event_schema("typed.event")
        class TypedEvent(BaseModel):
            count: int
            ratio: float
            active: bool
        
        data = {
            "count": "not a number",  # Wrong type
            "ratio": 3.14,
            "active": True
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_event_data("typed.event", data)
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("count",) for e in errors)
    
    def test_validate_extra_fields(self):
        """Test validation with extra fields (should be ignored by default)"""
        @register_event_schema("strict.event")
        class StrictEvent(BaseModel):
            allowed_field: str
        
        data = {
            "allowed_field": "value",
            "extra_field": "should be ignored"
        }
        
        validated = validate_event_data("strict.event", data)
        assert validated.allowed_field == "value"
        assert not hasattr(validated, "extra_field")
    
    def test_validate_datetime_fields(self):
        """Test validation of datetime fields"""
        @register_event_schema("timed.event")
        class TimedEvent(TimestampedEventModel):
            pass
        
        now = datetime.utcnow()
        data = {
            "name": "test",
            "occurred_at": now.isoformat(),
            "duration_ms": 123.45
        }
        
        validated = validate_event_data("timed.event", data)
        assert validated.name == "test"
        assert isinstance(validated.occurred_at, datetime)
        assert validated.duration_ms == 123.45
    
    def test_validate_nonexistent_schema(self):
        """Test validation fails for non-existent schema"""
        with pytest.raises(ValueError) as exc_info:
            validate_event_data("does.not.exist", {"any": "data"})
        
        assert "No schema registered for event type: does.not.exist" in str(exc_info.value)


class TestDecorators:
    """Test decorator functionality"""
    
    def test_publishes_event_decorator(self):
        """Test @publishes_event decorator"""
        @publishes_event("user.created")
        @publishes_event("audit.logged")
        async def create_user(user_data):
            return {"user_id": "123"}
        
        assert hasattr(create_user, "_publishes_events")
        assert "user.created" in create_user._publishes_events
        assert "audit.logged" in create_user._publishes_events
        assert len(create_user._publishes_events) == 2
    
    def test_subscribes_to_event_decorator(self):
        """Test @subscribes_to_event decorator"""
        @subscribes_to_event("user.created")
        @subscribes_to_event("user.updated")
        async def handle_user_events(event):
            pass
        
        assert hasattr(handle_user_events, "_subscribes_to_events")
        assert "user.created" in handle_user_events._subscribes_to_events
        assert "user.updated" in handle_user_events._subscribes_to_events
    
    def test_decorator_on_class_method(self):
        """Test decorators on class methods"""
        class EventHandler:
            @publishes_event("task.completed")
            def complete_task(self, task_id):
                return task_id
            
            @subscribes_to_event("task.assigned")
            def on_task_assigned(self, event):
                pass
        
        handler = EventHandler()
        assert hasattr(handler.complete_task, "_publishes_events")
        assert hasattr(handler.on_task_assigned, "_subscribes_to_events")
    
    def test_decorator_preserves_function(self):
        """Test decorator preserves original function"""
        def original_function(x, y):
            """Original docstring"""
            return x + y
        
        decorated = publishes_event("test.event")(original_function)
        
        # Function still works
        assert decorated(2, 3) == 5
        
        # Preserves attributes
        assert decorated.__name__ == "original_function"
        assert decorated.__doc__ == "Original docstring"
    
    def test_mixed_decorators(self):
        """Test function with both decorators"""
        @publishes_event("result.computed")
        @subscribes_to_event("input.received")
        def process_data(data):
            return data.upper()
        
        assert hasattr(process_data, "_publishes_events")
        assert hasattr(process_data, "_subscribes_to_events")
        assert "result.computed" in process_data._publishes_events
        assert "input.received" in process_data._subscribes_to_events


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_empty_registry_operations(self):
        """Test operations on empty registry"""
        assert len(EVENT_REGISTRY) == 0
        assert list_registered_events() == {}
        assert get_event_schema("any.event") is None
    
    def test_event_schema_dataclass(self):
        """Test EventSchema dataclass behavior"""
        model = SimpleEventModel
        schema = EventSchema(
            name="test.schema",
            model=model,
            publisher="TestPublisher",
            description="Test description"
        )
        
        assert schema.name == "test.schema"
        assert schema.model == model
        assert schema.publisher == "TestPublisher"
        assert schema.description == "Test description"
    
    def test_schema_with_none_metadata(self):
        """Test schema with None publisher/description"""
        schema = EventSchema(
            name="minimal.schema",
            model=SimpleEventModel
        )
        
        assert schema.publisher is None
        assert schema.description is None
    
    def test_complex_validation_errors(self):
        """Test detailed validation error information"""
        @register_event_schema("complex.validation")
        class ComplexValidation(BaseModel):
            numbers: List[int]
            mapping: Dict[str, float]
            nested: Dict[str, List[int]]
        
        data = {
            "numbers": [1, "two", 3],  # Invalid item
            "mapping": {"a": 1.5, "b": "not a float"},  # Invalid value
            "nested": {"x": [1, 2], "y": "not a list"}  # Invalid type
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_event_data("complex.validation", data)
        
        errors = exc_info.value.errors()
        assert len(errors) >= 3  # At least 3 validation errors
    
    def test_decorator_multiple_applications(self):
        """Test applying same decorator multiple times"""
        @publishes_event("event.one")
        @publishes_event("event.one")  # Duplicate
        def duplicate_publisher():
            pass
        
        # Should have both entries (duplicates allowed)
        assert duplicate_publisher._publishes_events.count("event.one") == 2


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def test_event_workflow_registration(self):
        """Test registering events for a complete workflow"""
        # User service events
        @register_event_schema("user.created", publisher="UserService")
        class UserCreated(BaseModel):
            user_id: str
            email: str
            created_at: datetime
        
        @register_event_schema("user.verified", publisher="UserService")
        class UserVerified(BaseModel):
            user_id: str
            verified_at: datetime
        
        # Email service events
        @register_event_schema("email.sent", publisher="EmailService")
        class EmailSent(BaseModel):
            recipient: str
            subject: str
            sent_at: datetime
        
        # Verify all registered
        schemas = list_registered_events()
        assert len(schemas) == 3
        assert all(name in schemas for name in ["user.created", "user.verified", "email.sent"])
    
    def test_service_with_event_methods(self):
        """Test a service class with event publishing/subscribing methods"""
        class UserService:
            @publishes_event("user.created")
            @publishes_event("audit.user_action")
            async def create_user(self, email: str) -> str:
                # Would publish events here
                return f"user_{email.split('@')[0]}"
            
            @subscribes_to_event("user.verification_requested")
            async def handle_verification_request(self, event):
                # Would handle event here
                pass
            
            @publishes_event("user.deleted")
            @subscribes_to_event("user.deletion_requested")
            async def delete_user(self, user_id: str):
                # Both publishes and subscribes
                pass
        
        service = UserService()
        
        # Verify metadata
        assert len(service.create_user._publishes_events) == 2
        assert len(service.handle_verification_request._subscribes_to_events) == 1
        assert hasattr(service.delete_user, "_publishes_events")
        assert hasattr(service.delete_user, "_subscribes_to_events")