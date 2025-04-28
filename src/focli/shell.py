"""
Interactive shell for the Folio CLI.

This module provides the main entry point for the Folio CLI interactive shell.
"""

import argparse
import os
import traceback

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console

from src.focli.commands import execute_command, get_command_registry
from src.focli.commands.simulate import simulate_command
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


def initialize_state():
    """Initialize the application state.

    Returns:
        Dictionary containing the initial application state
    """
    return {
        "portfolio_groups": None,
        "portfolio_summary": None,
        "loaded_portfolio": None,
        "last_simulation": None,
        "simulation_history": [],
        "last_position": None,
        "position_simulations": {},
        "filtered_groups": None,
        "simulation_presets": {
            "default": {"range": 20.0, "steps": 13},
            "detailed": {"range": 20.0, "steps": 21, "detailed": True},
            "quick": {"range": 10.0, "steps": 5},
        },
        "command_history": [],
    }


def load_default_portfolio(state, console):
    """Try to load the default portfolio.

    Args:
        state: Application state
        console: Rich console for output

    Returns:
        True if portfolio was loaded successfully, False otherwise
    """
    default_portfolio = "private-data/portfolio-private.csv"
    try:
        load_portfolio(default_portfolio, state, console)
        return True
    except Exception as e:
        console.print(f"[yellow]Could not load default portfolio: {e}[/yellow]")
        console.print(
            "[yellow]Use 'portfolio load <path>' to load a portfolio.[/yellow]"
        )
        return False


def main():
    """Main entry point for the Folio CLI."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Folio CLI")
    parser.add_argument(
        "--simulate", action="store_true", help="Run simulation directly"
    )
    parser.add_argument(
        "--preset", type=str, help="Simulation preset to use (default, quick, detailed)"
    )
    args = parser.parse_args()

    console = Console()

    # Initialize application state
    state = initialize_state()

    # If direct simulation is requested
    if args.simulate:
        console.print("[bold cyan]Folio CLI - Direct Simulation[/bold cyan]")

        # Try to load default portfolio
        if load_default_portfolio(state, console):
            # Run simulation with optional preset
            sim_args = []
            if args.preset:
                sim_args = ["-p", args.preset]

            # Execute simulation command
            simulate_command(sim_args, state, console)
            return
        else:
            console.print(
                "[bold red]Error:[/bold red] Cannot run simulation without a portfolio."
            )
            console.print(
                "Please run the CLI without --simulate to load a portfolio first."
            )
            return

    # Regular interactive mode
    console.print("[bold cyan]Folio Interactive Shell[/bold cyan]")
    console.print("Type 'help' for available commands.")

    # Create history file in user's home directory
    history_file = os.path.expanduser("~/.folio_history")

    # Create session with auto-completion and history
    session = PromptSession(
        completer=create_completer(), history=FileHistory(history_file)
    )

    # Try to load default portfolio
    load_default_portfolio(state, console)

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

            # Execute the command
            execute_command(text, state, console)

            # Add to command history
            state["command_history"].append(text)

        except KeyboardInterrupt:
            # Handle Ctrl+C
            console.print("[yellow]Use 'exit' to exit the application.[/yellow]")
        except EOFError:
            # Handle Ctrl+D
            break
        except Exception as e:
            # Handle other exceptions
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print(traceback.format_exc())


def confirm_exit():
    """Confirm exit with the user.

    Returns:
        Always returns True to exit without confirmation
    """
    return True  # Skip confirmation and exit directly


if __name__ == "__main__":
    main()
