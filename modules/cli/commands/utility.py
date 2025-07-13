"""
Utility Commands

Miscellaneous utility commands for enhanced user experience.
"""


def register_utility_commands(registry):
    """Register utility commands"""
    
    @registry.command(help="Toggle mouse mode for text selection", category="Utility")
    def mouse(cli, args):
        """Toggle mouse mode on/off for text selection"""
        cli._mouse_enabled = not cli._mouse_enabled
        status = "ON" if cli._mouse_enabled else "OFF"
        feature = "CLI features" if cli._mouse_enabled else "Text selection"
        default_note = " (default)" if not cli._mouse_enabled else ""
        cli.console.print(f"[yellow]Mouse mode: {status}{default_note} - {feature} enabled[/yellow]")
        return True