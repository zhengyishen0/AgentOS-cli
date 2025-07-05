"""Event handlers for AgentOS EventBus system."""

# Import all handlers to ensure they are registered
from .agent_handlers import (
    agent_think,
    agent_chain,
    agent_decide
)

from .thread_handlers import (
    thread_match,
    thread_summarize,
    thread_create,
    thread_archived
)

from .memory_handlers import (
    memory_append,
    memory_search,
    memory_digest
)

from .task_handlers import (
    task_schedule,
    task_register,
    task_list
)

from .system_handlers import (
    user_input,
    user_notify,
    web_search
)

__all__ = [
    # Agent handlers
    'agent_think',
    'agent_chain',
    'agent_decide',
    
    # Thread handlers
    'thread_match',
    'thread_summarize',
    'thread_create',
    'thread_archived',
    
    # Memory handlers
    'memory_append',
    'memory_search',
    'memory_digest',
    
    # Task handlers
    'task_schedule',
    'task_register',
    'task_list',
    
    # System handlers
    'user_input',
    'user_notify',
    'web_search',
    
]