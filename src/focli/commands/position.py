"""
Position analysis commands for the Folio CLI.

This module provides commands for analyzing specific position groups.
"""

from typing import Any

from src.focli.formatters import display_position_details
from src.focli.utils import find_position_group, parse_args


def position_command(args: list[str], state: dict[str, Any], console):
    """Analyze a specific position group.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio_groups"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Check if we have a ticker
    if not args:
        console.print("[bold yellow]Usage:[/bold yellow] position <ticker> [options]")
        console.print("Type 'help position' for more information.")
        return

    # Get the ticker
    ticker = args[0].upper()
    position_args = args[1:]

    # Define argument specifications
    arg_specs = {
        'detailed': {
            'type': bool,
            'default': True,
            'help': 'Show detailed information',
            'aliases': ['-d', '--detailed', '--no-detailed']
        }
    }

    try:
        # Parse arguments
        parsed_args = parse_args(position_args, arg_specs)

        detailed = parsed_args['detailed']

        # Find the position group
        group = find_position_group(ticker, state["portfolio_groups"])

        if not group:
            console.print(f"[bold red]Position not found:[/bold red] {ticker}")
            return

        # Display detailed position information
        display_position_details(group, detailed, console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error analyzing position:[/bold red] {e!s}")
        import traceback
        console.print(traceback.format_exc())
