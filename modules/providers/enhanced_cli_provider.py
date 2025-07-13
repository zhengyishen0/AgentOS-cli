"""
Enhanced CLI Provider for AgentOS EventChain Architecture
Based on elegant_click_typer patterns with full CLI provider functionality
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Callable, List, Any
from datetime import datetime, timezone
import logging

import typer
import click
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from modules.providers.thread_manager import ThreadManager
from modules.eventbus import Thread, ConcurrentEventBus

logger = logging.getLogger(__name__)

# Initialize Typer with Rich
app = typer.Typer(
    help="AgentOS CLI - EventChain Architecture",
    rich_markup_mode="rich"
)
console = Console()


class AgentOSSlashCommand:
    """Enhanced slash command system for AgentOS with Click style decorators"""

    def __init__(self):
        self.commands: Dict[str, dict] = {}
        self._completion_cache = None

    def command(self, name: str = None, **attrs):
        """
        Click-style decorator for AgentOS slash commands.

        Args:
            name: Command name (defaults to function name with /)
            aliases: List of alternative names
            help: Help text
            hidden: Hide from help listing
            category: Command category for grouping
        """
        def decorator(func):
            # Determine command name
            cmd_name = name or f'/{func.__name__.replace("_", "-")}'

            # Store command info
            cmd_info = {
                'callback': func,
                'help': attrs.get('help', func.__doc__ or ''),
                'aliases': attrs.get('aliases', []),
                'hidden': attrs.get('hidden', False),
                'category': attrs.get('category', 'General'),
            }

            # Register main command and aliases
            self.commands[cmd_name] = cmd_info
            for alias in cmd_info['aliases']:
                self.commands[alias] = cmd_info

            return func
        return decorator

    def get_completer(self) -> WordCompleter:
        """Get a prompt_toolkit completer with all commands"""
        # Build word list with descriptions
        words = []
        meta_dict = {}
        seen_callbacks = set()

        for cmd, info in self.commands.items():
            # Skip aliases and hidden commands in completion
            if info['callback'] not in seen_callbacks and not info['hidden']:
                seen_callbacks.add(info['callback'])
                words.append(cmd)
                meta_dict[cmd] = info['help']

        return WordCompleter(
            words=words,
            meta_dict=meta_dict,
            ignore_case=True,
            sentence=True,  # Allow completion in middle of line
            match_middle=True
        )

    def create_dynamic_completer(self, cli_provider) -> Completer:
        """Create a smarter completer that shows on '/' press with thread awareness"""
        class AgentOSCompleter(Completer):
            def __init__(self, command_registry, cli_provider):
                self.registry = command_registry
                self.cli_provider = cli_provider

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor

                # Show all commands when just '/' is typed
                if text == '/':
                    seen = set()
                    for cmd, info in self.registry.commands.items():
                        if info['callback'] not in seen and not info['hidden']:
                            seen.add(info['callback'])
                            yield Completion(
                                cmd,
                                start_position=-1,
                                display=f"{cmd:<15}",
                                display_meta=info['help'][:50] +
                                '...' if len(
                                    info['help']) > 50 else info['help']
                            )

                # Filter commands as user types
                elif text.startswith('/'):
                    seen = set()
                    for cmd, info in self.registry.commands.items():
                        if cmd.startswith(text) and info['callback'] not in seen and not info['hidden']:
                            seen.add(info['callback'])
                            yield Completion(
                                cmd,
                                start_position=-len(text),
                                display=cmd,
                                display_meta=info['help'][:50] +
                                '...' if len(
                                    info['help']) > 50 else info['help']
                            )

        return AgentOSCompleter(self, cli_provider)

    def execute(self, cli_instance, command_line: str):
        """Execute a slash command"""
        parts = command_line.split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ''

        if cmd_name in self.commands:
            return self.commands[cmd_name]['callback'](cli_instance, args)
        else:
            click.secho(f"Unknown command: {cmd_name}", fg='red')
            click.echo("Type /help for available commands")
            return True


# Create global slash command registry
slash = AgentOSSlashCommand()


class EnhancedCLIProvider:
    """Enhanced CLI Provider combining elegant patterns with AgentOS functionality"""

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
        self._mouse_enabled: bool = True
        
        # Enhanced UI components
        self.console = Console()
        self.history = FileHistory('.agentos_history')
        self.completer = slash.create_dynamic_completer(self)
        
        # Key bindings to force completion on '/'
        self.key_bindings = KeyBindings()

        @self.key_bindings.add('/')
        def _(event):
            """Force completion menu when / is pressed"""
            event.current_buffer.insert_text('/')
            event.current_buffer.start_completion()
            
        # Setup slash commands
        self.setup_slash_commands()

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
            self.console.print("[yellow]No threads available[/yellow]")
            return
        
        if direction == "back":
            if self._current_thread_index >= len(self._threads_cache) - 1:
                self.console.print("[blue]No older threads available[/blue]")
                return
            self._current_thread_index += 1
        elif direction == "next":
            if self._current_thread_index <= 0:
                self.console.print("[blue]No newer threads available[/blue]")
                return
            self._current_thread_index -= 1
        
        # Update current thread
        thread_data = self._threads_cache[self._current_thread_index]
        self._current_thread_id = thread_data.thread_id
        
        self.console.print(f"[green]Switched to thread:[/green] {self._get_current_thread_title()}")

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
            
            for event in recent_events:
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
                    self.console.print(f"[dim][{timestamp}][/dim] [magenta]🔗 Chain:[/magenta] {event.result['message']}")
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
            
            # Create prompt session if not exists
            if not hasattr(self, '_prompt_session'):
                # Create mouse support condition
                from prompt_toolkit.filters import Condition
                mouse_condition = Condition(lambda: self._mouse_enabled)
                
                self._prompt_session = PromptSession(
                    completer=self.completer,
                    history=self.history,
                    key_bindings=self.key_bindings,
                    auto_suggest=AutoSuggestFromHistory(),
                    complete_while_typing=True,
                    enable_history_search=True,
                    mouse_support=mouse_condition,  # Dynamic mouse support
                )
            
            # Strip rich markup for clean display
            clean_title = thread_title.replace('[cyan]', '').replace('[/cyan]', '').replace('[white]', '').replace('[/white]', '').replace('[dim]', '').replace('[/dim]', '')
            prompt_text = f"\n{clean_title}\n> "
            
            # Use async prompt with proper stdout patching
            with patch_stdout():
                result = await self._prompt_session.prompt_async(prompt_text)
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

    def setup_slash_commands(self):
        """Setup all AgentOS slash commands using decorators"""
        
        @slash.command(aliases=['/q', '/quit'], help="Exit AgentOS CLI", category="System")
        def exit_command(cli, args):
            """Exit AgentOS CLI"""
            cli._running = False
            click.secho("👋 Goodbye!", fg='green')
            return False

        @slash.command(help="Show available commands", category="Help")
        def help(cli, args):
            """Display all available slash commands"""
            click.echo()
            click.secho("🤖 AgentOS CLI - EventChain Architecture", fg='cyan', bold=True)
            click.echo("=" * 50)

            # Group by category
            categories = {}
            seen = set()

            for cmd, info in slash.commands.items():
                if info['callback'] not in seen and not info['hidden']:
                    seen.add(info['callback'])
                    category = info.get('category', 'General')
                    if category not in categories:
                        categories[category] = []
                    categories[category].append((cmd, info))

            for category, commands in sorted(categories.items()):
                click.echo()
                click.secho(f"{category}:", fg='yellow', bold=True)
                for cmd, info in sorted(commands):
                    # Show aliases
                    aliases = [a for a in info['aliases'] if a != cmd]
                    alias_text = f" ({', '.join(aliases)})" if aliases else ""

                    click.echo(
                        click.style(f"  {cmd:<15}", fg='green') +
                        click.style(f"{info['help']}", fg='white') +
                        click.style(alias_text, fg='cyan', dim=True)
                    )

            click.echo()
            click.secho("Any other text (without /) will be processed as user input through EventChain:", fg='blue')
            click.secho("user.input → thread.match → agent.think", fg='cyan', dim=True)
            
            # Add text selection help
            click.echo()
            click.secho("💡 Text Selection Tips:", fg='magenta', bold=True)
            click.secho("  • Hold Shift while selecting text (works in most terminals)", fg='white')
            click.secho("  • Use Ctrl+Shift+C to copy selected text", fg='white')
            click.secho("  • Use /mouse command to toggle mouse mode if needed", fg='white')
            click.secho("  • Use /clear to clear screen for easier selection", fg='white')
            return True

        @slash.command(aliases=['/cls'], help="Clear the screen", category="Utility")
        def clear(cli, args):
            """Clear the terminal screen"""
            click.clear()
            return True

        @slash.command(help="Show system status", category="System")
        def status(cli, args):
            """Display current system status"""
            cli.console.print("\n[bold cyan]📊 AgentOS System Status[/bold cyan]")
            cli.console.print(f"[dim]Session ID:[/dim] {cli.session_id}")
            cli.console.print(f"[dim]Running:[/dim] [green]{cli._running}[/green]")
            cli.console.print(f"[dim]Event Bus:[/dim] [green]Connected[/green]" if cli.event_bus else "[red]Not connected[/red]")
            cli.console.print(f"[dim]Current Thread:[/dim] {cli._get_current_thread_title()}")
            cli.console.print(f"[dim]Total Threads:[/dim] {len(cli._threads_cache)}")
            
            if hasattr(cli.event_bus, 'get_event_history'):
                history = cli.event_bus.get_event_history()
                cli.console.print(f"[dim]Total Events:[/dim] {len(history)}")
            cli.console.print()
            return True

        @slash.command(help="Show event bus debug info", category="Debug")
        def debug(cli, args):
            """Show event bus history"""
            if not hasattr(cli.event_bus, 'get_event_history'):
                cli.console.print("[red]Event history not available[/red]")
                return True
                
            history = cli.event_bus.get_event_history()
            cli.console.print(f"\n[bold yellow]🐛 Event History ({len(history)} events)[/bold yellow]")
            
            for i, event in enumerate(history[-5:]):  # Show last 5 events
                timestamp = getattr(event, 'timestamp', 'Unknown')
                name = getattr(event, 'name', 'Unknown') 
                source = getattr(event, 'source', 'Unknown')
                cli.console.print(f"  {i+1}. [dim][{timestamp}][/dim] [cyan]{name}[/cyan] [dim](from {source})[/dim]")
            cli.console.print()
            return True

        @slash.command(help="Clear event history", category="Debug")
        def clear_events(cli, args):
            """Clear event bus history"""
            if hasattr(cli.event_bus, 'clear_history'):
                cli.event_bus.clear_history()
                cli.console.print("[green]Event history cleared[/green]")
            else:
                cli.console.print("[red]Event history clearing not available[/red]")
            return True

        # Thread commands - handled synchronously by storing coroutines to run later
        @slash.command(help="Create new thread", category="Thread")
        def thread_new(cli, args):
            """Create and switch to new thread"""
            # Store the coroutine to be executed by the main loop
            cli._pending_coroutine = cli._create_new_thread()
            cli.console.print("[yellow]Creating new thread...[/yellow]")
            return True

        @slash.command(help="Switch to previous thread", category="Thread")
        def thread_back(cli, args):
            """Switch to older thread"""
            cli._pending_coroutine = cli._switch_to_thread("back")
            return True

        @slash.command(help="Switch to next thread", category="Thread")
        def thread_next(cli, args):
            """Switch to newer thread"""
            cli._pending_coroutine = cli._switch_to_thread("next")
            return True

        @slash.command(help="List available threads", category="Thread")
        def thread_list(cli, args):
            """List top 10 threads"""
            cli._pending_coroutine = cli._list_threads()
            return True

        @slash.command(help="Show current thread history", category="Thread")
        def thread_history(cli, args):
            """Show chat history of current thread"""
            cli._pending_coroutine = cli._show_thread_history()
            return True

        @slash.command(help="Show recent events", category="Debug")
        def events(cli, args):
            """Show recent events in detailed format"""
            if not hasattr(cli.event_bus, 'get_event_history'):
                cli.console.print("[red]Event history not available[/red]")
                return True
                
            history = cli.event_bus.get_event_history()
            cli.console.print(f"\n[bold cyan]📋 Recent Events ({len(history)} total)[/bold cyan]")
            
            for i, event in enumerate(history[-10:]):  # Show last 10 events
                timestamp = getattr(event, 'timestamp', 'Unknown')
                name = getattr(event, 'name', 'Unknown')
                source = getattr(event, 'source', 'Unknown')
                cli.console.print(f"  {i+1}. [dim][{timestamp}][/dim] [cyan]{name}[/cyan] [dim](from {source})[/dim]")
            cli.console.print()
            return True

        @slash.command(help="Toggle mouse mode for text selection", category="Utility")
        def mouse(cli, args):
            """Toggle mouse mode on/off for text selection"""
            cli._mouse_enabled = not cli._mouse_enabled
            status = "ON" if cli._mouse_enabled else "OFF"
            feature = "CLI features" if cli._mouse_enabled else "Text selection"
            cli.console.print(f"[yellow]Mouse mode: {status} - {feature} enabled[/yellow]")
            return True

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
                    slash.execute(self, user_input)
                    # Check if there's a pending coroutine to execute
                    if self._pending_coroutine:
                        await self._pending_coroutine
                        self._pending_coroutine = None
                else:
                    # Regular message - process through EventChain
                    await self.publish_user_input(user_input)
                    
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]Use /exit to quit[/dim]")
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                self.console.print(f"[red]Error: {e}[/red]")


# Typer commands for CLI entry points
@app.command()
def chat(
    model: str = typer.Option("opus", "--model", "-m",
                              help="Model to use (opus/sonnet)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Start an interactive AgentOS CLI session.

    Examples:
        agentos-cli chat
        agentos-cli chat --model sonnet
        agentos-cli chat --verbose
    """
    # Import here to avoid circular imports
    from modules import eventbus, thread_manager
    # Import handlers to ensure proper registration (imports trigger @register decorators)
    import modules.handlers.agent_handlers
    import modules.handlers.thread_handlers  
    import modules.handlers.memory_handlers
    import modules.handlers.task_handlers
    import modules.handlers.system_handlers
    
    # Verify event registration
    registered_events = eventbus.list_events()
    console.print(f"[dim]Initialized {len(registered_events)} event handlers[/dim]")
    
    cli = EnhancedCLIProvider(event_bus=eventbus, thread_manager=thread_manager)
    
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        console.print(f"[dim]Registered events: {', '.join(sorted(registered_events))}[/dim]")
    
    asyncio.run(cli.run_interactive())


@app.command()
def quick(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option("opus", "--model", "-m", help="Model to use"),
):
    """
    Send a quick message without entering interactive mode.

    Example:
        agentos-cli quick "What is Python?"
    """
    from modules import eventbus, thread_manager
    # Import handlers to trigger registration (imports trigger @register decorators)
    import modules.handlers.agent_handlers
    import modules.handlers.thread_handlers
    import modules.handlers.memory_handlers  
    import modules.handlers.task_handlers
    import modules.handlers.system_handlers
    
    async def quick_message():
        # Initialize event handlers
        registered_events = eventbus.list_events()
        console.print(f"[dim]Initialized {len(registered_events)} event handlers[/dim]")
        
        cli = EnhancedCLIProvider(event_bus=eventbus, thread_manager=thread_manager)
        await cli._load_threads_cache()
        
        console.print(f"[cyan]Processing:[/cyan] {message}")
        console.print()
        
        await cli.publish_user_input(message)
        
        console.print(f"\n[green]✅ Message processed successfully[/green]")
    
    asyncio.run(quick_message())


@app.command()
def threads(
    list_all: bool = typer.Option(False, "--all", "-a", help="List all threads"),
    show_history: Optional[str] = typer.Option(None, "--history", "-h", help="Show history for thread ID"),
):
    """Manage AgentOS threads"""
    from modules import thread_manager
    
    async def manage_threads():
        if show_history:
            # Show specific thread history
            thread = await thread_manager.get_thread(show_history)
            if thread:
                console.print(f"[bold cyan]Thread {show_history} History:[/bold cyan]")
                # Display thread details
                console.print(f"Title: {thread.title}")
                console.print(f"Created: {thread.created_at}")
                console.print(f"Events: {len(thread.events)}")
            else:
                console.print(f"[red]Thread {show_history} not found[/red]")
        else:
            # List threads
            threads = await thread_manager.list_threads(status="active")
            console.print(f"[bold cyan]Found {len(threads)} active threads:[/bold cyan]")
            for i, thread in enumerate(threads[:10]):
                console.print(f"{i+1}. {thread.thread_id}: {thread.title}")
    
    asyncio.run(manage_threads())


@app.callback()
def callback(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version"),
):
    """AgentOS CLI - EventChain Architecture"""
    if version:
        click.echo("AgentOS CLI v0.1.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()