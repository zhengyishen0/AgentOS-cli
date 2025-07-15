"""Task system data models for AgentOS."""

from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class TaskTrigger(BaseModel):
    """Base trigger configuration."""
    type: Literal["cron", "interval", "date", "hook"]
    

class CronTrigger(TaskTrigger):
    """Cron-based scheduling trigger."""
    type: Literal["cron"] = "cron"
    expression: str = Field(..., description="Cron expression like '0 9 * * *'")


class IntervalTrigger(TaskTrigger):
    """Interval-based scheduling trigger."""
    type: Literal["interval"] = "interval"
    seconds: int = Field(..., description="Interval in seconds")


class DateTrigger(TaskTrigger):
    """One-time date trigger."""
    type: Literal["date"] = "date"
    run_date: datetime = Field(..., description="When to run the task")


class HookTrigger(TaskTrigger):
    """Event-based hook trigger."""
    type: Literal["hook"] = "hook"
    event_pattern: str = Field(..., description="Event name pattern to match (supports wildcards)")
    position: Literal["before", "after"] = Field(default="after", description="Hook position relative to event")
    condition: Optional[str] = Field(default=None, description="Optional condition to evaluate")


class RepetitionGuard(BaseModel):
    """Guards against repetitive/duplicate task execution."""
    cooldown_seconds: Optional[int] = Field(default=None, description="Minimum seconds between executions")
    max_per_hour: Optional[int] = Field(default=None, description="Maximum executions per hour")
    dedupe_key: Optional[str] = Field(default=None, description="Template for deduplication key")


class Task(BaseModel):
    """Complete task definition."""
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    name: str = Field(..., description="Human-readable task name")
    type: Literal["scheduled", "hook"] = Field(..., description="Task type")
    trigger: Dict[str, Any] = Field(..., description="Trigger configuration")
    event_chain: List[Dict[str, Any]] = Field(..., description="Event chain to execute")
    
    # Optional fields
    thread_id: Optional[str] = Field(default=None, description="Thread ID for stateful execution")
    repetition_guard: Optional[Dict[str, Any]] = Field(default=None, description="Repetition guard config")
    priority: int = Field(default=0, description="Execution priority (higher = first)")
    can_block: bool = Field(default=False, description="For pre-hooks: can block original event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")
    
    # System fields
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    
    def to_apscheduler_kwargs(self) -> Dict[str, Any]:
        """Convert to APScheduler job kwargs."""
        kwargs = {
            "id": self.id,
            "name": self.name,
            "kwargs": {
                "task_id": self.id,
                "event_chain": self.event_chain,
                "thread_id": self.thread_id,
                "metadata": self.metadata
            }
        }
        
        # Add trigger based on type
        trigger = self.trigger
        if trigger["type"] == "cron":
            kwargs["trigger"] = "cron"
            # Parse cron expression
            from apscheduler.triggers.cron import CronTrigger
            kwargs["trigger"] = CronTrigger.from_crontab(trigger["expression"])
        elif trigger["type"] == "interval":
            kwargs["trigger"] = "interval"
            kwargs["seconds"] = trigger["seconds"]
        elif trigger["type"] == "date":
            kwargs["trigger"] = "date"
            kwargs["run_date"] = trigger["run_date"]
            
        return kwargs