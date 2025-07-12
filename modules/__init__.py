"""AgentOS Modules - Global Instances

This module provides centralized global instances for the AgentOS system,
ensuring consistent access across all modules while keeping the code clean.
"""

from .eventbus.event_bus import ConcurrentEventBus
from .providers.cli_provider import CLIProvider
from .providers.thread_manager import ThreadManager
from .eventbus.event_chain import EventChainExecutor

# Create global instances
thread_manager = ThreadManager()
eventbus = ConcurrentEventBus(persistence_enabled=True)
cli_provider = CLIProvider(eventbus, thread_manager)
executor = EventChainExecutor(eventbus, thread_manager)

# Export them for easy access
__all__ = ['eventbus', 'cli_provider', 'thread_manager', 'executor']
