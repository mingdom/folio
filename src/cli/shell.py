"""
Interactive shell for the Folio CLI.

This module provides an interactive shell for the Folio CLI, allowing users
to enter commands in a REPL (Read-Eval-Print Loop) interface.
"""

import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console

from .commands.portfolio import portfolio_list, portfolio_load, portfolio_summary
from .commands.position import position_analyze
from .state import State

# Create console for rich output
console = Console()

# Create state object for the interactive shell
state = State()

# Define commands available in the interactive shell
COMMANDS = {
    "portfolio": {
        "load": portfolio_load,
        "summary": portfolio_summary,
        "list": portfolio_list,
    },
    "position": position_analyze,
    "help": None,  # Will be handled separately
    "exit": None,  # Will be handled separately
}


def get_command_completer():
    """Create a completer for the interactive shell."""
    # Flatten the command structure for completion
    words = []
    for cmd, subcmds in COMMANDS.items():
        words.append(cmd)
        if isinstance(subcmds, dict):
            # Handle dictionary of subcommands
            for subcmd in subcmds:
                words.append(f"{cmd} {subcmd}")
        # For function commands like position, just add the base command

    # Add special commands
    words.append("help")
    words.append("exit")

    return WordCompleter(words, ignore_case=True)


def process_command(command: str) -> bool:
    """
    Process a command entered in the interactive shell.

    Args:
        command: The command string entered by the user

    Returns:
        True if the shell should continue, False if it should exit
    """
    # Split the command into parts
    parts = command.strip().split()
    if not parts:
        return True

    cmd = parts[0].lower()

    # Handle exit command
    if cmd == "exit":
        return False

    # Handle help command
    if cmd == "help":
        show_help(parts[1] if len(parts) > 1 else None)
        return True

    # Handle portfolio commands
    if cmd == "portfolio":
        if len(parts) > 1 and parts[1] in COMMANDS["portfolio"]:
            # Call the appropriate command function
            subcmd = parts[1]
            args = parts[2:]
            try:
                COMMANDS["portfolio"][subcmd](state=state, args=args)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e!s}")
        else:
            # Show help for the command
            show_help("portfolio")

    # Handle position commands
    elif cmd == "position":
        if len(parts) > 1:
            # Call the position analysis function
            ticker_and_args = parts[1:]
            try:
                COMMANDS["position"](state=state, args=ticker_and_args)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e!s}")
        else:
            # Show help for the command
            show_help("position")

    # Handle other commands
    elif cmd in COMMANDS:
        # Show help for the command
        show_help(cmd)
    else:
        console.print(f"[red]Unknown command:[/red] {cmd}")
        console.print("Type [bold]help[/bold] to see available commands")

    return True


def show_help(command: str | None = None):
    """
    Show help information for commands.

    Args:
        command: The command to show help for, or None for general help
    """
    if command is None:
        console.print("[bold]Available commands:[/bold]")
        console.print(
            "  portfolio load <FILE_PATH>  - Load portfolio data from a CSV file"
        )
        console.print(
            "  portfolio summary           - Display high-level portfolio metrics"
        )
        console.print(
            "  portfolio list [options]    - List positions with filtering and sorting"
        )
        console.print("  position <TICKER>           - Show all positions for a ticker")
        console.print("  help [COMMAND]              - Display help information")
        console.print("  exit                        - Exit the interactive shell")
    elif command == "portfolio":
        console.print("[bold]Portfolio commands:[/bold]")
        console.print(
            "  portfolio load <FILE_PATH>  - Load portfolio data from a CSV file"
        )
        console.print(
            "  portfolio summary           - Display high-level portfolio metrics"
        )
        console.print(
            "  portfolio list [options]    - List positions with filtering and sorting"
        )
    elif command == "position":
        console.print("[bold]Position commands:[/bold]")
        console.print("  position <TICKER>           - Show all positions for a ticker")
    else:
        console.print(f"[red]No help available for command:[/red] {command}")


def start_interactive_shell():
    """Start the interactive shell."""
    # Create history file in user's home directory
    history_file = os.path.expanduser("~/.folio_cli_history")

    # Create prompt session with history and auto-suggest
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        completer=get_command_completer(),
    )

    # Print welcome message
    console.print("[bold]Folio CLI[/bold] - Interactive Shell")
    console.print(
        "Type [bold]help[/bold] for a list of commands or [bold]exit[/bold] to quit"
    )

    # Try to load the default portfolio if it exists
    default_portfolio_path = Path("private-data/portfolios/portfolio-default.csv")
    if default_portfolio_path.exists():
        try:
            portfolio_load(state=state, args=[str(default_portfolio_path)])
            console.print("[green]Loaded default portfolio[/green]")

            # Display portfolio summary by default
            console.print("\n[bold]Portfolio Summary:[/bold]")
            portfolio_summary(state=state, _args=[])
        except Exception as e:
            console.print(f"[yellow]Could not load default portfolio:[/yellow] {e!s}")

    # Main loop
    while True:
        try:
            # Get command from user
            command = session.prompt("folio> ")

            # Process the command
            if not process_command(command):
                break

        except KeyboardInterrupt:
            # Handle Ctrl+C
            console.print("\n[yellow]Use [bold]exit[/bold] to quit[/yellow]")

        except EOFError:
            # Handle Ctrl+D
            console.print("\n[green]Exiting...[/green]")
            break

        except Exception as e:
            # Handle other exceptions
            console.print(f"[red]Error:[/red] {e!s}")

    console.print("[green]Goodbye![/green]")
