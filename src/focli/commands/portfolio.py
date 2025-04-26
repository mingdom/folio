"""
Portfolio management commands for the Folio CLI.

This module provides commands for managing and analyzing portfolios.
"""

from typing import Any

from rich.box import ROUNDED
from rich.table import Table

from src.focli.formatters import display_portfolio_summary, format_currency
from src.focli.utils import load_portfolio


def portfolio_command(args: list[str], state: dict[str, Any], console):
    """View and analyze portfolio.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if we have a subcommand
    if not args:
        console.print(
            "[bold yellow]Usage:[/bold yellow] portfolio <subcommand> [options]"
        )
        console.print("Available subcommands: list, summary, load")
        console.print("Type 'help portfolio' for more information.")
        return

    subcommand = args[0].lower()
    subcommand_args = args[1:]

    if subcommand == "list":
        portfolio_list(subcommand_args, state, console)
    elif subcommand == "summary":
        portfolio_summary(subcommand_args, state, console)
    elif subcommand == "load":
        portfolio_load(subcommand_args, state, console)
    else:
        console.print(f"[bold red]Unknown subcommand:[/bold red] {subcommand}")
        console.print("Available subcommands: list, summary, load")


def portfolio_list(args: list[str], state: dict[str, Any], console):  # noqa: ARG001
    """List all positions in the portfolio.

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

    # Create a table of positions
    table = Table(title="Portfolio Positions", box=ROUNDED)
    table.add_column("Ticker", style="cyan")
    table.add_column("Beta", style="yellow", justify="right")
    table.add_column("Net Exposure", style="green", justify="right")
    table.add_column("Stock Value", style="green", justify="right")
    table.add_column("Option Value", style="green", justify="right")
    table.add_column("Options", style="magenta", justify="right")

    # Add rows for each position
    for group in state["portfolio_groups"]:
        stock_value = group.stock_position.market_value if group.stock_position else 0
        option_value = (
            sum(op.market_value for op in group.option_positions)
            if group.option_positions
            else 0
        )
        option_count = len(group.option_positions) if group.option_positions else 0

        table.add_row(
            group.ticker,
            f"{group.beta:.2f}",
            format_currency(group.net_exposure),
            format_currency(stock_value),
            format_currency(option_value),
            f"{option_count}",
        )

    console.print(table)


def portfolio_summary(args: list[str], state: dict[str, Any], console):  # noqa: ARG001
    """Show a summary of the portfolio.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio_summary"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Display the portfolio summary
    display_portfolio_summary(state["portfolio_summary"], console)


def portfolio_load(args: list[str], state: dict[str, Any], console):
    """Load a portfolio from a CSV file.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if we have a path
    if not args:
        console.print("[bold yellow]Usage:[/bold yellow] portfolio load <path>")
        console.print("Type 'help portfolio load' for more information.")
        return

    # Get the path
    path = args[0]

    try:
        # Load the portfolio
        load_portfolio(path, state, console)

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error loading portfolio:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())
