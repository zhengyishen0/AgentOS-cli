"""Data models for EventBus system."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class Event(BaseModel):
    """Unified event model for the entire system with full lifecycle tracking."""
    
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(description="Event name (e.g., 'user.login')")
    data: Dict[str, Any] = Field(description="Event data payload")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(default="system", description="Source of the event")
    status: str = Field(default="published", description="Event status: published, completed, failed")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Event execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")


class ExecutionResult(BaseModel):
    """Result of executing an event chain."""
    
    thread_id: str = Field(description="Thread identifier")
    events: List[Event] = Field(description="Executed events")
    success: bool = Field(description="Overall chain success")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    total_execution_time_ms: float = Field(default=0.0, description="Total execution time")


class Thread(BaseModel):
    """Thread containing conversation context and event history."""
    
    thread_id: str = Field(description="Unique thread identifier")
    summary: str = Field(description="Thread summary")
    status: str = Field(default="active", description="Thread status: active, archived")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: List[Event] = Field(default_factory=list, description="Thread events")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Thread metadata")
    
    def add_event(self, event: Event):
        """Add an event to the thread."""
        self.events.append(event)
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def get_context(self) -> Dict[str, Any]:
        """Get thread context for event execution."""
        context = {
            'thread_id': self.thread_id,
            'summary': self.summary,
            'metadata': self.metadata,
            'thread': {
                self.thread_id: {
                    'events': [event.model_dump() for event in self.events],
                    'summary': self.summary,
                    'metadata': self.metadata
                }
            }
        }
        
        # Add recent event results to context
        for event in self.events[-10:]:  # Last 10 events for efficiency
            if '.' in event.name and event.result:
                parts = event.name.split('.')
                current = context
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = {'result': event.result}
        
        return context