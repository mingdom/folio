"""
Position commands for the Folio CLI.

This module provides a unified position analysis command that shows all
positions for a ticker in a single table with key metrics.
"""

import typer
from rich.console import Console
from rich.table import Table

from src.folib.services.portfolio_service import group_positions_by_ticker
from src.folib.services.position_service import get_position_beta_adjusted_exposure

from ..formatters import format_currency, format_quantity
from .utils import load_portfolio

# Create Typer app for position commands
position_app = typer.Typer(help="Analyze a specific position")

# Create console for rich output
console = Console()


@position_app.callback(invoke_without_command=True)
def position_analyze_cmd(
    ctx: typer.Context,
    ticker: str = typer.Argument(None, help="Ticker symbol to analyze"),
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
):
    """
    Analyze all positions for a ticker.

    Shows all stock and option positions for the specified ticker in a unified table
    with quantity, info, value, and beta adjusted exposure.

    Example usage:
      position SPY                    # Show all SPY positions
      position --file myport.csv SPY  # Use specific portfolio file
    """
    # If no ticker provided and there's a subcommand, let typer handle it
    if ticker is None:
        if ctx.invoked_subcommand is None:
            console.print("[red]Error:[/red] Missing ticker symbol")
            console.print("Usage: position <TICKER> [OPTIONS]")
            raise typer.Exit(code=1)
        return

    try:
        # Load the portfolio
        result = load_portfolio(file_path)
        portfolio = result["portfolio"]

        # Group positions by ticker
        grouped_positions = group_positions_by_ticker(portfolio.positions)

        # Check if the ticker exists in the portfolio
        ticker = ticker.upper()
        if ticker not in grouped_positions:
            console.print(f"[red]Error:[/red] Ticker {ticker} not found in portfolio")
            raise typer.Exit(code=1)

        # Get positions for the ticker
        positions = grouped_positions[ticker]

        # === UNIFIED POSITION DISPLAY ===
        console.print(f"\n[bold]Position Analysis for {ticker}[/bold]")

        # Create unified table for all positions
        table = Table(title=f"{ticker} Positions")
        table.add_column("Quantity", justify="right")
        table.add_column("Info", justify="left")
        table.add_column("Value", justify="right")
        table.add_column("Beta Adjusted Exposure", justify="right")

        # Add rows for each position
        for position in positions:
            # Calculate beta adjusted exposure
            try:
                beta_adjusted_exposure = get_position_beta_adjusted_exposure(position)
                beta_exposure_str = format_currency(beta_adjusted_exposure)
            except Exception as e:
                beta_exposure_str = f"Error: {e}"

            # Add row to table
            table.add_row(
                format_quantity(position.quantity),
                position.description,
                format_currency(position.market_value),
                beta_exposure_str,
            )

        console.print(table)

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

        # Calculate and display total beta adjusted exposure
        total_beta_adjusted_exposure = 0.0
        for position in positions:
            try:
                beta_adjusted_exposure = get_position_beta_adjusted_exposure(position)
                total_beta_adjusted_exposure += beta_adjusted_exposure
            except Exception:
                # Skip positions with errors
                pass

        console.print(
            f"[bold]Total Beta Adjusted Exposure:[/bold] {format_currency(total_beta_adjusted_exposure)}"
        )

    except Exception as e:
        console.print(f"[red]Error analyzing position:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Interactive mode command functions


def position_analyze(state, args):
    """Analyze all positions for a ticker (interactive mode)."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    # Parse arguments
    if not args:
        console.print("[red]Error:[/red] Missing ticker symbol")
        console.print("Usage: position <TICKER>")
        return

    ticker = args[0].upper()

    try:
        # Group positions by ticker
        grouped_positions = group_positions_by_ticker(state.portfolio.positions)

        # Check if the ticker exists in the portfolio
        if ticker not in grouped_positions:
            console.print(f"[red]Error:[/red] Ticker {ticker} not found in portfolio")
            return

        # Get positions for the ticker
        positions = grouped_positions[ticker]

        # === UNIFIED POSITION DISPLAY ===
        console.print(f"\n[bold]Position Analysis for {ticker}[/bold]")

        # Create unified table for all positions
        table = Table(title=f"{ticker} Positions")
        table.add_column("Quantity", justify="right")
        table.add_column("Info", justify="left")
        table.add_column("Value", justify="right")
        table.add_column("Beta Adjusted Exposure", justify="right")

        # Add rows for each position
        for position in positions:
            # Calculate beta adjusted exposure
            try:
                beta_adjusted_exposure = get_position_beta_adjusted_exposure(position)
                beta_exposure_str = format_currency(beta_adjusted_exposure)
            except Exception as e:
                beta_exposure_str = f"Error: {e}"

            # Add row to table
            table.add_row(
                format_quantity(position.quantity),
                position.description,
                format_currency(position.market_value),
                beta_exposure_str,
            )

        console.print(table)

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

        # Calculate and display total beta adjusted exposure
        total_beta_adjusted_exposure = 0.0
        for position in positions:
            try:
                beta_adjusted_exposure = get_position_beta_adjusted_exposure(position)
                total_beta_adjusted_exposure += beta_adjusted_exposure
            except Exception:
                # Skip positions with errors
                pass

        console.print(
            f"[bold]Total Beta Adjusted Exposure:[/bold] {format_currency(total_beta_adjusted_exposure)}"
        )

    except Exception as e:
        console.print(f"[red]Error analyzing position:[/red] {e!s}")
