"""
Simulation commands for the Folio CLI.

This module provides commands for simulating portfolio performance under different scenarios.
"""

from typing import Any

from src.focli.formatters import display_simulation_results
from src.focli.utils import generate_spy_changes, parse_args
from src.folio.simulator import simulate_portfolio_with_spy_changes


def simulate_command(args: list[str], state: dict[str, Any], console):
    """Simulate portfolio performance with SPY changes.

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

    # Check if we have a subcommand
    if not args:
        console.print("[bold yellow]Usage:[/bold yellow] simulate <subcommand> [options]")
        console.print("Available subcommands: spy, scenario")
        console.print("Type 'help simulate' for more information.")
        return

    subcommand = args[0].lower()
    subcommand_args = args[1:]

    if subcommand == "spy":
        simulate_spy(subcommand_args, state, console)
    elif subcommand == "scenario":
        console.print("[bold yellow]Note:[/bold yellow] Scenario simulation is not yet implemented.")
    else:
        console.print(f"[bold red]Unknown subcommand:[/bold red] {subcommand}")
        console.print("Available subcommands: spy, scenario")

def simulate_spy(args: list[str], state: dict[str, Any], console):
    """Simulate portfolio performance with SPY changes.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        'range': {
            'type': float,
            'default': 20.0,
            'help': 'SPY change range in percent',
            'aliases': ['-r', '--range']
        },
        'steps': {
            'type': int,
            'default': 13,
            'help': 'Number of steps in the simulation',
            'aliases': ['-s', '--steps']
        },
        'focus': {
            'type': str,
            'default': None,
            'help': 'Comma-separated list of tickers to focus on',
            'aliases': ['-f', '--focus']
        },
        'detailed': {
            'type': bool,
            'default': False,
            'help': 'Show detailed analysis for all positions',
            'aliases': ['-d', '--detailed']
        }
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)

        range_pct = parsed_args['range']
        steps = parsed_args['steps']
        focus = parsed_args['focus']
        detailed = parsed_args['detailed']

        # Parse focus tickers if provided
        focus_tickers = None
        if focus:
            focus_tickers = [ticker.strip().upper() for ticker in focus.split(",")]

        # Generate SPY changes
        spy_changes = generate_spy_changes(range_pct, steps)

        # Run the simulation
        console.print(f"[bold]Running simulation with range ±{range_pct}% and {steps} steps...[/bold]")

        results = simulate_portfolio_with_spy_changes(
            portfolio_groups=state["portfolio_groups"],
            spy_changes=spy_changes,
            cash_like_positions=state["portfolio_summary"].cash_like_positions,
            pending_activity_value=state["portfolio_summary"].pending_activity_value,
        )

        # Store results for future reference
        state["last_simulation"] = results

        # Display the results
        display_simulation_results(results, detailed, focus_tickers, console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error running simulation:[/bold red] {e!s}")
        import traceback
        console.print(traceback.format_exc())
