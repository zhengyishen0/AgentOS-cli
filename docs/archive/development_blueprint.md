# Complete Software Development Blueprint

## Table of Contents
1. [Design Philosophy](#design-philosophy)
2. [Project Structure](#project-structure)
3. [Development Process](#development-process)
4. [Configuration Files](#configuration-files)
5. [Testing Strategy](#testing-strategy)
6. [Development Workflow](#development-workflow)
7. [Commands Reference](#commands-reference)
8. [Architecture Decision Framework](#architecture-decision-framework)
9. [Service Factory Pattern](#service-factory-pattern)
10. [Event System & Auto-Schema Generation](#event-system--auto-schema-generation)
11. [Naming Conventions](#naming-conventions)

## Design Philosophy

### Three Layers of Design
1. **Product Design**: Top-level design defining the problem and major solutions
2. **Architecture Design**: High-level design defining key modules, their functions, and how they work together
3. **Detailed Design**: Low-level design describing interfaces, key functions/classes, and behaviors

### Three Layers of Module Architecture
Each module can implement up to three architectural layers based on complexity:

1. **Core Function**: Pure business logic (stateless when possible)
2. **Wrapper Chain**: Cross-cutting concerns including persistence, caching, validation
3. **Service Integration**: Composition layer that orchestrates core + wrapper chains for production features

Start with Core only, add layers as needed.

### Key Design Principles

1. **Direct Implementation**: Prefer self-contained components over abstract interfaces. Each component should directly implement its functionality rather than delegating through abstractions.

2. **Composition over Abstraction**: Use direct wrappers that can be composed into chains. This allows flexible feature addition without modifying existing code.

3. **Progressive Enhancement**: Start simple, add complexity only when needed. Use wrappers to add cross-cutting concerns (caching, monitoring, retry) without touching core logic.

4. **Explicit Dependencies**: Components declare what they need in their constructor. No hidden dependencies or global state.

5. **Core Type Declaration**: Explicitly declare whether core components are stateless functions or stateful services for predictable behavior and proper lifecycle management.

## Project Structure

```
project/
├── docs/
│   ├── product_design.md        # Problem & solution overview
│   ├── architecture.md          # System design decisions and interface specs
│   └── event_schemas.md         # EventBus event schemas and contracts
│
├── core/                        # Core architectural components
│   ├── __init__.py
│   ├── interfaces.py           # Protocol definitions with contracts and contract test bases
│   ├── base_service.py         # Universal service base class and wrapper chain
│   ├── service_factory.py     # Service factory for consistent dependency injection
│   ├── event_bus.py           # Event bus implementation for inter-module communication
│   └── exceptions.py          # Domain exception hierarchy
│
├── shared/                     # Generic utilities (no architectural opinions)
│   ├── __init__.py
│   ├── types.py               # Universal type aliases (ID, Metadata)
│   ├── utilities.py           # Pure utility functions (generate_id, deep_merge)
│   ├── decorators.py          # Generic decorators (retry, timed, validate_input)
│   └── mixins.py              # Generic class behaviors (TimestampMixin, CacheKeyMixin)
│
├── modules/                    # Business logic, organized by domain
│   ├── __init__.py
│   └── {domain}/              # e.g., users, payments, orders
│       ├── __init__.py
│       ├── interfaces.py      # Domain-specific protocols
│       ├── models.py          # Pydantic models for validation
│       ├── core/              # Core functionality (functions or services)
│       │   ├── __init__.py
│       │   └── {specific_cores}.py
│       ├── wrappers/          # Domain-specific wrappers (Layer 2)
│       │   ├── persistence_wrapper.py  # Persistence operations
│       │   ├── validation_wrapper.py   # Domain validation
│       │   └── {domain}_wrapper.py     # Business-specific logic
│       ├── service.py         # Integration & orchestration (Layer 3)
│       └── validators.py      # Domain-specific validators
│
├── extensions/               # Hot-reloadable system capabilities (optional)
│   ├── core/
│   │   ├── extension_runtime.py  # Extension execution engine
│   │   └── hot_reload.py         # Extension lifecycle management
│   ├── repository.py         # Extension registration and lifecycle
│   └── service.py            # EventBus integration
│
├── tests/                     # Testing goals:
│   ├── unit/                 # Pure function tests for core logic
│   ├── contracts/            # Protocol compliance tests
│   ├── properties/           # Property-based tests
│   ├── integration/          # Multi-component workflow tests
│   ├── events/              # Event flow tests
│   └── e2e/                 # End-to-end scenario validation
│
├── scripts/                  # Development/deployment scripts
├── Makefile                 # Common commands
├── pyproject.toml           # Project configuration
└── .pre-commit-config.yaml  # Pre-commit hooks
```

### Core vs Shared Organization

**core/**: Contains architectural components and domain-specific contracts
- **interfaces.py**: Domain protocols and contracts  
- **base_service.py**: Universal service architecture foundation
- **service_factory.py**: Dependency injection and service creation patterns
- **event_bus.py**: Inter-module communication infrastructure  
- **exceptions.py**: Domain error hierarchy and patterns

**shared/**: Contains generic, reusable utilities with no architectural opinions
- **types.py**: Basic type aliases (ID, Metadata)
- **utilities.py**: Pure utility functions (generate_id, deep_merge, chunk_list)
- **decorators.py**: Generic decorators (retry, timed, validate_input)  
- **mixins.py**: Generic class behaviors (TimestampMixin, CacheKeyMixin, SerializableMixin)

**Key principle**: If it has domain/architectural knowledge → **core/**, if it's a pure utility → **shared/**

## Development Process

### Phase 1: Product Design

Create `docs/product_design.md` documenting:
- Problem statement and user needs
- Proposed solution and key features
- Success criteria and constraints
- Major technical decisions

### Phase 2: Architecture Design

Create `docs/architecture.md` documenting:
- System overview and goals
- Core components and their responsibilities
- Data flow between components
- Key architectural decisions and rationale
- Technology stack choices

### Phase 3: Core Interface Design

**Design Principle**: Define minimal contracts for shared behaviors. Use direct implementation in wrappers for cross-cutting concerns.

Define shared abstractions in `core/interfaces.py`:

```python
from typing import Protocol, TypeVar, Any
from enum import Enum
import pytest

T = TypeVar('T')

# Core type declaration system
class CoreType(Enum):
    FUNCTION = "function"    # Stateless, pure functions
    SERVICE = "service"      # Stateful, long-running processes

class CoreBase:
    core_type: CoreType

class FunctionCore(CoreBase):
    core_type = CoreType.FUNCTION
    # Pure functions: calculations, transformations, validations
    
class ServiceCore(CoreBase):
    core_type = CoreType.SERVICE
    async def start(self): ...
    async def stop(self): ...
    async def health_check(self): ...

# Minimal protocols for core behaviors
class Repository(Protocol[T]):
    """Base repository contract. Repository is for business entities, like Users, Orders, etc."""
    async def find(self, id: str) -> T | None: ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, id: str) -> bool: ...

class Registry(Protocol[T]):
    """Resource registry contract. Registry is for resources, like files, plugins, templates, configs, etc."""
    async def load_from_file(self, path: Path) -> T: ...
    async def list_available(self) -> list[str]: ...
    async def list_active(self) -> list[T]: ...
    async def reload(self, resource_id: str) -> T: ...
    async def unload(self, resource_id: str) -> bool: ...

class EventBus(Protocol):
    """Event publishing contract."""
    async def publish(self, event_type: str, data: dict[str, Any]) -> None: ...
    async def subscribe(self, event_type: str, handler: Callable) -> None: ...

# Base wrapper interface
class Wrapper(Protocol):
    """All wrappers implement this."""
    async def wrap(self, next_func: Callable, *args, **kwargs) -> Any: ...
```

Define exceptions in `core/exceptions.py`:

```python
class DomainError(Exception): pass
class ValidationError(DomainError): pass
class NotFoundError(DomainError): pass
```

Define mixins in `core/mixins.py`:

```python
class TimestampMixin:
    created_at: float
    updated_at: float
    
class CacheKeyMixin:
    @staticmethod
    def cache_key(namespace: str, *args) -> str: ...
```

### Phase 4: Module Design

For each domain module, implement the appropriate layers:

#### Layer 1: Core Function (Always Required)

Define core business logic with explicit type declaration in `modules/{domain}/core/`:

```python
# modules/payment/core/payment_processor.py
class PaymentProcessor(FunctionCore):
    """Pure payment processing logic - stateless."""
    
    def calculate_fee(self, amount: Decimal) -> Decimal: ...
    def validate_payment(self, request: PaymentRequest) -> ValidationResult: ...
    async def process_transaction(self, request: PaymentRequest, gateway: PaymentGateway) -> TransactionResult: ...

# modules/notification/core/email_service.py  
class EmailService(ServiceCore):
    """Stateful email service with connection pooling."""
    
    def __init__(self):
        self.connection_pool = None
        self.is_running = False
    
    async def start(self):
        self.connection_pool = await create_smtp_pool()
        self.is_running = True
    
    async def stop(self):
        await self.connection_pool.close()
        self.is_running = False
```

#### Layer 2: Wrapper Chain (When Cross-Cutting Concerns Needed)

Implement domain-specific wrappers in `modules/{domain}/wrappers/`:

```python
# modules/payment/wrappers/persistence_wrapper.py
class PaymentPersistenceWrapper:
    """Payment persistence operations as wrapper."""
    
    def __init__(self, storage: PaymentStorage):
        self.storage = storage
    
    async def wrap(self, operation: ServiceOperation, context: OperationContext, next_func: Callable, *args, **kwargs) -> Any:
        if operation == ServiceOperation.CREATE:
            entity = args[0]
            # Persist entity
            saved = await self.storage.save(entity)
            # Continue chain with saved entity
            return await next_func(saved, **kwargs)
        elif operation == ServiceOperation.READ:
            entity_id = args[0]
            entity = await self.storage.find(entity_id)
            if entity:
                return await next_func(entity, **kwargs)
            return None
        else:
            return await next_func(*args, **kwargs)

# modules/payment/wrappers/validation_wrapper.py  
class PaymentValidationWrapper:
    """Payment validation as wrapper."""
    
    async def wrap(self, operation: ServiceOperation, context: OperationContext, next_func: Callable, *args, **kwargs) -> Any:
        if operation in [ServiceOperation.CREATE, ServiceOperation.UPDATE]:
            entity = args[0]
            # Validate payment rules
            if not self._validate_payment(entity):
                raise ValidationError("Invalid payment data")
        return await next_func(*args, **kwargs)
```

#### Layer 3: Service Integration (When Production Features Needed)

Orchestrate in `modules/{domain}/service.py` using BaseService:

```python
class PaymentService(BaseService[Payment]):
    """Payment service with wrapper-based architecture."""
    
    def __init__(
        self, 
        core: PaymentProcessor,
        event_bus: EventBus,
        wrappers: list[EnhancedWrapper] = None,
        config: dict[str, Any] = None
    ):
        # Initialize base service without repository
        super().__init__(
            core=core,
            repository=None,  # No separate repository - handled by wrappers
            event_bus=event_bus,
            wrappers=wrappers or [],
            config=config
        )
    
    async def _process(self, request: PaymentRequest, **kwargs) -> PaymentResult:
        """Process payment through wrapper chain."""
        # Core business logic - wrapper chain handles persistence, validation, etc.
        result = await self.core.process_transaction(request)
        
        # Publish domain event
        if self.event_bus:
            await self.event_bus.publish("payment.processed", {
                "payment_id": result.id,
                "amount": result.amount,
                "user_id": result.user_id
            })
        
        return PaymentResult.from_payment(result)
    
    def setup_event_handlers(self):
        """Setup domain-specific event handlers."""
        if self.event_bus:
            self.event_bus.subscribe("order.created", self.handle_order_created)
    
    async def handle_order_created(self, event_data: dict):
        """Handle order creation events."""
        order_id = event_data["order_id"]
        # Process payment for order
        await self.process_payment_for_order(order_id)
```

### Phase 4.5: Event-Driven Integration (When Inter-Module Communication Needed)

For systems requiring loose coupling between modules, implement event-driven communication:

```python
# modules/{domain}/service.py - Event integration
class PaymentService:
    def __init__(self, core, repository, event_bus: EventBus):
        self.event_bus = event_bus
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        self.event_bus.subscribe("order.created", self.handle_order_created)
        self.event_bus.subscribe("refund.requested", self.handle_refund_requested)
    
    async def process_payment(self, request):
        result = await self.core.process_transaction(request)
        await self.event_bus.publish("payment.processed", {
            "payment_id": result.id,
            "amount": result.amount
        })
        return result

    async def handle_order_created(self, event_data):
        """React to order creation events"""
        order_id = event_data["order_id"]
        await self.process_payment_for_order(order_id)
```

**Benefits**: Loose coupling, scalable communication, easier testing

**Event Schema Documentation**: All event schemas and contracts are documented in `docs/event_schemas.md`. This provides:
- Event structure definitions with required/optional fields
- Publisher/subscriber relationships
- Example payloads and usage patterns  
- Naming conventions and best practices

### Phase 4.6: Hot-Reload Pattern (For Dynamic Extensions)

For systems requiring runtime extensibility without restart:

```python
# extensions/repository.py
class ExtensionRepository:
    def __init__(self, event_bus: EventBus):
        self.loaded_extensions = {}
        self.event_bus = event_bus
        self.watch_extension_configs()
    
    async def hot_reload_extension(self, ext_name):
        """Reload extension without system restart"""
        await self.unload_extension(ext_name)
        await self.load_extension(ext_name)
        
        # Notify system of changes
        await self.event_bus.publish("extension.reloaded", {
            "extension_name": ext_name,
            "capabilities": self.get_extension_capabilities(ext_name)
        })

# Usage example
async def setup_extensions():
    extensions = ExtensionRepository(event_bus)
    await extensions.hot_reload_extension("task_manager")
```

**Use cases**: Plugin systems, feature flags, A/B testing, runtime configuration

##### Where Things Belong

**Core (Pure Business Logic)**
- Domain-specific logic

**Service Dependencies (Orchestration)**
- Event Bus (publish events to other services)
- Config (application settings)
- Wrapper Chain (composed behaviors)

**Wrappers (All Cross-Cutting Concerns)**
- Data persistence: saving, loading, querying
- Before/after operations: caching, logging, metrics
- Conditional execution: auth, fraud detection, rate limiting
- Error handling: retry, circuit breaker
- Transaction management
- Domain validation: business rules, constraints

**Rule**: If it's "do X before/after operation" → Wrapper. If it's core business logic → Core. If it's communication with other services → Event Bus.

##### Wrapper Pattern for Cross-Cutting Concerns

Create reusable wrappers in `shared/wrappers/` for generic concerns and `modules/{domain}/wrappers/` for domain-specific needs:

```python
class CacheWrapper:
    """Direct Redis implementation."""
    def __init__(self, redis_client, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl
    
    async def wrap(self, next_func: Callable, *args, **kwargs) -> Any:
        key = self._make_key(*args)
        cached = await self.redis.get(key)
        if cached:
            return pickle.loads(cached)
        
        result = await next_func(*args, **kwargs)
        await self.redis.setex(key, self.ttl, pickle.dumps(result))
        return result

class RetryWrapper:
    """Retry with exponential backoff."""
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    async def wrap(self, next_func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            try:
                return await next_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

# Example usage of Wrappers in Service
async def setup_payment_service():
    core = PaymentProcessor()
    storage = PaymentStorage(database)
    
    # Compose wrappers for production features
    wrappers = [
        CacheWrapper(redis_client, ttl=300),                    # 5-minute cache
        RetryWrapper(max_retries=3),                            # Retry on failure
        MonitoringWrapper(metrics_client),                      # Track performance
        LoggingWrapper(logger),                                 # Audit trail
        PaymentPersistenceWrapper(storage),                     # Domain persistence
        PaymentValidationWrapper(),                             # Domain validation
    ]
    
    return PaymentService(core, event_bus, wrappers)

# The service automatically applies all wrappers in the correct order
# Each wrapper can add its behavior without modifying the core logic
# The first wrapper in the list is the outermost:
# Request → [CacheWrapper → RetryWrapper → MonitoringWrapper → LoggingWrapper → PaymentPersistenceWrapper → PaymentValidationWrapper → Core] → Response
```

**Creating Custom Wrappers**

```python
class MyWrapper:
    async def wrap(self, next_func, *args, **kwargs):
        # Before logic
        result = await next_func(*args, **kwargs)  # Call next
        # After logic
        return result
```

### Phase 5: Write Tests First

Test each layer appropriately:

1. **Core Tests** (`tests/unit/`):
```python
def test_payment_calculation():
    core = PaymentProcessor()
    assert core.calculate_fee(Decimal("100")) == Decimal("3.20")
```

2. **Repository Tests** (`tests/integration/`):
```python
async def test_payment_repository():
    repo = PaymentRepository(test_db)
    saved = await repo.save(Payment(amount=100))
    assert saved.id is not None
```

3. **Wrapper Tests** (`tests/unit/wrappers/`):
```python
async def test_cache_wrapper():
    wrapper = CacheWrapper(mock_redis)
    result = await wrapper.wrap(mock_func, "arg1")
    assert mock_redis.get_called
```

4. **Service Tests** (`tests/integration/`):
```python
async def test_payment_service_full_stack():
    service = PaymentService(core, repo, [cache, retry, monitor])
    result = await service.process_payment(request)
    assert result.status == "completed"
```

### Phase 6: Implementation

Implement incrementally:
1. Start with Core layer only
2. Add Repository when persistence is needed
3. Add Service when production features are needed

## Configuration Files

### pyproject.toml

Initialize with Poetry:
```bash
poetry new your-project-name
poetry add pydantic fastapi sqlalchemy
poetry add --group dev pytest pytest-asyncio mypy black ruff hypothesis
```

Then configure in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.11"
strict = true

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Makefile

Create a simple `Makefile` for common tasks:
```makefile
.PHONY: install test lint format all

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run ruff .
	poetry run mypy .

format:
	poetry run black .
	poetry run ruff --fix .

all: lint test
```

### .pre-commit-config.yaml

Install and configure pre-commit:
```bash
pip install pre-commit
pre-commit sample-config > .pre-commit-config.yaml
pre-commit install
```

Then customize for your project:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: stable
    hooks:
      - id: black

  - repo: https://github.com/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## Testing Strategy

### Error Prevention Strategy

To catch errors at different stages:
1. **Use type hints for static type checks** - Catches type mismatches at development time
2. **Use Pydantic for complex data or external data** - Runtime validation at boundaries
3. **Use contract tests for interfaces** - Ensures implementations follow expected behavior contracts
4. **Use property tests for business rules** - Validates invariants and edge cases with generated data
5. **Use unit tests for different layers in each module** - Tests pure logic, integration, and isolation scenarios

### Test Types by Layer

#### 1. Core Layer Tests (Unit)
Pure business logic tests with no I/O:
```python
def test_calculate_fee():
    core = PaymentProcessor()
    assert core.calculate_fee(Decimal("100")) == Decimal("3.20")

def test_validate_payment():
    core = PaymentProcessor()
    result = core.validate_payment(invalid_request)
    assert not result.is_valid
```

#### 2. Repository/Registry Tests (Contract + Integration)
Test CRUD operations and persistence:
```python
class TestPaymentRepository:
    async def test_save_generates_id(self, repository):
        payment = Payment(amount=100)
        saved = await repository.save(payment)
        assert saved.id is not None
    
    async def test_find_by_id(self, repository):
        saved = await repository.save(Payment(amount=100))
        found = await repository.find(saved.id)
        assert found.amount == 100
```

#### 3. Wrapper Tests (Isolation)
Test each wrapper independently with mock functions:
```python
async def test_retry_wrapper():
    """Test retry logic without real service."""
    call_count = 0
    
    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary error")
        return "success"
    
    wrapper = RetryWrapper(max_retries=3)
    result = await wrapper.wrap(flaky_func)
    assert result == "success"
    assert call_count == 3

async def test_cache_wrapper():
    """Test caching behavior."""
    call_count = 0
    cache_storage = {}
    
    async def expensive_func(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # Mock redis client
    mock_redis = MockRedis(cache_storage)
    wrapper = CacheWrapper(mock_redis)
    
    # First call - miss
    result1 = await wrapper.wrap(expensive_func, 5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call - hit
    result2 = await wrapper.wrap(expensive_func, 5)
    assert result2 == 10
    assert call_count == 1  # No additional calls
```

#### 4. Service Integration Tests
Test the complete chain with real components:
```python
async def test_payment_service_with_wrappers():
    """Test service with multiple wrappers."""
    service = PaymentService(
        core=PaymentProcessor(),
        repository=InMemoryRepository(),
        wrappers=[
            MetricsWrapper(),
            CacheWrapper(MockRedis()),
            RetryWrapper(max_retries=2)
        ]
    )
    
    result = await service.process_payment(valid_request)
    assert result.status == "completed"
```

#### 5. Wrapper Composition Tests
Test that wrapper order matters and compositions work:
```python
async def test_wrapper_order():
    """Verify cache inside retry vs retry inside cache."""
    # Cache inside retry - retries check cache
    service1 = PaymentService(
        core=core,
        repository=repo,
        wrappers=[RetryWrapper(), CacheWrapper(redis)]
    )
    
    # Retry inside cache - cache stores failures
    service2 = PaymentService(
        core=core,
        repository=repo,
        wrappers=[CacheWrapper(redis), RetryWrapper()]
    )
    
    # Test different behaviors...
```

#### 6. Event Flow Tests
Test complete event-driven workflows:
```python
async def test_event_flow():
    """Test end-to-end event processing"""
    event_bus = TestEventBus()
    
    # Setup services with test event bus
    payment_service = PaymentService(core, repo, event_bus)
    order_service = OrderService(core, repo, event_bus)
    
    # Trigger initial event
    await event_bus.publish("order.created", {"order_id": "123"})
    
    # Verify event chain completion
    events = event_bus.get_published_events()
    assert "payment.processed" in [e.type for e in events]
    assert "order.completed" in [e.type for e in events]
```

#### 7. Hot-Reload Tests
Test dynamic extension loading:
```python
async def test_extension_hot_reload():
    """Test extension reload without system restart"""
    ext_repo = ExtensionRepository(event_bus)
    
    # Load initial extension
    await ext_repo.load_extension("test_extension_v1")
    result1 = await ext_repo.execute("test_extension", {"input": "test"})
    
    # Hot reload to new version
    await ext_repo.hot_reload_extension("test_extension_v2")
    result2 = await ext_repo.execute("test_extension", {"input": "test"})
    
    assert result1 != result2  # Behavior changed after reload
```

### Testing Philosophy

- **Test behavior, not implementation**
- **Test wrappers in isolation with simple mocks**
- **Test wrapper combinations for integration**
- **Use real implementations when fast**
- **Each test should tell a story**

## Development Workflow

### Initial Setup
```bash
# Clone and setup
git clone <repository>
cd project
make install
pre-commit install
```

### Daily Development
```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Design (if new module)
#    - Update product_design.md if needed
#    - Update architecture.md for new modules
#    - Plan which layers are needed

# 3. Write interfaces and contracts
# 4. Write tests first
# 5. Implement feature (start with core layer)

# 6. Run checks locally
make all

# 7. Commit (pre-commit runs)
git commit -m "Add feature"

# 8. Push (CI runs)
git push origin feature/new-feature
```

### Adding a New Module
```bash
# 1. Create module structure
mkdir -p modules/new_domain/core
touch modules/new_domain/{__init__,interfaces,models}.py
touch modules/new_domain/core/{__init__,business_logic}.py

# 2. Start with core layer only
# 3. Add repository.py when persistence needed
# 4. Add service.py when production features needed
```

## Commands Reference

### Essential Commands
| Command | Purpose |
|---------|---------|
| `make install` | Install all dependencies |
| `make test` | Run all tests |
| `make type-check` | Check type hints |
| `make format` | Format code automatically |
| `make lint` | Check code style |
| `make all` | Run all checks before commit |

### Test Commands
| Command | Purpose |
|---------|---------|
| `make test-unit` | Test pure functions |
| `make test-contracts` | Test behavioral contracts |
| `make test-properties` | Run property tests |
| `make test-integration` | Test component integration |
| `make test-events` | Test event flows |

### Development Commands
| Command | Purpose |
|---------|---------|
| `make dev` | Run tests in verbose mode |
| `make coverage` | Generate coverage report |
| `poetry shell` | Activate virtual environment |
| `poetry run python` | Run Python in environment |

## Architecture Decision Framework

### Choosing Architecture Patterns

**Single Module System**: Use three-layer pattern only
- Core for business logic
- Repository for persistence  
- Service for external integrations

**Multi-Module System**: Add event-driven communication
- EventBus for loose coupling
- Pydantic event schemas with automatic validation
- Event registry with decorator-based registration
- Event flow testing for integration validation

**Extensible System**: Add hot-reload capabilities
- Extension repository for dynamic loading
- Core type declaration for predictable behavior
- Event-driven extension coordination

### Decision Matrix

| System Complexity | Pattern | Use When |
|------------------|---------|----------|
| Single domain | Three-layer | Focused, standalone applications |
| Multiple domains | Event-driven | Microservices, modular monoliths |
| Runtime extensibility | Hot-reload | Plugin systems, configurable platforms |

## Service Factory Pattern

### Overview

The Service Factory provides centralized service creation with consistent wrapper configurations across environments. It orchestrates the three-layer architecture (Core → Repository → Service) and manages environment-specific wrapper chains.

### Design Principles

1. **Centralized Configuration**: All wrapper management happens in one place
2. **Environment-Aware**: Different wrapper combinations for development, production, and testing
3. **Consistent Interface**: All services get created the same way regardless of complexity
4. **Flexible Composition**: Supports additional service-specific wrappers

### Implementation

#### Core Factory Class

Located in `core/service_factory.py`:

```python
from typing import Type, TypeVar, Dict, Any, List, Optional
from core.interfaces import EventBus
from core.base_service import BaseService
from core.interfaces import EnhancedWrapper as Wrapper

S = TypeVar('S', bound=BaseService)

class ServiceFactory:
    """Factory for creating services with consistent wrapper configurations."""
    
    def __init__(self):
        self.default_wrappers: List[Wrapper] = []
        self.environment_wrappers: Dict[str, List[Wrapper]] = {}
    
    def set_default_wrappers(self, wrappers: List[Wrapper]):
        """Set default wrappers for all services."""
        self.default_wrappers = wrappers
    
    def set_environment_wrappers(self, env: str, wrappers: List[Wrapper]):
        """Set environment-specific wrappers."""
        self.environment_wrappers[env] = wrappers
    
    def create_service(
        self, 
        service_class: Type[S],
        core,
        repository=None,
        event_bus: Optional[EventBus] = None,
        additional_wrappers: Optional[List[Wrapper]] = None,
        environment: str = "production",
        config: Optional[Dict[str, Any]] = None
    ) -> S:
        """Create service with appropriate wrappers."""
        
        # Combine wrappers in order: default + environment + additional
        all_wrappers = (
            self.default_wrappers + 
            self.environment_wrappers.get(environment, []) +
            (additional_wrappers or [])
        )
        
        return service_class(
            core=core,
            repository=repository,
            event_bus=event_bus,
            wrappers=all_wrappers,
            config=config
        )

# Global factory instance
service_factory = ServiceFactory()

def create_service(service_class, core, repository=None, **kwargs) -> S:
    """Convenience function using global factory."""
    return service_factory.create_service(service_class, core, repository, **kwargs)
```

#### Application Setup

Configure the factory at application startup:

```python
# main.py or app.py
async def setup_services():
    """Configure service factory and create services."""
    
    # Create shared dependencies
    event_bus = EventBus()
    redis_client = await create_redis_client()
    metrics_client = MetricsClient()
    auth_service = AuthService()
    
    # Configure factory with default wrappers for all services
    service_factory.set_default_wrappers([
        AuthWrapper(auth_service),           # Authentication
        MonitoringWrapper(metrics_client),   # Metrics collection
        LoggingWrapper(logger),             # Audit logging
    ])
    
    # Set environment-specific wrappers
    service_factory.set_environment_wrappers("production", [
        CacheWrapper(redis_client, ttl=300),    # 5-minute cache
        RetryWrapper(max_retries=3),            # Retry on failures
        CircuitBreakerWrapper(),                # Circuit breaker
        RateLimitWrapper(requests_per_minute=100),
    ])
    
    service_factory.set_environment_wrappers("development", [
        DebugWrapper(),                         # Debug information
        MockWrapper(),                          # Mock external services
    ])
    
    service_factory.set_environment_wrappers("testing", [
        # Minimal wrappers for fast tests
    ])
    
    return service_factory
```

### Module Integration

#### Module Factory Functions

Each module provides environment-specific factory functions:

```python
# modules/payment/__init__.py
from core import create_service
from .core.payment_processor import PaymentProcessor
from .repository import PaymentRepository
from .service import PaymentService
from .wrappers.fraud_detection import FraudDetectionWrapper
from .wrappers.idempotency import IdempotencyWrapper

def create_development_payment_service(
    event_bus: EventBus,
    additional_wrappers: Optional[List[Wrapper]] = None
) -> PaymentService:
    """Create payment service for development."""
    core = PaymentProcessor()
    repository = PaymentRepository(database)
    
    # Domain-specific wrappers
    domain_wrappers = [
        FraudDetectionWrapper(threshold=0.1),  # Lower threshold for dev
    ]
    
    return create_service(
        service_class=PaymentService,
        core=core,
        repository=repository,
        event_bus=event_bus,
        additional_wrappers=domain_wrappers + (additional_wrappers or []),
        environment="development"
    )

def create_production_payment_service(
    event_bus: EventBus,
    additional_wrappers: Optional[List[Wrapper]] = None
) -> PaymentService:
    """Create payment service for production."""
    core = PaymentProcessor()
    repository = PaymentRepository(database)
    
    # Production domain-specific wrappers
    domain_wrappers = [
        IdempotencyWrapper(),                   # Prevent duplicate payments
        FraudDetectionWrapper(threshold=0.8),  # Strict fraud detection
    ]
    
    return create_service(
        service_class=PaymentService,
        core=core,
        repository=repository,
        event_bus=event_bus,
        additional_wrappers=domain_wrappers + (additional_wrappers or []),
        environment="production"
    )

def create_testing_payment_service(
    event_bus: Optional[EventBus] = None,
    additional_wrappers: Optional[List[Wrapper]] = None
) -> PaymentService:
    """Create payment service for testing."""
    if event_bus is None:
        event_bus = InMemoryEventBus()
    
    core = PaymentProcessor()
    repository = InMemoryPaymentRepository()  # In-memory for tests
    
    return create_service(
        service_class=PaymentService,
        core=core,
        repository=repository,
        event_bus=event_bus,
        additional_wrappers=additional_wrappers or [],
        environment="testing"
    )
```

#### FunctionCore vs ServiceCore Patterns

**FunctionCore Modules** (stateless):
```python
# modules/text_analyzer/__init__.py
def create_production_analyzer(event_bus: EventBus) -> TextAnalyzerService:
    """Create analyzer service - no repository needed."""
    core = TextAnalyzer()  # FunctionCore - stateless
    
    domain_wrappers = [
        TextValidationWrapper(),
        TextCacheWrapper(),
    ]
    
    return create_service(
        service_class=TextAnalyzerService,
        core=core,
        repository=None,  # FunctionCore doesn't need persistence
        event_bus=event_bus,
        additional_wrappers=domain_wrappers,
        environment="production"
    )
```

**ServiceCore Modules** (stateful):
```python
# modules/task_manager/__init__.py  
def create_production_task_manager(base_path: Path, event_bus: EventBus) -> TaskManagerService:
    """Create task manager service with persistence."""
    core = TaskProcessor()  # ServiceCore - stateful
    repository = TaskRepository(base_path)  # Needs persistence
    
    domain_wrappers = [
        TaskMetricsWrapper(),
        TaskRetryWrapper(max_retries=3),
    ]
    
    return create_service(
        service_class=TaskManagerService,
        core=core,
        repository=repository,  # ServiceCore often needs repository
        event_bus=event_bus,
        additional_wrappers=domain_wrappers,
        environment="production"
    )
```

### Environment Configuration

#### Wrapper Composition Order

Wrappers are applied in order: **Default → Environment → Additional**

```python
# Example composition for production payment service:
final_wrappers = [
    # Default (applied to all services)
    AuthWrapper(auth_service),
    MonitoringWrapper(metrics_client),
    LoggingWrapper(logger),
    
    # Environment-specific (production)
    CacheWrapper(redis_client),
    RetryWrapper(max_retries=3),
    CircuitBreakerWrapper(),
    RateLimitWrapper(),
    
    # Domain-specific (payment)
    IdempotencyWrapper(),
    FraudDetectionWrapper(),
]

# Request flow: AuthWrapper → MonitoringWrapper → ... → FraudDetectionWrapper → Core
```

#### Configuration Management

**Environment Variables**:
```python
# config/environments.py
import os

ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "development")

WRAPPER_CONFIGS = {
    "development": {
        "cache_ttl": 60,
        "retry_attempts": 1,
        "fraud_threshold": 0.1,
    },
    "production": {
        "cache_ttl": 300,
        "retry_attempts": 3,
        "fraud_threshold": 0.8,
    }
}
```

**Configuration-Driven Setup**:
```python
def configure_factory_from_config(config: Dict[str, Any]):
    """Configure factory from application config."""
    env = config.get("environment", "production")
    wrapper_config = config.get("wrappers", {})
    
    if env == "production":
        service_factory.set_environment_wrappers("production", [
            CacheWrapper(redis_client, ttl=wrapper_config.get("cache_ttl", 300)),
            RetryWrapper(max_retries=wrapper_config.get("retry_attempts", 3)),
            CircuitBreakerWrapper(),
        ])
```

### Testing with Service Factory

#### Test Service Creation

```python
# tests/test_service_factory.py
async def test_service_factory_creates_with_correct_wrappers():
    """Test factory applies wrappers in correct order."""
    
    # Setup test factory
    test_factory = ServiceFactory()
    test_factory.set_default_wrappers([TestWrapper1()])
    test_factory.set_environment_wrappers("testing", [TestWrapper2()])
    
    # Create service
    service = test_factory.create_service(
        service_class=TestService,
        core=TestCore(),
        additional_wrappers=[TestWrapper3()],
        environment="testing"
    )
    
    # Verify wrapper order: default + environment + additional
    assert len(service.wrappers) == 3
    assert isinstance(service.wrappers[0], TestWrapper1)
    assert isinstance(service.wrappers[1], TestWrapper2)
    assert isinstance(service.wrappers[2], TestWrapper3)

async def test_module_factory_functions():
    """Test module-specific factory functions work correctly."""
    
    # Test development setup
    dev_service = create_development_payment_service(event_bus)
    assert dev_service.environment == "development"
    
    # Test production setup
    prod_service = create_production_payment_service(event_bus)
    assert prod_service.environment == "production"
    
    # Test different wrapper configurations
    assert len(dev_service.wrappers) != len(prod_service.wrappers)
```

### Best Practices

#### Do's

1. **Use module factory functions** for service creation
2. **Configure factory once** at application startup
3. **Keep wrapper order consistent** across environments
4. **Test wrapper compositions** independently
5. **Use environment-specific configurations** for different deployments

#### Don'ts

1. **Don't create services directly** - always use factory
2. **Don't bypass the factory** for production services
3. **Don't put business logic** in wrapper configurations
4. **Don't hardcode wrapper parameters** - use configuration
5. **Don't forget to test** wrapper interaction effects

#### Common Patterns

**Service Registry Pattern**:
```python
class ServiceRegistry:
    """Registry of all application services."""
    
    def __init__(self, factory: ServiceFactory):
        self.factory = factory
        self.services = {}
    
    async def create_all_services(self, environment: str):
        """Create all services for given environment."""
        self.services = {
            'payment': create_production_payment_service(event_bus),
            'user': create_production_user_service(event_bus),
            'notification': create_production_notification_service(event_bus),
        }
        return self.services
```

**Dependency Injection Pattern**:
```python
async def setup_application(environment: str):
    """Setup complete application with dependency injection."""
    
    # Configure factory
    factory = await setup_services()
    
    # Create services with shared dependencies
    event_bus = EventBus()
    
    services = {
        'payment': create_production_payment_service(event_bus),
        'user': create_production_user_service(event_bus),
    }
    
    return Application(services)
```

## Event System & Auto-Schema Generation

### Overview

The event system provides type-safe, inter-module communication with **automatic schema generation**. Instead of manually maintaining event schemas, the system observes actual event publishing patterns and generates Pydantic schemas automatically from real usage.

### Design Principles

1. **Zero Manual Work**: Schemas generate automatically from observed event data
2. **Always Accurate**: Reflects actual usage, not outdated documentation
3. **Self-Learning**: Adapts as event structures evolve
4. **Type Safety**: Generated Pydantic models provide validation and IDE support
5. **Discoverable**: Auto-generated schemas exported to `shared/auto_generated_schemas.py`

### Core Components

#### Auto-Schema Engine (`shared/auto_schema/`)

The auto-schema system wraps event buses transparently and learns from actual usage:

```python
# shared/auto_schema/engine.py - SchemaInferenceEventBus
# Wraps any event bus and observes published events
# Generates schemas after configurable threshold (default: 3 observations)

# shared/auto_schema/export.py - Schema export utilities
# Finds all learning buses and exports schemas to file
```

#### Automatic Integration (`core/base_service.py`)

BaseService automatically wraps event buses with schema learning:

```python
# BaseService.__init__() automatically creates:
if config.ENABLE_SCHEMA_LEARNING:
    self.event_bus = SchemaInferenceEventBus(original_event_bus)
else:
    self.event_bus = original_event_bus
```

#### Usage - No Changes Required

Services publish events normally - schemas learn automatically:

```python
# Just publish events as usual
await self.event_bus.publish("calculation.completed", {
    "operation": "add",
    "operand_a": 5.0,
    "operand_b": 3.0,
    "result": 8.0,
    "timestamp": datetime.utcnow(),
    "request_id": "req-123"
})

# System automatically:
# 1. Observes the data structure
# 2. Generates schema after 3+ observations
# 3. Validates future events against learned schema
```

### Schema Management Commands

#### Export Generated Schemas

```bash
# Export all learned schemas to file
make schema-export

# View learning statistics  
make schema-summary

# Clean generated schema files
make schema-clean
```

#### Configuration

Control schema learning via environment variables:

```bash
# Enable/disable learning (default: true)
export ENABLE_SCHEMA_LEARNING=true

# Set observation threshold (default: 3)
export SCHEMA_LEARNING_THRESHOLD=5

# Set export file path (default: shared/auto_generated_schemas.py)
export SCHEMA_EXPORT_PATH=custom/path/schemas.py
```

### Event Publishing Patterns

#### Standard Event Publishing

Services publish events as normal - schemas learn automatically:

```python
class DomainService(BaseService):
    
    async def perform_action(self, request: ActionRequest, **kwargs) -> ActionResult:
        try:
            result = await self.core.execute_action(request)
            
            # Publish success event - schema will be learned automatically
            await self.event_bus.publish("domain.action_completed", {
                "entity_id": request.entity_id,
                "action": request.action_type,
                "timestamp": datetime.utcnow(),
                "request_id": kwargs.get("request_id"),
                "user_id": kwargs.get("user_id"),
                "domain_data": {"result": result.data}
            })
            
            return result
            
        except Exception as e:
            # Publish error event - schema will be learned automatically
            await self.event_bus.publish("domain.action_failed", {
                "entity_id": request.entity_id,
                "action": request.action_type,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.utcnow(),
                "request_id": kwargs.get("request_id"),
                "user_id": kwargs.get("user_id")
            })
            raise
```

#### Optional Documentation Decorators

You can still use decorators for documentation (no functional impact):

```python
from core.event_registry import publishes_event

class DomainService(BaseService):
    
    @publishes_event("domain.action_completed")  # Documentation only
    @publishes_event("domain.action_failed")     # Documentation only
    async def perform_action(self, request: ActionRequest, **kwargs):
        # Implementation same as above
```

### Generated Schema File

#### Auto-Generated Schemas (`shared/auto_generated_schemas.py`)

After running services, schemas are automatically generated:

```python
# Auto-generated event schemas
# Generated by SchemaInferenceEventBus
# Generated at: 2025-06-27T15:14:51.804240

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class DomainActionCompletedEvent(BaseModel):
    """Auto-generated schema for domain.action_completed event."""
    
    entity_id: str
    action: str  
    timestamp: datetime
    request_id: str | None
    user_id: str | None
    domain_data: dict

class DomainActionFailedEvent(BaseModel):
    """Auto-generated schema for domain.action_failed event."""
    
    entity_id: str
    action: str
    error_type: str
    error_message: str
    timestamp: datetime
    request_id: str | None
    user_id: str | None
```

#### Using Generated Schemas

Import and use for validation in other services:

```python
from shared.auto_generated_schemas import DomainActionCompletedEvent

async def handle_action_completed(self, event_data: dict):
    # Validate incoming event data
    validated_event = DomainActionCompletedEvent(**event_data)
    print(f"Action {validated_event.action} completed for {validated_event.entity_id}")
```

### Benefits of Auto-Schema Generation

- **Zero Maintenance**: No manual schema updates required
- **Always Accurate**: Reflects actual event data, not stale documentation  
- **Self-Healing**: Adapts automatically as event structures evolve
- **Type Safety**: Generated Pydantic models provide full validation
- **Easy Discovery**: All schemas exported to single file

### Development Workflow

#### 1. Develop Normally
```python
# Just publish events as usual - no schema setup required
await self.event_bus.publish("user.registered", {
    "user_id": user.id,
    "email": user.email,
    "timestamp": datetime.utcnow()
})
```

#### 2. Run Your Code
```bash
# Run tests, start services, etc.
make test
```

#### 3. Export Learned Schemas
```bash
# Export schemas after running your code
make schema-export
```

#### 4. Use Generated Schemas
```python
# Import and use for validation
from shared.auto_generated_schemas import UserRegisteredEvent

def handle_user_registered(event_data: dict):
    event = UserRegisteredEvent(**event_data)  # Type-safe validation
    send_welcome_email(event.email)
```

### Schema Discovery

#### Learning Statistics

Check what schemas have been learned:

```bash
make schema-summary
```

Output:
```
📊 Schema Learning Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━
Found 1 schema learning event bus(es)

  • user.registered
    Observations: 5
    Schema: ✓ UserRegisteredEvent
  • cart.item_added  
    Observations: 12
    Schema: ✓ CartItemAddedEvent
```
### Testing Auto-Schema Systems

#### Schema Learning Tests

```python
@pytest.mark.asyncio
async def test_schema_learning():
    """Test that schemas are learned from actual events."""
    from shared.auto_schema import SchemaInferenceEventBus
    
    # Mock event bus
    mock_bus = MockEventBus()
    schema_bus = SchemaInferenceEventBus(mock_bus, enable_learning=True)
    schema_bus.schema_generation_threshold = 2  # Lower for testing
    
    # Publish events to learn schema
    await schema_bus.publish("test.event", {
        "user_id": "user-123",
        "action": "test_action",
        "timestamp": datetime.utcnow()
    })
    
    await schema_bus.publish("test.event", {
        "user_id": "user-456", 
        "action": "another_action",
        "timestamp": datetime.utcnow()
    })
    
    # Verify schema was generated
    summary = schema_bus.list_learned_events()
    assert "test.event" in summary
    assert summary["test.event"]["has_schema"] is True
    assert summary["test.event"]["observation_count"] == 2
```

#### Schema Export Tests

```python
def test_schema_export():
    """Test that schemas can be exported to file."""
    from shared.auto_schema.export import export_all_schemas
    
    # After running services with schema learning
    result = export_all_schemas("test_schemas.py")
    
    assert result["schemas_exported"] > 0
    assert os.path.exists("test_schemas.py")
    
    # Verify exported file is valid Python
    with open("test_schemas.py") as f:
        content = f.read()
        assert "class" in content
        assert "BaseModel" in content
```

### Event Naming Conventions

- **Format**: `{domain}.{action}` using dot notation
- **Domain**: Lowercase noun (user, payment, order, calculation)  
- **Action**: Past tense verb for completed actions (created, updated, deleted, completed)
- **Present tense**: For ongoing states (processing, validating, pending)

**Examples**:
- `user.created` - User registration completed
- `payment.processed` - Payment successfully processed
- `order.shipped` - Order shipped to customer
- `calculation.completed` - Mathematical operation finished
- `document.processing` - Document being processed
- `task.pending` - Task waiting for execution

### Best Practices

#### Do's

1. **Publish events consistently** - use same field names and types across events
2. **Include standard fields** - timestamp, request_id, user_id for traceability
3. **Use descriptive event names** - follow domain.action naming convention
4. **Export schemas regularly** - run `make schema-export` after development
5. **Version your schemas** - commit exported schemas to track changes
5. **Test system events** independently from business logic
6. **Focus on infrastructure concerns** (service lifecycle, system health, errors)

#### Don'ts

1. **Don't centralize domain events** - they create coupling between modules
2. **Don't use global event bus for business logic** - keep it for system concerns
3. **Don't include sensitive data** in system events - use component names only
4. **Don't make system events too detailed** - focus on operational concerns
5. **Don't couple modules through events** - prefer direct interfaces

#### Common Patterns

**Request/Response Correlation**:
```python
# Include request_id for tracing request flow
await self.event_bus.publish("order.created", {
    "order_id": order.id,
    "request_id": request.correlation_id,  # Links events to request
    "user_id": request.user_id
})
```

**Error Event Pattern**:
```python
# Standardized error events
@register_event_schema("domain.action_failed")
class DomainActionFailedEvent(BaseModel):
    entity_id: str
    action: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    user_id: Optional[str] = None
```

**State Transition Events**:
```python
# Events for state machine transitions
await self.event_bus.publish("order.status_changed", {
    "order_id": order.id,
    "from_status": previous_status,
    "to_status": new_status,
    "reason": transition_reason
})
```

## Naming Conventions

### Files and Directories
- **Modules**: lowercase with underscores (`user_service.py`, `payment_processor.py`)
- **Classes**: PascalCase (`UserService`, `PaymentProcessor`)
- **Functions/Variables**: snake_case (`process_payment`, `user_id`)
- **Constants**: UPPERCASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private**: prefix with underscore (`_internal_method`)
- **Protocols/Interfaces**: descriptive nouns (`Repository`, `EventPublisher`)

### Module Layer Files
- **Core Logic**: `core/` folder with specific implementations
- **Lifecycle**: `repository.py` (CRUD operations)
- **Service**: `service.py` (orchestration)
- **Interfaces**: `interfaces.py` (contracts)
- **Models**: `models.py` (data structures)

### Type Naming
- **Type Aliases**: PascalCase (`UserId`, `Money`)
- **Generic Types**: Single capital letters (`T`, `K`, `V`)
- **Pydantic Models**: noun + purpose (`UserCreateRequest`, `PaymentResponse`)

### Test Naming
- **Test Files**: `test_` prefix (`test_user_service.py`)
- **Test Functions**: `test_` + behavior (`test_payment_is_idempotent`)
- **Contract Tests**: `ContractTests` suffix (`RepositoryContractTests`)

### Domain-Specific Conventions
- **Core Classes**: `{Domain}Core` (e.g., `UserCore`, `PaymentProcessor`)
- **Repositories**: `{Entity}Repository` (e.g., `UserRepository`, `OrderRepository`)
- **Services**: `{Domain}Service` (e.g., `UserService`, `PaymentService`)
- **Validators**: `{Purpose}Validator` (e.g., `EmailValidator`, `AmountValidator`)
- **Events**: `{Entity}{Action}Event` (e.g., `UserCreatedEvent`, `OrderCancelledEvent`)

### Event-Driven Conventions
- **Events**: `{entity}.{action}` (e.g., `payment.processed`, `user.created`)
- **Event Handlers**: `handle_{entity}_{action}` (e.g., `handle_payment_processed`)
- **Event Data**: Include entity ID and relevant context

### Extension/Plugin Conventions
- **Extension Names**: descriptive_noun (e.g., `task_manager`, `knowledge_extractor`)
- **Extension Files**: `{name}_extension.py` or `{name}_plugin.py`
- **Extension APIs**: `execute(input_data)`, `reload()`, `get_capabilities()`

### API Endpoints
- **REST**: `/api/v1/{resource}` (plural nouns)
- **GraphQL**: `{action}{Resource}` (e.g., `createUser`, `listOrders`)
- **WebSocket**: `/ws/{channel}` (e.g., `/ws/notifications`)

### Database Naming
- **Tables**: plural, snake_case (`users`, `order_items`)
- **Columns**: snake_case (`user_id`, `created_at`)
- **Indexes**: `idx_{table}_{columns}` (e.g., `idx_users_email`)
- **Foreign Keys**: `fk_{table}_{referenced_table}` (e.g., `fk_orders_users`)

### Environment Variables
- **Format**: `{PROJECT}_{COMPONENT}_{SETTING}` 
- **Examples**: `APP_DATABASE_URL`, `APP_REDIS_HOST`, `APP_LOG_LEVEL`

### Error Messages
- **Format**: Clear, actionable, and specific
- **Good**: "User with email 'john@example.com' already exists"
- **Bad**: "Error occurred"

### Log Messages
- **Format**: `[{timestamp}] {level} {component}: {message}`
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Include**: Context, IDs, and actionable information