"""
CLI Commands Module

Organizes slash commands by category for better maintainability.
"""

from .system import register_system_commands
from .thread import register_thread_commands  
from .debug import register_debug_commands
from .utility import register_utility_commands


def register_all_commands(registry):
    """Register all command categories with the given registry"""
    register_system_commands(registry)
    register_thread_commands(registry)
    register_debug_commands(registry)
    register_utility_commands(registry)