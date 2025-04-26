"""
Command registry and execution for the Folio CLI.

This module provides a central registry for all commands and handles command execution.
"""

from collections.abc import Callable
from typing import Any

# Import command modules
from .help import help_command
from .portfolio import portfolio_command
from .position import position_command
from .simulate import simulate_command

# Command registry
_COMMANDS = {}


def register_command(
    name: str, handler: Callable, help_text: str, subcommands: list[str] | None = None
):
    """Register a command with the command registry.

    Args:
        name: Command name
        handler: Function that handles the command
        help_text: Help text for the command
        subcommands: List of subcommands (if any)
    """
    _COMMANDS[name] = {
        "handler": handler,
        "help": help_text,
        "subcommands": subcommands,
    }


def get_command_registry():
    """Get the command registry.

    Returns:
        Dictionary of registered commands
    """
    return _COMMANDS


def execute_command(command_line: str, state: dict[str, Any], console):
    """Execute a command from the command line.

    Args:
        command_line: Full command line to execute
        state: Application state dictionary
        console: Rich console for output
    """
    # Parse the command line
    parts = command_line.strip().split()
    if not parts:
        return

    command = parts[0].lower()
    args = parts[1:]

    # Check if the command exists
    if command not in _COMMANDS:
        console.print(f"[bold red]Unknown command:[/bold red] {command}")
        console.print("Type 'help' to see available commands.")
        return

    # Execute the command
    try:
        _COMMANDS[command]["handler"](args, state, console)
    except Exception as e:
        console.print(
            f"[bold red]Error executing command '{command}':[/bold red] {e!s}"
        )


# Import command modules

# Register commands
register_command("help", help_command, "Show help information")
register_command(
    "simulate",
    simulate_command,
    "Simulate portfolio performance with SPY changes",
    ["spy", "scenario"],
)
register_command("position", position_command, "Analyze a specific position group")
register_command(
    "portfolio",
    portfolio_command,
    "View and analyze portfolio",
    ["list", "summary", "load"],
)
register_command("exit", lambda *args: None, "Exit the application")
