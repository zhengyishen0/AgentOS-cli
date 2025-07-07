"""
AgentOS CLI - EventChain Architecture Implementation
"""

import asyncio
import logging
from typing import Dict, Any

from modules import eventbus, cli_provider, thread_manager, executor

# Import all event handlers to trigger registration
from modules.handlers import (
    agent_handlers,
    thread_handlers,
    memory_handlers,
    task_handlers,
    system_handlers
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentOSRuntime:
    """Main AgentOS runtime with event bus and chain executor."""
    
    def __init__(self):
        self.event_bus = eventbus
        self.thread_manager = thread_manager
        self.executor = executor
        self.cli = cli_provider
        self._initialized = False
    
    async def initialize(self):
        """Initialize the event bus and register all handlers."""
        if self._initialized:
            return
            
        logger.info("Initializing AgentOS EventChain Runtime...")
        
        # Handlers are automatically registered via @eventbus.register decorators
        # Just need to verify they're loaded
        registered_events = self.event_bus.list_events()
        logger.info(f"Registered {len(registered_events)} event handlers: {', '.join(registered_events)}")
        
        self._initialized = True
        logger.info("AgentOS Runtime initialized successfully")
    
    async def process_user_input(self, text: str) -> Dict[str, Any]:
        """Process user input through the CLI provider.
        
        Args:
            text: User input text
            
        Returns:
            Processing result
        """
        return await self.cli.process_user_input(text)
    
    async def execute_custom_chain(self, chain: list, thread_id: str = "custom") -> Dict[str, Any]:
        """Execute a custom event chain.
        
        Args:
            chain: List of events to execute
            thread_id: Thread ID for context
            
        Returns:
            Event chain execution result
        """
        return await self.executor.execute_chain(chain, thread_id)


async def run_cli():
    """Run the CLI interface for AgentOS."""
    runtime = AgentOSRuntime()
    await runtime.initialize()
    await runtime.cli.run_interactive()


async def main():
    """Main entry point."""
    await run_cli()


if __name__ == "__main__":
    asyncio.run(main())
