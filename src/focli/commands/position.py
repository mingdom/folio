"""
Position analysis commands for the Folio CLI.

This module provides commands for analyzing specific position groups.
"""

from typing import Any

from src.focli.formatters import (
    display_position_details,
    display_position_risk_analysis,
    display_position_simulation,
)
from src.focli.utils import (
    find_position_group,
    generate_spy_changes,
    parse_args,
    simulate_position_with_spy_changes,
)


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

    # Check if we have a subcommand
    if len(args) > 1 and args[1] in ["details", "risk", "simulate"]:
        subcommand = args[1]
        position_args = args[2:]

        if subcommand == "details":
            position_details(ticker, position_args, state, console)
        elif subcommand == "risk":
            position_risk(ticker, position_args, state, console)
        elif subcommand == "simulate":
            position_simulate(ticker, position_args, state, console)
    else:
        # Default to details
        position_args = args[1:]
        position_details(ticker, position_args, state, console)


def position_details(ticker: str, args: list[str], state: dict[str, Any], console):
    """Show detailed information about a position.

    Args:
        ticker: Ticker symbol
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        "detailed": {
            "type": bool,
            "default": True,
            "help": "Show detailed information",
            "aliases": ["-d", "--detailed", "--no-detailed"],
        }
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)
        detailed = parsed_args["detailed"]

        # Find the position group
        group = find_position_group(ticker, state["portfolio_groups"])

        if not group:
            console.print(f"[bold red]Position not found:[/bold red] {ticker}")
            return

        # Display detailed position information
        display_position_details(group, detailed, console)

        # Store the last viewed position in state
        state["last_position"] = group

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error analyzing position:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())


def position_risk(ticker: str, args: list[str], state: dict[str, Any], console):
    """Show risk analysis for a position.

    Args:
        ticker: Ticker symbol
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        "detailed": {
            "type": bool,
            "default": False,
            "help": "Show detailed information",
            "aliases": ["-d", "--detailed"],
        }
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)
        detailed = parsed_args["detailed"]

        # Find the position group
        group = find_position_group(ticker, state["portfolio_groups"])

        if not group:
            console.print(f"[bold red]Position not found:[/bold red] {ticker}")
            return

        # Display risk analysis
        display_position_risk_analysis(group, detailed, console)

        # Store the last viewed position in state
        state["last_position"] = group

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error analyzing position risk:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())


def position_simulate(ticker: str, args: list[str], state: dict[str, Any], console):
    """Simulate a position with SPY changes.

    Args:
        ticker: Ticker symbol
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        "range": {
            "type": float,
            "default": 20.0,
            "help": "SPY change range in percent",
            "aliases": ["-r", "--range"],
        },
        "steps": {
            "type": int,
            "default": 13,
            "help": "Number of steps in the simulation",
            "aliases": ["-s", "--steps"],
        },
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)
        range_pct = parsed_args["range"]
        steps = parsed_args["steps"]

        # Find the position group
        group = find_position_group(ticker, state["portfolio_groups"])

        if not group:
            console.print(f"[bold red]Position not found:[/bold red] {ticker}")
            return

        # Generate SPY changes
        spy_changes = generate_spy_changes(range_pct, steps)

        # Run the simulation
        console.print(
            f"[bold]Simulating {ticker} with SPY range ±{range_pct}% and {steps} steps...[/bold]"
        )

        # Simulate the position
        results = simulate_position_with_spy_changes(group, spy_changes)

        # Store results in state
        if "position_simulations" not in state:
            state["position_simulations"] = {}
        state["position_simulations"][ticker] = results
        state["last_position"] = group

        # Display the results
        display_position_simulation(results, console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error simulating position:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())
