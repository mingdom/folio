"""
Interactive shell for the Folio CLI.

This module provides the main entry point for the Folio CLI interactive shell.
"""

import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import confirm
from rich.console import Console

from src.focli.commands import execute_command, get_command_registry
from src.focli.utils import load_portfolio


def create_completer():
    """Create a nested completer for command auto-completion.

    Returns:
        NestedCompleter for command auto-completion
    """
    # Build a nested completer from the command registry
    commands = get_command_registry()

    # Create completion dictionary with subcommands and parameters
    completion_dict = {}
    for cmd_name, cmd_info in commands.items():
        if cmd_info.get("subcommands"):
            completion_dict[cmd_name] = {
                subcmd: None for subcmd in cmd_info["subcommands"]
            }
        else:
            completion_dict[cmd_name] = None

    return NestedCompleter.from_nested_dict(completion_dict)

def main():
    """Main entry point for the Folio CLI."""
    console = Console()
    console.print("[bold cyan]Folio Interactive Shell[/bold cyan]")
    console.print("Type 'help' for available commands.")

    # Create history file in user's home directory
    history_file = os.path.expanduser("~/.folio_history")

    # Create session with auto-completion and history
    session = PromptSession(
        completer=create_completer(),
        history=FileHistory(history_file)
    )

    # Initialize application state
    state = {
        "portfolio_groups": None,
        "portfolio_summary": None,
        "last_simulation": None,
        "loaded_portfolio": None,
    }

    # Try to load default portfolio
    default_portfolio = "private-data/portfolio-private.csv"
    try:
        load_portfolio(default_portfolio, state, console)
    except Exception as e:
        console.print(f"[yellow]Could not load default portfolio: {e}[/yellow]")
        console.print("[yellow]Use 'portfolio load <path>' to load a portfolio.[/yellow]")

    # Main REPL loop
    while True:
        try:
            # Get user input
            text = session.prompt("folio> ")

            if not text.strip():
                continue

            # Handle exit command directly
            if text.strip().lower() == "exit":
                if confirm_exit():
                    break
                continue

            # Process the command
            execute_command(text, state, console)

        except KeyboardInterrupt:
            # Handle Ctrl+C
            console.print("\n[yellow]Use 'exit' to exit the application.[/yellow]")
            continue
        except EOFError:
            # Handle Ctrl+D
            console.print("\nGoodbye!")
            break
        except Exception as e:
            # Handle unexpected errors
            console.print(f"[bold red]Error:[/bold red] {e!s}")

    console.print("Goodbye!")

def confirm_exit():
    """Confirm exit with the user.

    Returns:
        True if the user confirms, False otherwise
    """
    return confirm("Are you sure you want to exit?")

if __name__ == "__main__":
    main()
