"""Example usage of the AgentOS task system."""

import asyncio
from datetime import datetime, timedelta
from modules import eventbus
from modules.tasks import TaskManager


async def demonstrate_task_system():
    """Demonstrate the task system capabilities."""
    
    print("=== AgentOS Task System Demo ===\n")
    
    # Initialize the task manager
    task_manager = TaskManager()
    await task_manager.start()
    
    # 1. Schedule an interval task
    print("1. Creating an interval task (runs every 30 seconds)...")
    result = await eventbus.publish("task.schedule", {
        "name": "System Health Check",
        "trigger": {"type": "interval", "seconds": 30},
        "event_chain": [
            {"event": "system.status", "data": {}},
            {"event": "logger.info", "data": {"message": "Health check completed"}}
        ]
    })
    print(f"   Created: {result}\n")
    
    # 2. Schedule a one-time task
    print("2. Creating a one-time task (runs in 1 minute)...")
    run_time = datetime.now() + timedelta(minutes=1)
    result = await eventbus.publish("task.schedule", {
        "name": "Data Backup",
        "trigger": {"type": "once", "run_time": run_time},
        "event_chain": [
            {"event": "backup.start", "data": {"type": "incremental"}},
            {"event": "notification.send", "data": {"message": "Backup completed"}}
        ]
    })
    print(f"   Created: {result}\n")
    
    # 3. Register an event hook
    print("3. Creating an event hook (triggers on user events)...")
    result = await eventbus.publish("task.hook", {
        "name": "New User Handler",
        "pattern": "user.created",
        "event_chain": [
            {"event": "email.welcome", "data": {"template": "new_user"}},
            {"event": "analytics.track", "data": {"event": "user_onboarded"}}
        ]
    })
    print(f"   Created: {result}\n")
    
    # 4. List all tasks
    print("4. Listing all tasks...")
    result = await eventbus.publish("task.list", {})
    print(f"   Total tasks: {result['count']}")
    for task in result['tasks']:
        print(f"   - {task['name']} ({task['type']})")
    
    # 5. Trigger a user event to test the hook
    print("\n5. Testing hook by creating a user...")
    await eventbus.publish("user.created", {
        "user_id": "123",
        "name": "Test User",
        "email": "test@example.com"
    })
    
    print("\nTask system is running. Press Ctrl+C to stop.")
    
    try:
        # Keep running to see task executions
        await asyncio.sleep(3600)  # Run for 1 hour
    except KeyboardInterrupt:
        print("\nStopping task system...")
        task_manager.stop()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(demonstrate_task_system())