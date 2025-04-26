"""
Help command for the Folio CLI.

This module provides the help command for displaying information about available commands.
"""

from typing import Any

from rich.box import ROUNDED
from rich.table import Table


def help_command(args: list[str], state: dict[str, Any], console):  # noqa: ARG001
    """Show help information.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    from src.focli.commands import get_command_registry

    # Get the command registry
    commands = get_command_registry()

    # Check if we're showing help for a specific command
    if args and args[0] in commands:
        command = args[0]
        command_info = commands[command]

        console.print(f"\n[bold]Help for command:[/bold] [cyan]{command}[/cyan]")
        console.print(f"\n{command_info['help']}\n")

        # Show subcommands if available
        if command_info.get("subcommands"):
            console.print("[bold]Subcommands:[/bold]")
            for subcommand in command_info["subcommands"]:
                console.print(f"  [cyan]{subcommand}[/cyan]")
            console.print("")

        # Show usage examples based on the command
        console.print("[bold]Usage examples:[/bold]")

        if command == "simulate":
            console.print(
                "  [green]simulate spy[/green] - Run a simulation with default parameters"
            )
            console.print(
                "  [green]simulate spy --range 10 --steps 21[/green] - Run a simulation with ±10% range and 21 steps"
            )
            console.print(
                "  [green]simulate spy --focus SPY,AAPL[/green] - Run a simulation focusing on specific tickers"
            )
            console.print(
                "  [green]simulate spy --detailed[/green] - Run a simulation with detailed position analysis"
            )

        elif command == "position":
            console.print(
                "  [green]position SPY[/green] - Show details for the SPY position"
            )
            console.print(
                "  [green]position AAPL --detailed[/green] - Show detailed information for the AAPL position"
            )

        elif command == "portfolio":
            console.print(
                "  [green]portfolio summary[/green] - Show a summary of the portfolio"
            )
            console.print(
                "  [green]portfolio load path/to/portfolio.csv[/green] - Load a portfolio from a CSV file"
            )
            console.print(
                "  [green]portfolio list[/green] - List all positions in the portfolio"
            )

        elif command == "help":
            console.print("  [green]help[/green] - Show this help message")
            console.print(
                "  [green]help simulate[/green] - Show help for the simulate command"
            )

        elif command == "exit":
            console.print("  [green]exit[/green] - Exit the application")

        console.print("")

    else:
        # Show general help
        console.print("\n[bold cyan]Folio CLI Help[/bold cyan]")
        console.print("\nAvailable commands:\n")

        # Create a table of commands
        table = Table(box=ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Subcommands", style="yellow")

        # Add rows for each command
        for name, info in commands.items():
            subcommands = (
                ", ".join(info.get("subcommands", []))
                if info.get("subcommands")
                else ""
            )
            table.add_row(name, info["help"], subcommands)

        console.print(table)

        # Show general usage
        console.print("\n[bold]General usage:[/bold]")
        console.print("  Type a command followed by any arguments or options.")
        console.print(
            "  Use [cyan]help <command>[/cyan] to get help for a specific command."
        )
        console.print("  Use [cyan]exit[/cyan] to exit the application.")
        console.print("")
