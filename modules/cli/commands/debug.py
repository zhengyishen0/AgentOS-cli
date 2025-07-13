"""
Debug and Development Commands

Commands for debugging, event inspection, and development tools.
"""


def register_debug_commands(registry):
    """Register debug and development commands"""
    
    @registry.command(help="Show event bus debug info", category="Debug")
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

    @registry.command(help="Clear event history", category="Debug")
    def clear_events(cli, args):
        """Clear event bus history"""
        if hasattr(cli.event_bus, 'clear_history'):
            cli.event_bus.clear_history()
            cli.console.print("[green]Event history cleared[/green]")
        else:
            cli.console.print("[red]Event history clearing not available[/red]")
        return True

    @registry.command(help="Show recent events", category="Debug")
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