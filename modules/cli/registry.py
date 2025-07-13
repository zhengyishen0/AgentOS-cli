"""
Slash Command Registry System

Handles registration, discovery, and execution of slash commands
with Click-style decorators and auto-completion support.
"""

from typing import Dict, Callable, Any
import click
from prompt_toolkit.completion import WordCompleter, Completer, Completion


class SlashCommandRegistry:
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