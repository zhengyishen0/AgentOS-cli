"""Task scheduler using APScheduler for time-based execution."""

import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class TaskScheduler:
    """Minimal scheduler using APScheduler."""
    
    def __init__(self):
        # Use memory store (no persistence for now)
        self.scheduler = AsyncIOScheduler()
        self.task_count = 0
        
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        print("Scheduler started!")
        
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print("Scheduler stopped!")
        
    def add_interval_task(self, task_id: str, func, seconds: int):
        """Add a task that runs every N seconds."""
        self.scheduler.add_job(
            func,
            'interval',
            seconds=seconds,
            id=task_id,
            replace_existing=True
        )
        print(f"Added interval task {task_id} (every {seconds}s)")
        
    def add_one_time_task(self, task_id: str, func, run_time: datetime):
        """Add a task that runs once at a specific time."""
        self.scheduler.add_job(
            func,
            'date',
            run_date=run_time,
            id=task_id,
            replace_existing=True
        )
        print(f"Added one-time task {task_id} (at {run_time})")
        
    def remove_task(self, task_id: str):
        """Remove a task."""
        try:
            self.scheduler.remove_job(task_id)
            print(f"Removed task {task_id}")
            return True
        except:
            return False
            
    def list_tasks(self):
        """List all scheduled tasks."""
        jobs = self.scheduler.get_jobs()
        print(f"\nScheduled tasks ({len(jobs)}):")
        for job in jobs:
            print(f"  - {job.id}: next run at {job.next_run_time}")
        return jobs

