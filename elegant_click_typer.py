"""
Elegant Click + Typer integration with slash command autocompletion
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Callable, List

import typer
import click
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

# Initialize Typer with Rich
app = typer.Typer(
    help="Claude Code - AI coding assistant",
    rich_markup_mode="rich"
)
console = Console()


class SlashCommand:
    """Decorator and registry for slash commands using Click style"""

    def __init__(self):
        self.commands: Dict[str, dict] = {}
        self._completion_cache = None

    def command(self, name: str = None, **attrs):
        """
        Click-style decorator for slash commands.

        Args:
            name: Command name (defaults to function name with /)
            aliases: List of alternative names
            help: Help text
            hidden: Hide from help listing
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

    def create_dynamic_completer(self) -> Completer:
        """Create a smarter completer that shows on '/' press"""
        class SlashCompleter(Completer):
            def __init__(self, command_registry):
                self.registry = command_registry

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

        return SlashCompleter(self)

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
slash = SlashCommand()


# Define slash commands using Click-style decorators
@slash.command(aliases=['/q', '/quit'], help="Exit the application")
def exit_command(cli, args):
    """Exit Claude Code"""
    cli.running = False
    return False


@slash.command(help="Show available commands", category="Help")
def help(cli, args):
    """Display all available slash commands"""
    click.echo()
    click.secho("Available Commands", fg='cyan', bold=True)
    click.echo("=" * 40)

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
                click.style(alias_text, fg='dim')
            )

    click.echo()
    return True


@slash.command(aliases=['/cls'], help="Clear the screen", category="Utility")
def clear(cli, args):
    """Clear the terminal screen"""
    click.clear()
    return True


@slash.command(help="Show session status", category="Session")
def status(cli, args):
    """Display current session information"""
    click.secho("\nSession Status", fg='cyan', bold=True)
    click.echo(f"Model: {cli.model}")
    click.echo(f"Messages: {len(cli.messages)}")
    click.echo(f"Running: {cli.running}")
    return True


@slash.command(help="Toggle verbose output", category="Settings")
def verbose(cli, args):
    """Toggle verbose mode on/off"""
    cli.verbose = not cli.verbose
    status = "ON" if cli.verbose else "OFF"
    click.secho(f"Verbose mode: {status}", fg='yellow')
    return True


@slash.command(help="Switch model (opus/sonnet)", category="Settings")
def model(cli, args):
    """Switch between Claude models"""
    if args:
        cli.model = args
    else:
        # Toggle between models
        cli.model = "sonnet" if cli.model == "opus" else "opus"
    click.secho(f"Model switched to: {cli.model}", fg='green')
    return True


@slash.command(help="Save session to file", category="Session")
def save(cli, args):
    """Save the current session"""
    filename = args or "session.json"
    # Implement save logic
    click.secho(f"Session saved to: {filename}", fg='green')
    return True


class InteractiveCLI:
    """Main interactive CLI using Click + prompt_toolkit"""

    def __init__(self, model: str = "opus"):
        self.running = True
        self.model = model
        self.messages = []
        self.verbose = False
        self.history = FileHistory('.claude_history')
        self.completer = slash.create_dynamic_completer()

        # Key bindings to force completion on '/'
        self.key_bindings = KeyBindings()

        @self.key_bindings.add('/')
        def _(event):
            """Force completion menu when / is pressed"""
            event.current_buffer.insert_text('/')
            event.current_buffer.start_completion()

    def get_input(self) -> str:
        """Get input with slash command completion"""
        return prompt(
            '> ',
            completer=self.completer,
            history=self.history,
            key_bindings=self.key_bindings,
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
            enable_history_search=True,
            mouse_support=True,
        )

    def process_message(self, message: str):
        """Process a regular message"""
        self.messages.append({"role": "user", "content": message})

        # Simulate response
        import time
        with click.progressbar(
            length=100,
            label='Thinking',
            bar_template='%(label)s [%(bar)s] %(info)s'
        ) as bar:
            for i in range(100):
                bar.update(10)
                time.sleep(0.05)

        response = f"I received your message: {message}"
        self.messages.append({"role": "assistant", "content": response})
        click.echo(click.style("Assistant: ", fg='green', bold=True) + response)

    def run(self):
        """Main interaction loop"""
        # Welcome message using Click's styling
        click.clear()
        click.echo(click.style(
            '✸ Welcome to Claude Code!', fg='yellow', bold=True))
        click.echo(click.style(
            'Type /help for commands, or start chatting', dim=True))
        click.echo()

        while self.running:
            try:
                # Get input with completions
                user_input = self.get_input()

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith('/'):
                    slash.execute(self, user_input)
                else:
                    # Regular message
                    self.process_message(user_input)

            except (EOFError, KeyboardInterrupt):
                click.echo("\nUse /exit to quit")
            except Exception as e:
                click.secho(f"Error: {e}", fg='red')


# Typer commands for CLI entry points
@app.command()
def chat(
    model: str = typer.Option("opus", "--model", "-m",
                              help="Model to use (opus/sonnet)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Start an interactive Claude Code session.

    Examples:
        claude-code chat
        claude-code chat --model sonnet
        claude-code chat --verbose
    """
    cli = InteractiveCLI(model=model)
    cli.verbose = verbose
    cli.run()


@app.command()
def quick(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option("opus", "--model", "-m"),
):
    """
    Send a quick message without entering interactive mode.

    Example:
        claude-code quick "What is Python?"
    """
    with console.status("[yellow]Thinking...[/yellow]"):
        # Simulate API call
        import time
        time.sleep(1)

    console.print(
        f"[green]Response:[/green] Here's a response to '{message}' using {model}")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s",
                              help="Show current config"),
    set_model: Optional[str] = typer.Option(
        None, "--model", help="Set default model"),
):
    """Manage Claude Code configuration"""
    if show:
        click.echo("Current configuration:")
        click.echo(f"  Model: opus")
        click.echo(f"  History: enabled")
    elif set_model:
        click.echo(f"Model set to: {set_model}")
    else:
        click.echo("Use --show to see config or --model to set default")


@app.callback()
def callback(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version"),
):
    """Claude Code - AI coding assistant"""
    if version:
        click.echo("Claude Code v1.0.0")
        raise typer.Exit()


# Additional slash commands can be added easily
@slash.command(help="Show thinking process", hidden=True)
def think(cli, args):
    """Toggle thinking display (hidden command)"""
    # Hidden from help but still works
    click.echo("Thinking mode toggled")
    return True


if __name__ == "__main__":
    app()
