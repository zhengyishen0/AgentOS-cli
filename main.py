"""
AgentOS CLI - EventChain Architecture Implementation
"""

import asyncio
import logging
from typing import Dict, Any

from modules.eventbus.event_bus import InMemoryEventBus
from modules.eventbus.event_chain import EventChainExecutor
from modules.eventbus.thread_manager import ThreadManager

# Import all event handlers
from modules.eventbus.event_handlers import (
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
        self.event_bus = InMemoryEventBus()
        self.thread_manager = ThreadManager()
        self.executor = EventChainExecutor(self.event_bus, self.thread_manager)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the event bus and register all handlers."""
        if self._initialized:
            return
            
        logger.info("Initializing AgentOS EventChain Runtime...")
        
        # Register agent handlers (core AI functionality)
        await self.event_bus.subscribe("agent.think", agent_handlers.agent_think)
        await self.event_bus.subscribe("agent.chain", agent_handlers.agent_chain)
        await self.event_bus.subscribe("agent.decide", agent_handlers.agent_decide)
        
        # Register thread handlers
        await self.event_bus.subscribe("thread.match", thread_handlers.thread_match)
        await self.event_bus.subscribe("thread.summarize", thread_handlers.thread_summarize)
        await self.event_bus.subscribe("thread.create", thread_handlers.thread_create)
        await self.event_bus.subscribe("thread.archived", thread_handlers.thread_archived)
        
        # Register memory handlers
        await self.event_bus.subscribe("memory.append", memory_handlers.memory_append)
        await self.event_bus.subscribe("memory.search", memory_handlers.memory_search)
        await self.event_bus.subscribe("memory.digest", memory_handlers.memory_digest)
        
        # Register task handlers
        await self.event_bus.subscribe("task.schedule", task_handlers.task_schedule)
        await self.event_bus.subscribe("task.register", task_handlers.task_register)
        await self.event_bus.subscribe("task.list", task_handlers.task_list)
        
        # Register system handlers
        await self.event_bus.subscribe("user.input", system_handlers.user_input)
        await self.event_bus.subscribe("user.notify", system_handlers.user_notify)
        await self.event_bus.subscribe("web.search", system_handlers.web_search)
        
        self._initialized = True
        logger.info("AgentOS Runtime initialized successfully")
    
    async def process_user_input(self, text: str) -> Dict[str, Any]:
        """Process user input through the standard EventChain flow.
        
        Standard flow: user.input → thread.match → agent.think
        
        Args:
            text: User input text
            
        Returns:
            Final result from the event chain
        """
        # Standard event chain for user input processing
        chain = [
            {"event": "user.input", "params": {"text": text}},
            {"event": "thread.match", "params": {"input": "{user.input.result.text}"}},
            {"event": "agent.think", "params": {
                "thread_id": "{thread.match.result.thread_id}",
                "prompt": "{user.input.result.text}"
            }}
        ]
        
        # Execute the chain
        result = await self.executor.execute_chain(chain, "main_session")
        return result
    
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
    
    print("🤖 AgentOS CLI - EventChain Architecture")
    print("Type 'exit' to quit, 'help' for commands")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            elif user_input.lower() == 'help':
                print("""
Available commands:
- exit: Quit the CLI
- help: Show this help message
- debug: Show event bus history
- clear: Clear event history
- Any other text: Process as user input through EventChain
                """)
                continue
            elif user_input.lower() == 'debug':
                history = runtime.event_bus.get_event_history()
                print(f"Event history: {len(history)} events")
                for event in history[-5:]:  # Show last 5 events
                    print(f"  {event.timestamp}: {event.type} - {event.data}")
                continue
            elif user_input.lower() == 'clear':
                runtime.event_bus.clear_history()
                print("Event history cleared")
                continue
            
            # Process user input through EventChain
            result = await runtime.process_user_input(user_input)
            
            # Display result
            if result.success:
                print(f"✅ Chain executed successfully in {result.total_execution_time_ms:.2f}ms")
                
                # Try to extract meaningful response
                for event in result.events:
                    if event.result and not event.error:
                        if hasattr(event.result, 'get') and event.result.get('message'):
                            print(f"📝 {event.result['message']}")
                        elif event.event == 'agent.think':
                            print(f"🤔 Agent thinking result: {event.result}")
            else:
                print(f"❌ Chain execution failed: {result.error}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            print(f"❌ Error: {e}")


async def main():
    """Main entry point."""
    await run_cli()


if __name__ == "__main__":
    asyncio.run(main())
