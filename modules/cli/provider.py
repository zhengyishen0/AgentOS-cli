"""
Enhanced CLI Provider

Core CLI provider with clean architecture, focused only on:
- Input/output handling
- Event bus integration 
- Thread management
- Async session management
"""

import asyncio
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone
import logging

from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from modules.providers.thread_manager import ThreadManager
from modules.eventbus import Thread, ConcurrentEventBus
from .registry import SlashCommandRegistry
from .commands import register_all_commands

logger = logging.getLogger(__name__)


class EnhancedCLIProvider:
    """Enhanced CLI Provider with clean architecture and modular commands"""

    def __init__(self, event_bus=None, thread_manager=None):
        """Initialize the enhanced CLI provider."""
        # Core AgentOS components
        self.event_bus: ConcurrentEventBus = event_bus
        self.thread_manager: ThreadManager = thread_manager
        self.session_id: Optional[str] = None
        self._running: bool = False
        
        # Thread navigation state
        self._threads_cache: List[Thread] = []
        self._current_thread_index: int = -1
        self._current_thread_id: Optional[str] = None
        self._threads_loaded: bool = False
        self._pending_coroutine = None
        self._mouse_enabled: bool = False
        
        # Enhanced UI components
        self.console = Console()
        self.history = FileHistory('modules/cli/command_history.txt')
        
        # Command system
        self.command_registry = SlashCommandRegistry()
        register_all_commands(self.command_registry)
        
        # Input handling
        self.key_bindings = KeyBindings()
        self._setup_key_bindings()
        self.completer = self.command_registry.create_dynamic_completer(self)
        
        # Display options
        self._tree_style = True  # Toggle between bullet and tree style (tree is default)

    def _setup_key_bindings(self):
        """Setup keyboard shortcuts for thread navigation"""
        
        # Ctrl+P for previous thread (older) - vim-style
        @self.key_bindings.add('c-p')
        def ctrl_previous_thread(event):
            """Go to previous (older) thread with Ctrl+P"""
            # Use synchronous thread switching to avoid coroutine warning
            self._sync_switch_to_thread("back")
            # Force the prompt to refresh with new thread info
            event.app.invalidate()

        # Ctrl+N for next thread (newer) - vim-style
        @self.key_bindings.add('c-n')
        def ctrl_next_thread(event):
            """Go to next (newer) thread with Ctrl+N"""
            # Use synchronous thread switching to avoid coroutine warning
            self._sync_switch_to_thread("next")
            # Force the prompt to refresh with new thread info
            event.app.invalidate()

    def _sync_switch_to_thread(self, direction: str) -> None:
        """Synchronous thread switching for key bindings"""
        if not self._threads_cache:
            print("\n⚠️  No threads available")
            return
        
        if direction == "back":
            # Switch to older thread (higher index)
            if self._current_thread_index >= len(self._threads_cache) - 1:
                print("\n⚠️  No older threads available")
                return
            self._current_thread_index += 1
        elif direction == "next":
            # Switch to newer thread (lower index)
            if self._current_thread_index <= 0:
                print("\n⚠️  No newer threads available")
                return
            self._current_thread_index -= 1
        
        # Update current thread
        thread_data = self._threads_cache[self._current_thread_index]
        self._current_thread_id = thread_data.thread_id
        
        # Show the switch confirmation with simple, clean formatting
        direction_arrow = "←" if direction == "back" else "→"
        key_name = "Ctrl+P" if direction == "back" else "Ctrl+N"
        
        # Get clean thread info without Rich markup for display
        if self._current_thread_index >= 0 and self._current_thread_index < len(self._threads_cache):
            thread_data = self._threads_cache[self._current_thread_index]
            title = thread_data.title
            if len(title) > 50:
                title = title[:47] + "..."
            thread_info = f"{thread_data.thread_id}: {title}"
        else:
            thread_info = "Unknown thread"
        
        # Clean format matching the original style
        print(f"\n✅ Switched to thread: {thread_info}")

    async def _load_threads_cache(self) -> None:
        """Load all threads into memory cache for navigation."""
        try:
            if self._threads_loaded:
                return
                
            with self.console.status("[yellow]Loading threads...[/yellow]"):
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
            with self.console.status("[yellow]Creating new thread...[/yellow]"):
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
            return "[dim]No thread selected[/dim]"
        
        if self._current_thread_index >= 0 and self._current_thread_index < len(self._threads_cache):
            thread_data = self._threads_cache[self._current_thread_index]
            title = thread_data.title
            # Truncate if too long
            if len(title) > 60:
                title = title[:57] + "..."
            return f"[cyan]{thread_data.thread_id}[/cyan]: [white]{title}[/white]"
        
        return f"[dim]Unknown thread[/dim]"

    async def _switch_to_thread(self, direction: str) -> None:
        """Switch to previous or next thread."""
        if not self._threads_cache:
            print("\n⚠️  No threads available")
            return
        
        if direction == "back":
            if self._current_thread_index >= len(self._threads_cache) - 1:
                print("\n⚠️  No older threads available")
                return
            self._current_thread_index += 1
        elif direction == "next":
            if self._current_thread_index <= 0:
                print("\n⚠️  No newer threads available")
                return
            self._current_thread_index -= 1
        
        # Update current thread
        thread_data = self._threads_cache[self._current_thread_index]
        self._current_thread_id = thread_data.thread_id
        
        # Use clean formatting consistent with sync version
        title = thread_data.title
        if len(title) > 50:
            title = title[:47] + "..."
        thread_info = f"{thread_data.thread_id}: {title}"
        
        print(f"\n✅ Switched to thread: {thread_info}")

    async def _list_threads(self) -> None:
        """Display list of top 10 threads."""
        if not self._threads_cache:
            self.console.print("[blue]No threads available[/blue]")
            return
        
        self.console.print("\n[bold cyan]🧵 Available Threads (Top 10):[/bold cyan]")
        
        for i, thread_data in enumerate(self._threads_cache[:10]):
            title = thread_data.title
            if len(title) > 50:
                title = title[:47] + "..."
            
            # Mark current thread
            marker = "[bold green]→[/bold green] " if i == self._current_thread_index else "  "
            self.console.print(f"{marker}{i+1}. [cyan]{thread_data.thread_id}[/cyan]: [white]{title}[/white]")
        
        if len(self._threads_cache) > 10:
            self.console.print(f"[dim]... and {len(self._threads_cache) - 10} more threads[/dim]")
        self.console.print()

    async def _interactive_thread_selection(self) -> None:
        """Interactive thread picker with arrow key navigation"""
        if not self._threads_cache:
            self.console.print("[blue]No threads available[/blue]")
            return
        
        # Show up to 15 threads for selection
        display_threads = self._threads_cache[:15]
        selected_index = 0  # Start with first thread selected
        
        # Find current thread in the list to pre-select it
        for i, thread in enumerate(display_threads):
            if thread.thread_id == self._current_thread_id:
                selected_index = i
                break
        
        self.console.print("\n[bold cyan]🧵 Select a Thread (use ↑↓ arrows, Enter to select, Esc to cancel):[/bold cyan]")
        if len(self._threads_cache) > 15:
            self.console.print(f"[dim]Showing first 15 of {len(self._threads_cache)} threads[/dim]")
        self.console.print()
        
        try:
            from prompt_toolkit import Application
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.layout.containers import HSplit
            from prompt_toolkit.layout.layout import Layout
            from prompt_toolkit.widgets import TextArea
            from prompt_toolkit.application.current import get_app
            
            # Create key bindings for arrow navigation
            kb = KeyBindings()
            result = {"selected": None, "cancelled": False}
            
            @kb.add('up')
            def move_up(event):
                nonlocal selected_index
                if selected_index > 0:
                    selected_index -= 1
                    update_display()
            
            @kb.add('down') 
            def move_down(event):
                nonlocal selected_index
                if selected_index < len(display_threads) - 1:
                    selected_index += 1
                    update_display()
            
            @kb.add('enter')
            def select_thread(event):
                result["selected"] = selected_index
                event.app.exit()
            
            @kb.add('escape')
            @kb.add('c-c')
            def cancel(event):
                result["cancelled"] = True
                event.app.exit()
            
            def update_display():
                """Update the thread list display"""
                lines = []
                for i, thread_data in enumerate(display_threads):
                    title = thread_data.title
                    if len(title) > 50:
                        title = title[:47] + "..."
                    
                    if i == selected_index:
                        # Highlighted selection
                        lines.append(f" ► {i+1:2d}. {title} ({thread_data.thread_id})")
                    else:
                        # Normal item
                        lines.append(f"   {i+1:2d}. {title} ({thread_data.thread_id})")
                
                # Clear previous display and show new one
                self.console.clear()
                self.console.print("\n[bold cyan]🧵 Select a Thread (use ↑↓ arrows, Enter to select, Esc to cancel):[/bold cyan]")
                if len(self._threads_cache) > 15:
                    self.console.print(f"[dim]Showing first 15 of {len(self._threads_cache)} threads[/dim]")
                self.console.print()
                
                for line in lines:
                    self.console.print(line)
            
            # Create a simple text area for the interface
            text_area = TextArea(
                text="",
                read_only=True,
                scrollbar=False,
                wrap_lines=False,
            )
            
            # Create layout
            layout = Layout(HSplit([text_area]))
            
            # Create application
            app = Application(
                layout=layout,
                key_bindings=kb,
                full_screen=False,
                mouse_support=False,
            )
            
            # Show initial display
            update_display()
            
            # Run the application
            await app.run_async()
            
            # Process result
            if result["cancelled"]:
                self.console.print("[yellow]Thread selection cancelled[/yellow]")
            elif result["selected"] is not None:
                # Switch to selected thread
                self._current_thread_index = result["selected"]
                thread_data = display_threads[self._current_thread_index]
                self._current_thread_id = thread_data.thread_id
                self.console.print(f"[green]✅ Switched to thread:[/green] {self._get_current_thread_title()}")
                
        except ImportError:
            # Fallback to number-based selection if prompt_toolkit widgets not available
            self.console.print("[yellow]Arrow key navigation not available, using number selection[/yellow]")
            await self._fallback_thread_selection(display_threads)
        except (EOFError, KeyboardInterrupt):
            self.console.print("[yellow]Thread selection cancelled[/yellow]")
        except Exception as e:
            logger.warning(f"Thread selection error: {e}")
            # Fallback to number selection
            await self._fallback_thread_selection(display_threads)

    async def _fallback_thread_selection(self, display_threads):
        """Fallback number-based thread selection"""
        self.console.print(f"[dim]Enter thread number (1-{len(display_threads)}) or press Enter to cancel:[/dim]")
        
        try:
            from prompt_toolkit import PromptSession
            prompt_session = PromptSession()
            choice = await prompt_session.prompt_async("Thread # > ")
            choice = choice.strip()
            
            if not choice:  # User pressed Enter to cancel
                self.console.print("[yellow]Thread selection cancelled[/yellow]")
                return
            
            try:
                thread_num = int(choice)
                if 1 <= thread_num <= len(display_threads):
                    # Switch to selected thread
                    self._current_thread_index = thread_num - 1
                    thread_data = display_threads[self._current_thread_index]
                    self._current_thread_id = thread_data.thread_id
                    self.console.print(f"[green]✅ Switched to thread:[/green] {self._get_current_thread_title()}")
                else:
                    self.console.print(f"[red]Invalid thread number. Please enter 1-{len(display_threads)}[/red]")
            except ValueError:
                self.console.print("[red]Invalid input. Please enter a number.[/red]")
                
        except (EOFError, KeyboardInterrupt):
            self.console.print("[yellow]Thread selection cancelled[/yellow]")

    async def _show_thread_history(self) -> None:
        """Display the chat history of the current thread."""
        if not self._current_thread_id:
            self.console.print("[yellow]No thread selected[/yellow]")
            return
        
        try:
            with self.console.status("[yellow]Loading thread history...[/yellow]"):
                thread = await self.thread_manager.get_thread(self._current_thread_id)
                
            if not thread:
                self.console.print(f"[red]Thread {self._current_thread_id} not found[/red]")
                return
            
            self.console.print(f"\n[bold cyan]📜 Chat History for Thread:[/bold cyan] [{thread.thread_id}] {thread.title}")
            self.console.print(f"[dim]Title:[/dim] {thread.title}")
            self.console.print(f"[dim]Created:[/dim] {thread.created_at}")
            self.console.print(f"[dim]Updated:[/dim] {thread.updated_at}")
            self.console.print(f"[dim]Summary:[/dim] {thread.summary}")
            self.console.rule("[dim]Chat History[/dim]")
            
            if not thread.events:
                self.console.print("[blue]No events in this thread yet[/blue]")
                return
            
            # Display the 10 latest events in chronological order
            filtered_events = [x for x in thread.events if x.name not in ("thread.created")]
            sorted_events = sorted(filtered_events, key=lambda x: x.timestamp)
            recent_events = sorted_events[-10:] if len(sorted_events) > 10 else sorted_events
            
            # Track chain events and their children for indented display
            chain_events = {}
            processed_events = set()
            
            # First pass: identify chain events and their children
            for event in recent_events:
                if event.name == "agent.chain" and event.result and isinstance(event.result, dict):
                    chain_id = event.event_id if hasattr(event, 'event_id') else id(event)
                    chain_events[chain_id] = {
                        'parent': event,
                        'children': []
                    }
                    
                    # Look for child events that were executed as part of this chain
                    if 'events' in event.result:
                        for child_event_data in event.result['events']:
                            if isinstance(child_event_data, dict) and 'name' in child_event_data:
                                # Find the actual event object in recent_events
                                for recent_event in recent_events:
                                    if (recent_event.name == child_event_data['name'] and 
                                        recent_event.timestamp > event.timestamp and
                                        id(recent_event) not in processed_events):
                                        chain_events[chain_id]['children'].append(recent_event)
                                        processed_events.add(id(recent_event))
                                        break
            
            # Second pass: display events with indentation
            for event in recent_events:
                # Skip if this event is a child of a chain (will be displayed with parent)
                if id(event) in processed_events:
                    continue
                    
                timestamp = event.timestamp.strftime("%H:%M:%S") if hasattr(event.timestamp, 'strftime') else str(event.timestamp)
                
                # Format different event types with rich styling
                if event.name == "user.input":
                    self.console.print(f"[dim][{timestamp}][/dim] [blue]👨 User:[/blue] {event.data.get('input', '')}")
                elif event.name == "thread.match":
                    user_input = event.data.get('input', '')
                    if user_input:
                        self.console.print(f"[dim][{timestamp}][/dim] [blue]👨 User:[/blue] {user_input}")
                elif event.name == "agent.reply":
                    message = event.data.get('message', '')
                    self.console.print(f"[dim][{timestamp}][/dim] [green]🤖 Agent:[/green] {message}")
                elif event.name == "agent.think":
                    if event.result and 'message' in event.result and event.result.get('event') == 'agent.reply':
                        continue
                    elif event.result and 'message' in event.result:
                        self.console.print(f"[dim][{timestamp}][/dim] [yellow]🤔 Thinking:[/yellow] {event.result['message']}")
                elif event.name == "agent.chain":
                    # Display chain parent with original message
                    original_message = event.data.get('message', 'Chain execution')
                    self.console.print(f"[dim][{timestamp}][/dim] [magenta]🔗 Chain:[/magenta] {original_message}")
                    
                    # Display child events with bullet points
                    chain_id = event.event_id if hasattr(event, 'event_id') else id(event)
                    if chain_id in chain_events:
                        for i, child_event in enumerate(chain_events[chain_id]['children']):
                            child_timestamp = child_event.timestamp.strftime("%H:%M:%S") if hasattr(child_event.timestamp, 'strftime') else str(child_event.timestamp)
                            
                            # Choose prefix based on tree style setting
                            if self._tree_style:
                                prefix = "  ├─ " if i < len(chain_events[chain_id]['children']) - 1 else "  └─ "
                            else:
                                prefix = "  • "
                            
                            if child_event.name == "agent.think":
                                if child_event.result and 'message' in child_event.result:
                                    self.console.print(f"{prefix}[dim][{child_timestamp}][/dim] [yellow]🤔 Thinking:[/yellow] {child_event.result['message']}")
                            elif child_event.name == "agent.reply":
                                message = child_event.data.get('message', '')
                                self.console.print(f"{prefix}[dim][{child_timestamp}][/dim] [green]🤖 Agent:[/green] {message}")
                            else:
                                # Generic child event display
                                self.console.print(f"{prefix}[dim][{child_timestamp}][/dim] [white]📊 {child_event.name}:[/white] {child_event.data}")
                elif event.name == "thread.created":
                    self.console.print(f"[dim][{timestamp}][/dim] [cyan]🧵 Thread created[/cyan]")
                else:
                    # Generic event display for other events
                    self.console.print(f"[dim][{timestamp}][/dim] [white]📊 {event.name}:[/white] {event.data}")
            
            self.console.rule()
            if len(thread.events) > 10:
                self.console.print(f"[dim]Showing 10 latest events (total: {len(thread.events)})[/dim]")
            else:
                self.console.print(f"[dim]Total events: {len(thread.events)}[/dim]")
            self.console.print()
            
        except Exception as e:
            logger.error(f"Failed to show thread history: {e}")
            self.console.print(f"[red]Error loading thread history: {e}[/red]")

    async def get_input(self) -> str:
        """Get input with enhanced completion and history"""
        thread_title = self._get_current_thread_title()
        
        try:
            # Use prompt_toolkit's async interface
            from prompt_toolkit import PromptSession
            from prompt_toolkit.patch_stdout import patch_stdout
            
            # Create dynamic prompt that updates when thread changes
            from prompt_toolkit.filters import Condition
            
            def get_dynamic_prompt():
                """Dynamic prompt that updates when thread changes"""
                current_title = self._get_current_thread_title()
                clean_title = current_title.replace('[cyan]', '').replace('[/cyan]', '').replace('[white]', '').replace('[/white]', '').replace('[dim]', '').replace('[/dim]', '')
                return f"\n{clean_title}\n> "
            
            mouse_condition = Condition(lambda: self._mouse_enabled)
            
            prompt_session = PromptSession(
                message=get_dynamic_prompt,  # Use dynamic prompt function
                completer=self.completer,
                history=self.history,
                key_bindings=self.key_bindings,
                auto_suggest=AutoSuggestFromHistory(),
                complete_while_typing=True,
                enable_history_search=True,
                mouse_support=mouse_condition,  # Dynamic mouse support
            )
            
            # Use async prompt with proper stdout patching
            with patch_stdout():
                result = await prompt_session.prompt_async()
                return result.strip()
                
        except (EOFError, KeyboardInterrupt):
            return "exit"
        except Exception as e:
            # Fallback to simple input if prompt_toolkit fails
            logger.warning(f"Prompt toolkit error: {e}, falling back to simple input")
            clean_title = thread_title.replace('[cyan]', '').replace('[/cyan]', '').replace('[white]', '').replace('[/white]', '').replace('[dim]', '').replace('[/dim]', '')
            prompt_text = f"\n{clean_title}\n> "
            return input(prompt_text).strip()

    async def publish_event(self, name: str, data: Dict[str, Any], source: str = "cli") -> Dict[str, Any]:
        """Publish an event to the event bus."""
        try:
            result = await self.event_bus.publish(name, data, source)
            logger.debug(f"Published event {name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to publish event {name}: {e}")
            return {"error": str(e)}

    async def publish_user_input(self, input: str, thread_id: str = None) -> None:
        """Process user input through the event system."""
        # Use current thread ID if not provided
        if thread_id is None:
            thread_id = self._current_thread_id or "new_thread"
        
        # Publish user.input → thread.match → agent.think
        data = {"input": input, "thread_id": thread_id}
        with self.console.status("[yellow]Processing...[/yellow]"):
            await self.publish_event("thread.match", data)

    async def run_interactive(self) -> None:
        """Run the enhanced interactive CLI session."""
        self._running = True
        self.session_id = f"agentos_session_{datetime.now(timezone.utc).isoformat()}"
        
        # Rich welcome message
        self.console.clear()
        self.console.print("✨ [bold yellow]Welcome to AgentOS CLI![/bold yellow]")
        self.console.print("[dim]Type /help for commands, or start chatting[/dim]")
        self.console.rule("[dim]EventChain Architecture[/dim]")
        
        # Load threads at startup
        await self._load_threads_cache()
        
        while self._running:
            try:
                # Get input with completions
                user_input = await self.get_input()

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith('/'):
                    self.command_registry.execute(self, user_input)
                else:
                    # Regular message - process through EventChain
                    await self.publish_user_input(user_input)
                
                # Check if there's a pending coroutine to execute (from slash commands or key bindings)
                if self._pending_coroutine:
                    await self._pending_coroutine
                    self._pending_coroutine = None
                    
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]Use /exit to quit[/dim]")
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                self.console.print(f"[red]Error: {e}[/red]")