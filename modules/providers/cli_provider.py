"""CLI Provider for AgentOS EventChain Architecture.

This provider handles command-line interface interactions and integrates
with the event-driven system for processing user input and displaying results.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from ..eventbus.event_bus import eventbus

logger = logging.getLogger(__name__)


class CLIProvider:
    """CLI provider for handling user interactions and event publishing."""
    
    def __init__(self, event_bus=None):
        """Initialize the CLI provider.
        
        Args:
            event_bus: Event bus instance to use for publishing events
        """
        self.event_bus = event_bus or eventbus
        self.session_id = None
        self._running = False
    
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
    
    def display_output(self, message: str, level: str = "info") -> None:
        """Display output to the user.
        
        Args:
            message: Message to display
            level: Output level (info, warning, error, success)
        """
        level_icons = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "success": "✅",
            "debug": "🐛",
            "agent": "🤖",
        }
        
        icon = level_icons.get(level, "ℹ️")
        print(f"{icon} {message}")
    
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
    
    async def publish_event(self, event_type: str, data: Dict[str, Any], source: str = "cli") -> Dict[str, Any]:
        """Publish an event to the event bus.
        
        Args:
            event_type: Type of event to publish
            data: Event data
            source: Source of the event
            
        Returns:
            Event handler results
        """
        try:
            result = await self.event_bus.publish(event_type, data, source)
            logger.debug(f"Published event {event_type}: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return {"error": str(e)}
    
    async def process_user_input(self, text: str) -> Dict[str, Any]:
        """Process user input through the event system.
        
        Args:
            text: User input text
            
        Returns:
            Processing result
        """
        # Publish user.input → thread.match → agent.think
        result = await self.publish_event("thread.match", {"text": text})
        
        # If successful, continue with standard flow
        if not result.get("error"):
            return result
        else:
            return {"error": "Failed to process user input"}

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
        
        while self._running:
            try:
                user_input = await self.get_user_input("\n> ")
                
                if not user_input:
                    continue
                
                # Parse for special commands
                command = self.parse_command(user_input)
                
                if command:
                    await self._handle_command(command)
                else:
                    # Process as regular user input
                    result = await self.process_user_input(user_input)
                    self.display_result(result)
                    
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
                self.display_output(f"  {event.timestamp}: {event.type} - {event.data}", "debug")
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
        elif command_type == "unknown":
            unknown_cmd = command.get("command", "unknown")
            self.display_output(f"Unknown command: /{unknown_cmd}. Type /help for available commands.", "error")
    
    def _show_status(self) -> None:
        """Show system status information."""
        self.display_output("📊 System Status", "info")
        self.display_output(f"Session ID: {self.session_id}", "info")
        self.display_output(f"Running: {self._running}", "info")
        self.display_output(f"Event Bus: {'Connected' if self.event_bus else 'Not connected'}", "info")
        
        # Show event bus stats if available
        if hasattr(self.event_bus, 'get_event_history'):
            history = self.event_bus.get_event_history()
            self.display_output(f"Total Events: {len(history)}", "info")
    
    def _show_threads(self) -> None:
        """Show available threads."""
        self.display_output("🧵 Available Threads", "info")
        # This would integrate with thread storage when available
        self.display_output("Thread management not yet implemented", "warning")
    
    def _show_recent_events(self) -> None:
        """Show recent events in a more detailed format."""
        if not hasattr(self.event_bus, 'get_event_history'):
            self.display_output("Event history not available", "error")
            return
            
        history = self.event_bus.get_event_history()
        self.display_output(f"📋 Recent Events ({len(history)} total)", "info")
        
        for i, event in enumerate(history[-10:]):  # Show last 10 events
            timestamp = getattr(event, 'timestamp', 'Unknown')
            event_type = getattr(event, 'type', 'Unknown')
            source = getattr(event, 'source', 'Unknown')
            self.display_output(f"  {i+1}. [{timestamp}] {event_type} (from {source})", "debug")

