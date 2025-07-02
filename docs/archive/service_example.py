# Simplified Service Demonstration
# Shows essential patterns for BaseService usage, service creation, and factory with wrappers

import time
from dataclasses import dataclass
from typing import Any

from core.base_service import BaseService
from core.interfaces import OperationContext, ServiceOperation
from core.service_factory import ServiceFactory, configure_factory


# === 1. SIMPLE DOMAIN MODEL ===
@dataclass
class Task:
    id: str
    title: str
    status: str = "pending"


# === 2. SIMPLE CORE BUSINESS LOGIC ===
class TaskManager:
    """Simple core business logic"""

    def validate_task(self, task: Task) -> bool:
        return len(task.title) > 0

    def process_task(self, task: Task) -> Task:
        task.status = "processed"
        return task


# === 3. SIMPLE REPOSITORY ===
class TaskRepository:
    """In-memory repository for demo"""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.counter = 0

    async def create(self, task: Task) -> Task:
        self.counter += 1
        task.id = str(self.counter)
        self.tasks[task.id] = task
        return task

    async def find_by_id(self, id: str) -> Task | None:
        return self.tasks.get(id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Task]:
        all_tasks = list(self.tasks.values())
        return all_tasks[offset : offset + limit]


# === 4. SERVICE IMPLEMENTATION ===
class TaskService(BaseService[Task]):
    """Minimal service showing BaseService usage"""

    def __init__(
        self,
        core: TaskManager,
        repository: TaskRepository,
        event_bus=None,
        wrappers=None,
        config=None,
    ):
        # Initialize with core, repository, event bus, wrappers, config
        super().__init__(core, repository, event_bus, wrappers, config)

    # Override domain-specific operation
    async def _process(self, task: Task, **kwargs) -> Task:
        """Process task through core business logic"""
        if not self.core.validate_task(task):
            raise ValueError("Invalid task")

        processed = self.core.process_task(task)
        return await self.repository.create(processed)


# === 5. SIMPLE WRAPPERS ===
class LoggingWrapper:
    """Simple logging wrapper"""

    async def wrap(
        self, operation: ServiceOperation, context: OperationContext, next_func, *args, **kwargs
    ) -> Any:
        print(f"[LOG] Starting {operation.value} operation")
        try:
            result = await next_func(*args, **kwargs)
            print(f"[LOG] Completed {operation.value} successfully")
            return result
        except Exception as e:
            print(f"[LOG] Failed {operation.value}: {e}")
            raise


class TimingWrapper:
    """Simple timing wrapper"""

    async def wrap(
        self, operation: ServiceOperation, context: OperationContext, next_func, *args, **kwargs
    ) -> Any:
        start = time.time()
        try:
            result = await next_func(*args, **kwargs)
            duration = time.time() - start
            print(f"[TIMING] {operation.value} took {duration:.3f}s")
            return result
        except Exception:
            duration = time.time() - start
            print(f"[TIMING] {operation.value} failed after {duration:.3f}s")
            raise


# === 6. SERVICE FACTORY (Using core/service_factory.py) ===
# The ServiceFactory is imported from core.service_factory
# We just need to configure it with our wrappers


# === 7. DEMONSTRATION USAGE ===
async def demonstrate_service_usage():
    """Show how to use the service patterns"""

    print("=== BaseService Demonstration ===\n")

    # 1. Configure global factory with default wrappers
    configure_factory(
        default_wrappers=[
            TimingWrapper(),  # Time all operations
            LoggingWrapper(),  # Log all operations
        ],
        environment_configs={
            "development": [],  # No additional wrappers for dev
            "production": [],  # Could add monitoring, caching, etc.
        },
    )

    # 2. Create service through factory
    factory = ServiceFactory()
    service = factory.create_service(
        service_class=TaskService,
        core=TaskManager(),
        repository=TaskRepository(),
        environment="development",
    )

    print("1. Creating task...")
    task = Task(id="", title="Learn BaseService patterns")
    created_task = await service.create(task)
    print(f"   Created task: {created_task}\n")

    print("2. Reading task...")
    found_task = await service.get(created_task.id)
    print(f"   Found task: {found_task}\n")

    print("3. Processing task (domain-specific operation)...")
    new_task = Task(id="", title="Process documents")
    processed_task = await service.process(new_task)
    print(f"   Processed task: {processed_task}\n")

    print("4. Listing all tasks...")
    all_tasks = await service.list()
    print(f"   Total tasks: {len(all_tasks)}")
    for task in all_tasks:
        print(f"   - {task.title} ({task.status})")


# === 8. RUN DEMONSTRATION ===
if __name__ == "__main__":
    import asyncio

    print("Starting service demonstration...")
    asyncio.run(demonstrate_service_usage())
    print("\nDemonstration complete!")
