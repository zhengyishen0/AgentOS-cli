"""CLI Provider for AgentOS EventChain Architecture.

This provider handles command-line interface interactions and integrates
with the event-driven system for processing user input and displaying results.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from modules.providers.thread_manager import ThreadManager
from modules.eventbus import Thread, ConcurrentEventBus
# from modules.eventbus.event_bus import ConcurrentEventBus

logger = logging.getLogger(__name__)


class CLIProvider:
    """CLI provider for handling user interactions and event publishing."""
    
    def __init__(self, event_bus=None, thread_manager=None):
        """Initialize the CLI provider.
        """
        self.event_bus: ConcurrentEventBus = event_bus
        self.thread_manager: ThreadManager = thread_manager
        self.session_id: Optional[str] = None
        self._running: bool = False
        
        # Thread navigation state
        self._threads_cache: List[Thread] = []
        self._current_thread_index: int = -1
        self._current_thread_id: Optional[str] = None
        self._threads_loaded: bool = False
        
        
    
    async def _load_threads_cache(self) -> None:
        """Load all threads into memory cache for navigation."""
        try:
            if self._threads_loaded:
                return
                
            # Get all active threads
            self._threads_cache = await self.thread_manager.list_threads(status="active")
            self._threads_cache.sort(key=lambda x: x.updated_at, reverse=True)
            
            # Set current thread to newest
            if self._threads_cache:
                self._current_thread_index = 0
                self._current_thread_id = self._threads_cache[0].thread_id
            else:
                # No threads exist, create a new one
                await self._create_new_thread()
            
            self._threads_loaded = True
            logger.info(f"Loaded {len(self._threads_cache)} threads into cache")
            
        except Exception as e:
            logger.error(f"Failed to load threads cache: {e}")
            # Fallback: create new thread
            await self._create_new_thread()
    
    async def _create_new_thread(self) -> None:
        """Create a new thread and set it as current."""
        try:
            thread = await self.thread_manager.create_thread()
            self._current_thread_id = thread.thread_id
                
            # Add to cache at the beginning (newest)
            self._threads_cache.insert(0, thread)
            self._current_thread_index = 0
            
            logger.info(f"Created new thread: {thread.thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to create new thread: {e}")
            # Fallback to a default thread ID
            self._current_thread_id = "default_thread"
    
    def _get_current_thread_title(self) -> str:
        """Get the current thread title for display."""
        if not self._current_thread_id:
            return "No thread selected"
        
        if self._current_thread_index >= 0 and self._current_thread_index < len(self._threads_cache):
            thread_data = self._threads_cache[self._current_thread_index]
            title = thread_data.title
            # Truncate if too long
            if len(title) > 60:
                title = title[:57] + "..."
            return f"{thread_data.thread_id}: {title}"
        
        return f"{self._current_thread_id}: Unknown thread"
    
    async def _switch_to_thread(self, direction: str) -> None:
        """Switch to previous or next thread.
        
        Args:
            direction: 'back' or 'next'
        """
        if not self._threads_cache:
            self.display_output("No threads available", "warning")
            return
        
        if direction == "back":
            if self._current_thread_index >= len(self._threads_cache) - 1:
                self.display_output("No older threads available", "info")
                return
            self._current_thread_index += 1
        elif direction == "next":
            if self._current_thread_index <= 0:
                self.display_output("No newer threads available", "info")
                return
            self._current_thread_index -= 1
        
        # Update current thread
        thread_data = self._threads_cache[self._current_thread_index]
        self._current_thread_id = thread_data.thread_id
        
        self.display_output(f"Switched to thread: {self._get_current_thread_title()}", "success")
    
    async def _list_threads(self) -> None:
        """Display list of top 10 threads."""
        if not self._threads_cache:
            self.display_output("No threads available", "info")
            return
        
        self.display_output("🧵 Available Threads (Top 10):", "info")
        
        for i, thread_data in enumerate(self._threads_cache[:10]):
            title = thread_data.title
            if len(title) > 50:
                title = title[:47] + "..."
            
            # Mark current thread
            marker = "→ " if i == self._current_thread_index else "  "
            self.display_output(f"{marker}{i+1}. {thread_data.thread_id}: {title}", "info")
        
        if len(self._threads_cache) > 10:
            self.display_output(f"... and {len(self._threads_cache) - 10} more threads", "info")
    
    async def _show_thread_history(self) -> None:
        """Display the chat history of the current thread."""
        if not self._current_thread_id:
            self.display_output("No thread selected", "warning")
            return
        
        try:
            # Load the current thread
            thread = await self.thread_manager.get_thread(self._current_thread_id)
            if not thread:
                self.display_output(f"Thread {self._current_thread_id} not found", "error")
                return
            
            self.display_output(f"📜 Chat History for Thread: [{thread.thread_id}] {thread.title}", "info")
            self.display_output(f"Title: {thread.title}", "info")
            self.display_output(f"Created: {thread.created_at}", "info")
            self.display_output(f"Updated: {thread.updated_at}", "info")
            self.display_output(f"Summary: {thread.summary}", "info") 
            print("-" * 60)
            
            if not thread.events:
                self.display_output("No events in this thread yet", "info")
                return
            
            # Display the 10 latest events in chronological order
            filtered_events = [x for x in thread.events if x.name not in ("thread.created")]
            sorted_events = sorted(filtered_events, key=lambda x: x.timestamp)
            recent_events = sorted_events[-10:] if len(sorted_events) > 10 else sorted_events
            for event in recent_events:
                timestamp = event.timestamp.strftime("%H:%M:%S") if hasattr(event.timestamp, 'strftime') else str(event.timestamp)
                
                # Format different event types
                if event.name == "user.input":
                    self.display_output(event.data.get('input', ''), "user", timestamp)
                elif event.name == "thread.match":
                    # Show user input from thread.match events
                    user_input = event.data.get('input', '')
                    if user_input:
                        self.display_output(user_input, "user", timestamp)
                    # Also show thread action if available (but don't increment counter)
                    # if event.result and 'action' in event.result:
                    #     action = event.result['action']
                    #     if action == "new":
                    #         self.display_output(f"[{timestamp}] 🆕 New thread created", "thread")
                    #     elif action == "switch":
                    #         self.display_output(f"[{timestamp}] 🔄 Switched to existing thread", "thread")
                    #     elif action == "continue":
                    #         self.display_output(f"[{timestamp}] ➡️ Continued in thread", "thread")
                elif event.name == "agent.reply":
                    message = event.data.get('message', '')
                    self.display_output(message, "agent", timestamp)
                elif event.name == "agent.think":
                    if event.result and 'message' in event.result and event.result.get('event') == 'agent.reply':
                        continue
                    elif event.result and 'message' in event.result:
                        self.display_output(event.result['message'], "debug", timestamp)
                elif event.name == "agent.chain":
                    self.display_output(event.result['message'], "chain", timestamp)
                elif event.name == "thread.created":
                    self.display_output("Thread created", "thread", timestamp)
                else:
                    # Generic event display for other events
                    self.display_output(event.data, "debug", timestamp)
            
            print("-" * 60)
            if len(thread.events) > 10:
                self.display_output(f"Showing 10 latest events (total: {len(thread.events)})", "info")
            else:
                self.display_output(f"Total events: {len(thread.events)}", "info")
            
        except Exception as e:
            logger.error(f"Failed to show thread history: {e}")
            self.display_output(f"Error loading thread history: {e}", "error")
    
    async def get_user_input(self, prompt: str = "> ") -> str:
        """Get user input from the command line.
        
        Args:
            prompt: Input prompt to display
            
        Returns:
            User input string
        """
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return "exit"
    
    def display_output(self, message: str, level: str = "info", timestamp: str = None) -> None:
        """Display output to the user.
        
        Args:
            message: Message to display
            level: info | warning | error | success | debug | agent | user | thread
            timestamp: Timestamp to display
        """
        level_icons = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "success": "✅",
            "debug": "🐛",
            "agent": "🤖",
            "user": "👨",
            "thread": "🧵",
            "chain": "🔗",
        }
        
        icon = level_icons.get(level, "ℹ️")
        leader = level.capitalize()
        print(f"[{timestamp}] {icon} {leader}: {message}")
    
    def display_result(self, result: Dict[str, Any]) -> None:
        """Display event chain result in a formatted way.
        
        Args:
            result: Event chain execution result
        """
        if not result:
            return
            
        if isinstance(result, dict):
            if result.get('success') is False:
                self.display_output(f"Chain execution failed: {result.get('error', 'Unknown error')}", "error")
                return
            
            # Display execution time if available
            if 'total_execution_time_ms' in result:
                self.display_output(f"Chain executed in {result['total_execution_time_ms']:.2f}ms", "success")
            
            # Display event results
            if 'events' in result:
                for event in result['events']:
                    if event.result and not event.error:
                        self._display_event_result(event)
    
    def _display_event_result(self, event: Any) -> None:
        """Display individual event result.
        
        Args:
            event: Event result to display
        """
        if hasattr(event, 'result') and event.result:
            if isinstance(event.result, dict):
                # Handle different event types
                if event.event == 'agent.think':
                    if 'message' in event.result:
                        self.display_output(f"🤔 Agent: {event.result['message']}")
                    else:
                        self.display_output(f"🤔 Agent thinking result: {event.result}")
                elif event.event == 'user.input':
                    self.display_output(f"📝 Processed input: {event.result.get('text', '')}")
                elif event.event == 'thread.match':
                    if 'thread_id' in event.result:
                        self.display_output(f"🧵 Matched thread: {event.result['thread_id']}")
                else:
                    self.display_output(f"📊 {event.event}: {event.result}")
    
    async def publish_event(self, name: str, data: Dict[str, Any], source: str = "cli") -> Dict[str, Any]:
        """Publish an event to the event bus.
        
        Args:
            name: Name of event to publish
            data: Event data
            source: Source of the event
            
        Returns:
            Event handler results
        """
        try:
            result = await self.event_bus.publish(name, data, source)
            logger.debug(f"Published event {name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to publish event {name}: {e}")
            return {"error": str(e)}
    
    async def publish_user_input(self, input: str, thread_id: str = None) -> None:
        """Process user input through the event system.
        
        Args:
            input: User input text
            thread_id: Optional thread ID (uses current thread if not provided)
        """
        # Use current thread ID if not provided
        if thread_id is None:
            thread_id = self._current_thread_id or "new_thread"
        
        # Publish user.input → thread.match → agent.think
        data = {"input": input, "thread_id": thread_id}
        await self.publish_event("thread.match", data)


    def parse_command(self, input_text: str) -> Optional[Dict[str, Any]]:
        """Parse user input to determine if it's a special command.
        
        Args:
            input_text: User input text
            
        Returns:
            Parsed command or None if it's regular input
        """
        input_text = input_text.strip()
        
        # Check if it's a slash command
        if not input_text.startswith('/'):
            return None
            
        # Remove the slash and split into command and arguments
        command_parts = input_text[1:].split(' ', 1)
        command = command_parts[0].lower()
        args = command_parts[1] if len(command_parts) > 1 else ""
        
        # Handle slash commands
        if command == "exit":
            return {"type": "exit"}
        elif command == "help":
            return {"type": "help"}
        elif command == "debug":
            return {"type": "debug"}
        elif command == "clear":
            return {"type": "clear"}
        elif command == "chain":
            # Custom chain execution
            return {"type": "custom_chain", "chain": args}
        elif command == "status":
            return {"type": "status"}
        elif command == "threads":
            return {"type": "threads"}
        elif command == "events":
            return {"type": "events"}
        elif command == "thread":
            # Thread navigation commands
            if args == "new":
                return {"type": "thread_new"}
            elif args == "back":
                return {"type": "thread_previous"}
            elif args == "next":
                return {"type": "thread_next"}
            elif args == "list":
                return {"type": "thread_list"}
            elif args == "history":
                return {"type": "thread_history"}
            else:
                return {"type": "thread_unknown", "args": args}
        
        # Unknown slash command
        return {"type": "unknown", "command": command}
    
    def show_help(self) -> None:
        """Display help information."""
        help_text = """
🤖 AgentOS CLI - EventChain Architecture

Available slash commands:
/help     - Show this help message
/exit     - Quit the CLI
/debug    - Show event bus history
/clear    - Clear event history
/status   - Show system status
/threads  - List available threads
/events   - Show recent events
/chain <description> - Execute a custom event chain

Thread navigation commands:
/thread new      - Create and switch to new thread
/thread back     - Switch to older thread
/thread next     - Switch to newer thread
/thread list     - List top 10 threads with summaries
/thread history  - Show chat history of current thread

Any other text (without /) will be processed as user input through EventChain:
user.input → thread.match → agent.think
        """
        print(help_text)
    
    async def run_interactive(self) -> None:
        """Run the interactive CLI session."""
        self._running = True
        self.session_id = f"cli_session_{datetime.now(timezone.utc).isoformat()}"
        
        self.display_output("🤖 AgentOS CLI - EventChain Architecture", "info")
        self.display_output("Type /help for available commands", "info")
        print("-" * 50)
        
        # Load threads at startup
        await self._load_threads_cache()
        
        while self._running:
            try:
                # Display current thread title
                thread_title = self._get_current_thread_title()
                prompt = f"\n[{thread_title}]\n> "
                
                user_input = await self.get_user_input(prompt)
                
                if not user_input:
                    continue
                
                # Parse for special commands
                command = self.parse_command(user_input)
                
                if command:
                    await self._handle_command(command)
                else:
                    # Process as regular user input
                    await self.publish_user_input(user_input)
                    
            except KeyboardInterrupt:
                self.display_output("\nGoodbye!", "info")
                break
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                self.display_output(f"Error: {e}", "error")
    
    async def _handle_command(self, command: Dict[str, Any]) -> None:
        """Handle special CLI commands.
        
        Args:
            command: Parsed command
        """
        command_type = command.get("type")
        
        if command_type == "exit":
            self._running = False
            self.display_output("Goodbye!", "info")
        elif command_type == "help":
            self.show_help()
        elif command_type == "debug":
            history = self.event_bus.get_event_history()
            self.display_output(f"Event history: {len(history)} events", "debug")
            for event in history[-5:]:  # Show last 5 events
                self.display_output(f"  {event.timestamp}: {event.name} - {event.data}", "debug")
        elif command_type == "clear":
            self.event_bus.clear_history()
            self.display_output("Event history cleared", "success")
        elif command_type == "status":
            self._show_status()
        elif command_type == "threads":
            self._show_threads()
        elif command_type == "events":
            self._show_recent_events()
        elif command_type == "custom_chain":
            # This would require more sophisticated chain parsing
            self.display_output("Custom chain execution not yet implemented", "warning")
        elif command_type == "thread_new":
            await self._create_new_thread()
            self.display_output(f"Created and switched to new thread: {self._get_current_thread_title()}", "success")
        elif command_type == "thread_previous":
            await self._switch_to_thread("back")
        elif command_type == "thread_next":
            await self._switch_to_thread("next")
        elif command_type == "thread_list":
            await self._list_threads()
        elif command_type == "thread_history":
            await self._show_thread_history()
        elif command_type == "thread_unknown":
            args = command.get("args", "")
            self.display_output(f"Unknown thread command: '{args}'. Use: new, back, next, list, or history", "error")
        elif command_type == "unknown":
            unknown_cmd = command.get("command", "unknown")
            self.display_output(f"Unknown command: /{unknown_cmd}. Type /help for available commands.", "error")
    
    def _show_status(self) -> None:
        """Show system status information."""
        self.display_output("📊 System Status", "info")
        self.display_output(f"Session ID: {self.session_id}", "info")
        self.display_output(f"Running: {self._running}", "info")
        self.display_output(f"Event Bus: {'Connected' if self.event_bus else 'Not connected'}", "info")
        
        # Show thread information
        self.display_output(f"Current Thread: {self._get_current_thread_title()}", "info")
        self.display_output(f"Total Threads: {len(self._threads_cache)}", "info")
        
        # Show event bus stats if available
        if hasattr(self.event_bus, 'get_event_history'):
            history = self.event_bus.get_event_history()
            self.display_output(f"Total Events: {len(history)}", "info")
    
    def _show_threads(self) -> None:
        """Show available threads."""
        # Use the new thread listing functionality
        asyncio.create_task(self._list_threads())
    
    def _show_recent_events(self) -> None:
        """Show recent events in a more detailed format."""
        if not hasattr(self.event_bus, 'get_event_history'):
            self.display_output("Event history not available", "error")
            return
            
        history = self.event_bus.get_event_history()
        self.display_output(f"📋 Recent Events ({len(history)} total)", "info")
        
        for i, event in enumerate(history[-10:]):  # Show last 10 events
            timestamp = getattr(event, 'timestamp', 'Unknown')
            name = getattr(event, 'name', 'Unknown')
            source = getattr(event, 'source', 'Unknown')
            self.display_output(f"  {i+1}. [{timestamp}] {name} (from {source})", "debug")

