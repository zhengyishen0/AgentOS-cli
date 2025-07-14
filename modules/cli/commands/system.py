"""
System Commands

Core system commands like exit, help, status, and clear.
"""

import click


def register_system_commands(registry):
    """Register system-level commands"""
    
    @registry.command("/exit", aliases=["/q", "/quit"], help="Exit AgentOS CLI", category="System")
    def exit_command(cli, args):
        """Exit AgentOS CLI"""
        cli._running = False
        click.secho("👋 Goodbye!", fg='green')
        return False

    @registry.command("/reload", help="Reload event handlers only", category="System")
    def reload_command(cli, args):
        """Reload only the event handlers without affecting other state"""
        click.secho("🔄 Reloading event handlers...", fg='yellow')
        
        # Reload all event handlers
        async def reload_event_handlers():
            try:
                # Re-import all handler modules to re-register events
                import importlib
                import modules.handlers.agent_handlers
                import modules.handlers.thread_handlers
                import modules.handlers.memory_handlers
                import modules.handlers.task_handlers
                import modules.handlers.system_handlers
                
                # Reload the modules to re-register handlers
                importlib.reload(modules.handlers.agent_handlers)
                importlib.reload(modules.handlers.thread_handlers)
                importlib.reload(modules.handlers.memory_handlers)
                importlib.reload(modules.handlers.task_handlers)
                importlib.reload(modules.handlers.system_handlers)
                
                # Get updated event count
                if cli.event_bus and hasattr(cli.event_bus, 'list_events'):
                    registered_events = cli.event_bus.list_events()
                    click.secho(f"✅ Reloaded {len(registered_events)} event handlers", fg='green')
                
            except Exception as e:
                click.secho(f"❌ Error reloading event handlers: {e}", fg='red')
        
        # Schedule event handler reload for next iteration
        cli._pending_coroutine = reload_event_handlers()
        
        return True

    @registry.command(help="Show available commands", category="Help")
    def help(cli, args):
        """Display all available slash commands"""
        click.echo()
        click.secho("🤖 AgentOS CLI - EventChain Architecture", fg='cyan', bold=True)
        click.echo("=" * 50)

        # Group by category
        categories = {}
        seen = set()

        for cmd, info in registry.commands.items():
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
        
        # Add keyboard shortcuts help
        click.echo()
        click.secho("⌨️  Keyboard Shortcuts:", fg='magenta', bold=True)
        click.secho("  • Ctrl+P - Switch to previous (older) thread", fg='white')
        click.secho("  • Ctrl+N - Switch to next (newer) thread", fg='white')
        click.secho("  • ↑↓ arrows - Navigate in /thread selection", fg='white')
        
        # Add text selection help
        click.echo()
        click.secho("💡 Text Selection Tips:", fg='magenta', bold=True)
        click.secho("  • Text selection is enabled by default (mouse mode: OFF)", fg='white')
        click.secho("  • Hold Shift while selecting text (works in most terminals)", fg='white')
        click.secho("  • Use Ctrl+Shift+C to copy selected text", fg='white')
        click.secho("  • Use /mouse command to toggle mouse mode if needed", fg='white')
        click.secho("  • Use /clear to clear screen for easier selection", fg='white')
        return True

    @registry.command(aliases=["/cls"], help="Clear the screen", category="Utility")
    def clear(cli, args):
        """Clear the terminal screen"""
        click.clear()
        return True

    @registry.command(help="Show system status", category="System")
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