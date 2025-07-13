"""
AgentOS CLI - Command Line Interface Module

A sophisticated CLI system with:
- Command registration and execution
- Auto-completion and history
- Rich formatting and interactive features
- Thread-aware operations
"""

from .provider import EnhancedCLIProvider
from .registry import SlashCommandRegistry

__all__ = [
    'EnhancedCLIProvider',
    'SlashCommandRegistry'
]