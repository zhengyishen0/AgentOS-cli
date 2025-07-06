"""Event schemas for AgentOS EventBus system.

This module defines all event data contracts using Pydantic models.
Each schema represents the structure of event data that flows through the system.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field


# Task Event Schemas
class TaskScheduleInput(BaseModel):
    """Input schema for task.schedule event."""
    type: str = Field(default="once", description="Task type: 'once', 'recurring', or 'conditional'")
    at: Optional[str] = Field(default=None, description="When to run the task (ISO format or cron expression)")
    action: List[str] = Field(default_factory=list, description="List of actions to execute")


class TaskRegisterInput(BaseModel):
    """Input schema for task.register event."""
    trigger: str = Field(description="Event trigger pattern")
    condition: str = Field(default="", description="Condition for task execution")
    action: List[str] = Field(default_factory=list, description="List of actions to execute")


class TaskListInput(BaseModel):
    """Input schema for task.list event."""
    filter: Dict[str, Any] = Field(default_factory=dict, description="Filter parameters")
    status: str = Field(default="all", description="Status filter: 'all', 'pending', 'completed', 'failed'")


# Agent Event Schemas
class AgentChainInput(BaseModel):
    """Input schema for agent.chain event."""
    message: str = Field(description="The pseudocode plan to convert into an event chain")


class AgentThinkInput(BaseModel):
    """Input schema for agent.think event."""
    thread_id: str = Field(description="The thread context identifier")
    prompt: str = Field(default="", description="Specific prompt for mid-chain reasoning")


class AgentDecideInput(BaseModel):
    """Input schema for agent.decide event."""
    event_schema: Dict[str, Any] = Field(description="The schema of the event being evaluated")
    prompt: str = Field(description="The prompt for the decision")
    params: Dict[str, Any] = Field(default_factory=dict, description="The parameters to pass to the condition")


# Agent Output Schemas
class ChainEventSpec(BaseModel):
    """Specification for a single event in a chain."""
    event: str = Field(description="Event name to trigger")
    params: Dict[str, Any] = Field(default_factory=dict, description="Event parameters")
    decide: Optional[str] = Field(default=None, description="Optional condition for event execution")


class AgentChainOutput(BaseModel):
    """Output schema for agent.chain event."""
    chain: List[Union[ChainEventSpec, List[ChainEventSpec]]] = Field(description="List of events to execute (nested lists indicate parallel execution)")

class AgentThinkParams(BaseModel):
    """Parameters for the agent.think event."""
    message: str = Field(description="The message to think about")

class AgentThinkOutput(BaseModel):
    """Output schema for agent.think event."""
    event: Literal["agent.reply", "agent.chain"] = Field(description="Next event to trigger")
    params: AgentThinkParams = Field(description="Parameters for the next event")


class AgentDecideOutput(BaseModel):
    """Output schema for agent.decide event."""
    action: Literal["continue", "skip"] = Field(description="Whether to continue or skip the event")
    params: Dict[str, Any] = Field(description="The updated/completed parameters")
    reason: Optional[str] = Field(default=None, description="Reason for skipping (if action is skip)")


# Thread Event Schemas
class ThreadMatchInput(BaseModel):
    """Input schema for thread.match event."""
    input: str = Field(description="User input text to match against existing threads")


class ThreadSummarizeInput(BaseModel):
    """Input schema for thread.summarize event."""
    thread_id: str = Field(description="Thread identifier to summarize")
    max_length: Optional[int] = Field(default=500, description="Maximum length of summary")


class ThreadCreateInput(BaseModel):
    """Input schema for thread.create event."""
    summary: Optional[str] = Field(default=None, description="Optional initial summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Thread metadata")

    class Config:
        extra = "forbid"  # Prevent additional properties


class ThreadArchivedInput(BaseModel):
    """Input schema for thread.archived event."""
    thread_id: str = Field(description="Thread identifier to archive")
    reason: Optional[str] = Field(default=None, description="Reason for archiving")


# Memory Event Schemas
class MemoryAppendInput(BaseModel):
    """Input schema for memory.append event."""
    content: str = Field(description="Content to append to memory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Content metadata")
    thread_id: Optional[str] = Field(default=None, description="Optional thread context")

    class Config:
        extra = "forbid"  # Prevent additional properties


class MemorySearchInput(BaseModel):
    """Input schema for memory.search event."""
    query: str = Field(description="Search query")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")
    threshold: Optional[float] = Field(default=0.7, description="Similarity threshold")


class MemoryDigestInput(BaseModel):
    """Input schema for memory.digest event."""
    content: str = Field(description="Content to digest")
    digest_type: str = Field(default="summary", description="Type of digest to create")
    max_length: Optional[int] = Field(default=200, description="Maximum length of digest")


# System Event Schemas
class UserInputInput(BaseModel):
    """Input schema for user.input event."""
    text: str = Field(description="User input text")


class UserNotifyInput(BaseModel):
    """Input schema for user.notify event."""
    message: str = Field(description="Notification message")
    level: str = Field(default="info", description="Notification level")
    title: Optional[str] = Field(default=None, description="Optional notification title")


class WebSearchInput(BaseModel):
    """Input schema for web.search event."""
    query: str = Field(description="Search query")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")
    source: Optional[str] = Field(default=None, description="Optional search source")