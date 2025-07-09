"""Event schemas for AgentOS EventBus system.

This module defines all event data contracts using Pydantic models.
Each schema represents the structure of event data that flows through the system.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field


# Task Event Schemas
class TaskScheduleInput(BaseModel):
    """Input schema for task.schedule event.
    
    This event schedules a task to be executed at a specific time or on a recurring basis.
    The task can be a one-time execution, recurring based on a cron expression, or conditional.
    
    Expected behavior: Creates a scheduled task that will trigger the specified actions
    when the time condition is met.
    """
    type: str = Field(default="once", description="Task type: 'once', 'recurring', or 'conditional'")
    at: Optional[str] = Field(default=None, description="When to run the task (ISO format or cron expression)")
    action: List[str] = Field(default_factory=list, description="List of actions to execute")


class TaskRegisterInput(BaseModel):
    """Input schema for task.register event.
    
    This event registers a new task that will be triggered when a specific event pattern occurs.
    The task can include conditional logic to determine whether it should execute.
    
    Expected behavior: Registers a task listener that will automatically execute the specified
    actions when the trigger event is detected and conditions are met.
    """
    trigger: str = Field(description="Event trigger pattern")
    condition: str = Field(default="", description="Condition for task execution")
    action: List[str] = Field(default_factory=list, description="List of actions to execute")


class TaskListInput(BaseModel):
    """Input schema for task.list event.
    
    This event retrieves a list of all registered and scheduled tasks in the system.
    Results can be filtered by various criteria including status and custom filters.
    
    Expected behavior: Returns a comprehensive list of tasks matching the specified
    filter criteria, showing their current status and configuration.
    """
    filter: Dict[str, Any] = Field(default_factory=dict, description="Filter parameters")
    status: str = Field(default="all", description="Status filter: 'all', 'pending', 'completed', 'failed'")

class AgentReplyInput(BaseModel):
    """Input schema for agent.reply event.
    
    This event allows the agent to send a direct response or notification to the user.
    The reply can include different levels of urgency and optional titles for better UX.
    
    Expected behavior: Delivers a message to the user interface with appropriate
    styling based on the notification level (agent,info, warning, error, etc.).
    """
    message: str = Field(description="Notification message")
    level: str = Field(default="agent", description="Notification level")
    title: Optional[str] = Field(default=None, description="Optional notification title")


# Agent Event Schemas
class AgentChainInput(BaseModel):
    """Input schema for agent.chain event.
    
    This event converts a pseudocode plan or natural language description into a structured
    event chain that can be executed by the system. The agent analyzes the plan and breaks
    it down into discrete, executable events.
    
    Expected behavior: Analyzes the provided plan and returns a structured chain of events
    that will accomplish the described task, with proper sequencing and parallel execution
    where appropriate.
    """
    message: str = Field(description="The pseudocode plan to convert into an event chain")
    thread_id: str = Field(description="The thread context identifier")


class AgentThinkInput(BaseModel):
    """Input schema for agent.think event.
    
    This event allows the agent to perform reasoning and analysis within a specific thread context.
    The agent can think through complex problems, evaluate options, or perform mid-chain reasoning
    to make decisions about next steps.
    
    Expected behavior: The agent processes the prompt within the thread context and returns
    either a direct reply to the user or a decision to continue with an event chain based on
    the reasoning performed.
    """
    thread_id: str = Field(description="The thread context identifier")
    prompt: str = Field(default="", description="Specific prompt for mid-chain reasoning")


class AgentDecideInput(BaseModel):
    """Input schema for agent.decide event.
    
    This event allows the agent to evaluate whether an event should proceed based on the
    provided parameters and conditions. The agent can modify parameters or decide to skip
    the event entirely based on its analysis.
    
    Expected behavior: The agent evaluates the event schema and parameters against the
    provided prompt, then returns a decision to continue (with potentially modified parameters)
    or skip the event entirely, along with reasoning for the decision.
    """
    thread_id: str = Field(description="The thread context identifier")
    event_schema: Dict[str, Any] = Field(description="The schema of the event being evaluated")
    prompt: str = Field(description="The prompt for the decision")
    params: Dict[str, Any] = Field(default_factory=dict, description="The parameters to pass to the condition")

class AgentThreadInput(BaseModel):
    """Input schema for agent.thread event.
    
    This event allows the agent to match user input against existing conversation threads
    to find relevant context or determine if a new thread should be created. The agent
    analyzes semantic similarity and relevance.
    
    Expected behavior: The agent compares the input against existing threads and returns
    confidence scores for each potential match, helping the system decide whether to
    continue an existing conversation or start a new thread.
    """
    input: str = Field(description="User input text to match against existing threads")
    thread_data: Optional[List[str]] = Field(default=None, description="Optional thread data to match against")


# Agent Output Schemas
class ChainEventSpec(BaseModel):
    """Specification for a single event in a chain."""
    event: str = Field(description="Event name to trigger")
    params: Dict[str, Any] = Field(default_factory=dict, description="Event parameters")
    decide: Optional[str] = Field(default=None, description="Optional condition for event execution")
    timestamp: Optional[str] = Field(default=None, description="Optional timestamp for the event")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Optional error message for the event")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Event execution result")
    execution_time_ms: Optional[float] = Field(default=None, description="Optional execution time for the event")

    class Config:
        extra = "forbid"  # Prevent additional properties

class AgentChainOutput(BaseModel):
    """Output schema for agent.chain event."""
    chain: List[Union[ChainEventSpec, List[ChainEventSpec]]] = Field(description="List of events to execute (nested lists indicate parallel execution)")

    class Config:
        extra = "forbid"  # Prevent additional properties

class AgentThinkOutput(BaseModel):
    """Output schema for agent.think event."""
    event: Literal["agent.reply", "agent.chain"] = Field(description="Next event to trigger")
    message: str = Field(description="The message to think about")

class AgentDecideOutput(BaseModel):
    """Output schema for agent.decide event."""
    action: Literal["continue", "skip"] = Field(description="Whether to continue or skip the event")
    params: Dict[str, Any] = Field(description="The updated/completed parameters")
    reason: Optional[str] = Field(default=None, description="Reason for skipping (if action is skip)")

    class Config:
        extra = "forbid"  # Prevent additional properties

class AgentThreadOutput(BaseModel):
    """Output schema for agent.thread event. 
    Example:
    {
        "thread_confidence": {
            "thread_id_1": 0.8,
            "thread_id_2": 0.5
        }
    }"""
    thread_confidence: Dict[str, float] = Field(description="Confidence level for each thread")


# Thread Event Schemas
class ThreadMatchInput(BaseModel):
    """Input schema for thread.match event.
    
    This event searches for existing conversation threads that match the provided input text.
    It uses semantic matching to find threads with similar context or topics.
    
    Expected behavior: Returns a list of thread IDs that match the input text, ordered by
    relevance score, allowing the system to continue existing conversations or identify
    related topics.
    """
    input: str = Field(description="User input text to match against existing threads")
    thread_id: Optional[str] = Field(default=None, description="Optional thread identifier to match against")


class ThreadSummarizeInput(BaseModel):
    """Input schema for thread.summarize event.
    
    This event creates a concise summary of a conversation thread, condensing the key
    points and context into a manageable format for future reference or context switching.
    
    Expected behavior: Analyzes the thread content and generates a summary that captures
    the main topics, decisions, and important information while staying within the
    specified length limit.
    """
    thread_id: str = Field(description="Thread identifier to summarize")
    max_length: Optional[int] = Field(default=500, description="Maximum length of summary")


class ThreadCreateInput(BaseModel):
    """Input schema for thread.create event.
    
    This event creates a new conversation thread with optional initial summary and metadata.
    New threads provide a clean context for new conversations or task sequences.
    
    Expected behavior: Creates a new thread in the system with the provided metadata
    and optional summary, returning a unique thread identifier for future reference.
    """
    summary: Optional[str] = Field(default=None, description="Optional initial summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Thread metadata")

    class Config:
        extra = "forbid"  # Prevent additional properties


class ThreadArchivedInput(BaseModel):
    """Input schema for thread.archived event.
    
    This event archives an existing conversation thread, moving it from active status
    to archived status. Archived threads are preserved but no longer appear in active
    conversation lists.
    
    Expected behavior: Marks the specified thread as archived, preserving all content
    and metadata while removing it from active thread listings. The thread can still
    be accessed for historical reference.
    """
    thread_id: str = Field(description="Thread identifier to archive")
    reason: Optional[str] = Field(default=None, description="Reason for archiving")


# Memory Event Schemas
class MemoryAppendInput(BaseModel):
    """Input schema for memory.append event.
    
    This event adds new content to the system's memory store, which can be used for
    future context retrieval and learning. Content is stored with metadata for
    better organization and retrieval.
    
    Expected behavior: Stores the provided content in the memory system with associated
    metadata and optional thread context, making it available for future search and
    retrieval operations.
    """
    content: str = Field(description="Content to append to memory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Content metadata")
    thread_id: Optional[str] = Field(default=None, description="Optional thread context")

    class Config:
        extra = "forbid"  # Prevent additional properties


class MemorySearchInput(BaseModel):
    """Input schema for memory.search event.
    
    This event searches through the system's memory store to find relevant content
    based on a query. It uses semantic similarity to match content even when exact
    keywords don't match.
    
    Expected behavior: Returns a list of memory entries that match the search query,
    ordered by relevance score. Results are filtered by the similarity threshold
    and limited to the specified number of results.
    """
    query: str = Field(description="Search query")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")
    threshold: Optional[float] = Field(default=0.7, description="Similarity threshold")


class MemoryDigestInput(BaseModel):
    """Input schema for memory.digest event.
    
    This event creates a condensed version of content stored in memory, summarizing
    key information while maintaining the essential context. Different digest types
    can be used for different purposes (summary, key points, etc.).
    
    Expected behavior: Analyzes the provided content and generates a digest of the
    specified type, condensing the information while preserving important details
    and staying within the length limit.
    """
    content: str = Field(description="Content to digest")
    digest_type: str = Field(default="summary", description="Type of digest to create")
    max_length: Optional[int] = Field(default=200, description="Maximum length of digest")


# System Event Schemas

class WebSearchInput(BaseModel):
    """Input schema for web.search event.
    
    This event performs web searches to gather current information from the internet.
    It can search across multiple sources or focus on specific domains based on the
    query requirements.
    
    Expected behavior: Executes a web search using the provided query and returns
    relevant results from the internet, including titles, URLs, and snippets.
    Results are limited to the specified number and can be filtered by source.
    """
    query: str = Field(description="Search query")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")
    source: Optional[str] = Field(default=None, description="Optional search source")

class WebFetchInput(BaseModel):
    """Input schema for web.fetch event.
    
    This event fetches the content of a web page.
    """
    url: str = Field(description="URL to fetch")