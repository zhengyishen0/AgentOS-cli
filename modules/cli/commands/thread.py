"""
Thread Management Commands

Commands for creating, navigating, and managing conversation threads.
"""


def register_thread_commands(registry):
    """Register thread management commands"""
    
    @registry.command(help="Interactive thread selection and management", category="Thread")
    def thread(cli, args):
        """Interactive thread picker - select from list of threads"""
        cli._pending_coroutine = cli._interactive_thread_selection()
        return True
    
    @registry.command(help="Create new thread", category="Thread")
    def thread_new(cli, args):
        """Create and switch to new thread"""
        cli._pending_coroutine = cli._create_new_thread()
        cli.console.print("[yellow]Creating new thread...[/yellow]")
        return True

    @registry.command(help="Switch to previous thread", category="Thread")
    def thread_back(cli, args):
        """Switch to older thread"""
        cli._pending_coroutine = cli._switch_to_thread("back")
        return True

    @registry.command(help="Switch to next thread", category="Thread")
    def thread_next(cli, args):
        """Switch to newer thread"""
        cli._pending_coroutine = cli._switch_to_thread("next")
        return True

    @registry.command(help="List available threads", category="Thread")
    def thread_list(cli, args):
        """List top 10 threads"""
        cli._pending_coroutine = cli._list_threads()
        return True

    @registry.command(help="Show current thread history", category="Thread")
    def thread_history(cli, args):
        """Show chat history of current thread"""
        cli._pending_coroutine = cli._show_thread_history()
        return True