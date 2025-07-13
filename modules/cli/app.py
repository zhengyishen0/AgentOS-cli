"""
Typer Application Entry Points

CLI application entry points using Typer for command-line interface.
"""

import asyncio
import logging
from typing import Optional

import typer
from rich.console import Console

from .provider import EnhancedCLIProvider

# Initialize Typer with Rich
app = typer.Typer(
    help="AgentOS CLI - EventChain Architecture",
    rich_markup_mode="rich"
)
console = Console()


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
        console.print("AgentOS CLI v0.1.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()