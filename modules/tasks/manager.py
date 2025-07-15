"""Task manager - integrates scheduling, hooks, and storage."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from modules import eventbus
from modules.eventbus.event_chain import EventChainExecutor
from .scheduler import TaskScheduler
from .storage import TaskStorage
from .hooks import HookManager


class TaskManager:
    """Complete task system with scheduling and hooks."""
    
    def __init__(self):
        self.storage = TaskStorage()
        self.scheduler = TaskScheduler()
        self.hook_manager = HookManager()
        self.chain_executor = EventChainExecutor(eventbus)
        self._started = False
        
    async def start(self):
        """Start all components."""
        if self._started:
            return
            
        # Start components
        self.scheduler.start()
        await self.hook_manager.start()
        
        # Register event handlers
        await eventbus.subscribe("task.schedule", self._handle_schedule_task)
        await eventbus.subscribe("task.hook", self._handle_hook_task)
        await eventbus.subscribe("task.list", self._handle_list_tasks)
        
        # Global event interceptor for hooks
        await eventbus.subscribe("*", self._check_hooks)
        
        # Load existing tasks
        self._load_tasks()
        
        self._started = True
        print("Integrated task system started!")
        
    def stop(self):
        """Stop all components."""
        self.scheduler.stop()
        self.hook_manager.stop()
        self._started = False
        
    def _load_tasks(self):
        """Load saved tasks."""
        for task in self.storage.list_tasks():
            if task.get("type") == "scheduled":
                self._schedule_task(task)
            elif task.get("type") == "hook":
                self._register_hook(task)
                
    async def _handle_schedule_task(self, event):
        """Handle task.schedule event."""
        data = event.data
        task_id = f"sched_{datetime.now().strftime('%H%M%S_%f')[:12]}"
        
        task = {
            "id": task_id,
            "type": "scheduled",
            "name": data.get("name", "Unnamed Task"),
            "trigger": data.get("trigger"),
            "event_chain": data.get("event_chain", [])
        }
        
        # Save and schedule
        self.storage.save_task(task_id, task)
        self._schedule_task(task)
        
        return {"task_id": task_id, "status": "scheduled"}
        
    async def _handle_hook_task(self, event):
        """Handle task.hook event."""
        data = event.data
        task_id = f"hook_{datetime.now().strftime('%H%M%S_%f')[:12]}"
        
        task = {
            "id": task_id,
            "type": "hook",
            "name": data.get("name", "Unnamed Hook"),
            "event_pattern": data.get("pattern"),
            "event_chain": data.get("event_chain", [])
        }
        
        # Save and register
        self.storage.save_task(task_id, task)
        self._register_hook(task)
        
        return {"hook_id": task_id, "status": "registered"}
        
    async def _handle_list_tasks(self, event):
        """Handle task.list event."""
        tasks = self.storage.list_tasks()
        return {
            "tasks": [
                {
                    "id": t["id"],
                    "name": t.get("name"),
                    "type": t.get("type"),
                    "pattern": t.get("event_pattern") if t.get("type") == "hook" else None
                }
                for t in tasks
            ],
            "count": len(tasks)
        }
        
    def _schedule_task(self, task: Dict):
        """Schedule a task."""
        task_id = task["id"]
        trigger = task.get("trigger", {})
        
        # Create executor function
        def execute():
            print(f"\n[Scheduled Task: {task['name']}]")
            # Execute synchronously for now
            for i, event in enumerate(task.get("event_chain", [])):
                print(f"  Step {i+1}: {event.get('event', 'unknown')}")
            
        # Schedule based on type
        if trigger.get("type") == "interval":
            self.scheduler.add_interval_task(task_id, execute, trigger.get("seconds", 60))
        elif trigger.get("type") == "once":
            run_time = trigger.get("run_time")
            if isinstance(run_time, str):
                run_time = datetime.fromisoformat(run_time)
            self.scheduler.add_one_time_task(task_id, execute, run_time)
            
    def _register_hook(self, task: Dict):
        """Register a hook."""
        task_id = task["id"]
        pattern = task.get("event_pattern", "*")
        
        # Create hook function
        def hook_func(event_name, event_data):
            print(f"\n[Hook Task: {task['name']}] Triggered by {event_name}")
            # Execute synchronously for now
            for i, event in enumerate(task.get("event_chain", [])):
                print(f"  Step {i+1}: {event.get('event', 'unknown')}")
            
        self.hook_manager.register_hook(task_id, pattern, hook_func)
        
    async def _check_hooks(self, event):
        """Check all events against registered hooks."""
        # Skip task system events to prevent loops
        if event.name.startswith("task."):
            return
            
        await self.hook_manager.handle_event(event.name, event.data)
        
    async def _execute_event_chain(self, event_chain: List[Dict]):
        """Execute an event chain."""
        try:
            # For now, just print the chain
            for i, event in enumerate(event_chain):
                print(f"  Step {i+1}: {event.get('event', 'unknown')} - {event.get('data', {})}")
            
            # In real implementation, would use:
            # result = await self.chain_executor.execute(event_chain)
            
        except Exception as e:
            print(f"  Error executing chain: {e}")


