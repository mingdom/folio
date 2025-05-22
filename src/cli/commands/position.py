"""
Position commands for the Folio CLI.

This module provides a unified position analysis command that shows both
position composition and risk metrics in a single view.
"""

import typer
from rich.console import Console
from rich.table import Table

from src.folib.services.portfolio_service import group_positions_by_ticker
from src.folib.services.position_service import analyze_position

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
    show_legs: bool = typer.Option(
        False, "--show-legs", help="Show detailed option leg information"
    ),
    show_greeks: bool = typer.Option(False, "--show-greeks", help="Show option Greeks"),
):
    """
    Analyze position details and risk metrics for a ticker.

    Example usage:
      position SPY                    # Basic position analysis
      position --show-legs SPY        # Show detailed option legs
      position --show-greeks SPY      # Include option Greeks
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

        # Separate stock and option positions
        stock_positions = [p for p in positions if p.position_type == "stock"]
        option_positions = [p for p in positions if p.position_type == "option"]

        # === POSITION DETAILS SECTION ===
        console.print(f"\n[bold]Position Analysis for {ticker}[/bold]")

        # Display stock positions
        if stock_positions:
            table = Table(title=f"{ticker} Stock Positions")
            table.add_column("Quantity", justify="right")
            table.add_column("Price", justify="right")
            table.add_column("Value", justify="right")
            table.add_column("Cost Basis", justify="right")

            for position in stock_positions:
                table.add_row(
                    format_quantity(position.quantity),
                    format_currency(position.price),
                    format_currency(position.market_value),
                    format_currency(position.cost_basis)
                    if position.cost_basis
                    else "N/A",
                )

            console.print(table)

        # Display option positions
        if option_positions:
            if show_legs:
                # Detailed option information
                table = Table(title=f"{ticker} Option Positions")
                table.add_column("Type", justify="left")
                table.add_column("Strike", justify="right")
                table.add_column("Expiry", justify="left")
                table.add_column("Quantity", justify="right")
                table.add_column("Price", justify="right")
                table.add_column("Value", justify="right")

                for position in option_positions:
                    table.add_row(
                        position.option_type.upper(),
                        format_currency(position.strike),
                        position.expiry.strftime("%Y-%m-%d"),
                        format_quantity(position.quantity),
                        format_currency(position.price),
                        format_currency(position.market_value),
                    )
            else:
                # Summary option information
                table = Table(title=f"{ticker} Option Summary")
                table.add_column("# of Options", justify="right")
                table.add_column("Total Value", justify="right")

                table.add_row(
                    str(len(option_positions)),
                    format_currency(sum(p.market_value for p in option_positions)),
                )

            console.print(table)

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

        # === RISK ANALYSIS SECTION ===

        # Analyze each position for risk metrics
        position_analyses = []
        failed_positions = []
        for position in positions:
            try:
                analysis = analyze_position(position)
                position_analyses.append(analysis)
            except Exception as e:
                failed_positions.append((position, e))
                console.print(
                    f"[red]Error:[/red] Failed to analyze {position.ticker} ({position.position_type}): {e}"
                )

        # Only show risk section if we have successful analyses
        if position_analyses:
            console.print("\n[bold]Risk Metrics[/bold]")

            # Create risk metrics table
            table = Table(title=f"{ticker} Risk Analysis")
            table.add_column("Metric", style="bold")
            table.add_column("Value", justify="right")

            # Calculate total metrics
            total_exposure = sum(a.get("exposure", 0) for a in position_analyses)
            total_beta_adjusted = sum(
                a.get("beta_adjusted_exposure", 0) for a in position_analyses
            )

            # Add rows for risk metrics
            table.add_row("Market Exposure", format_currency(total_exposure))
            table.add_row(
                "Beta-Adjusted Exposure", format_currency(total_beta_adjusted)
            )

            # Get beta if available
            beta = next((a.get("beta") for a in position_analyses if "beta" in a), None)
            if beta is not None:
                table.add_row("Beta", f"{beta:.2f}")

            console.print(table)

            # Display Greeks if requested and available
            if show_greeks and any("delta" in a for a in position_analyses):
                greeks_table = Table(title=f"{ticker} Option Greeks")
                greeks_table.add_column("Greek", style="bold")
                greeks_table.add_column("Value", justify="right")

                # Calculate total Greeks
                total_delta = sum(
                    a.get("delta", 0) * a.get("quantity", 0) * 100
                    for a in position_analyses
                    if "delta" in a
                )

                # Add rows for Greeks
                greeks_table.add_row("Delta", f"{total_delta:.2f}")

                # Add other Greeks when implemented in folib

                console.print(greeks_table)
        else:
            console.print(
                "\n[yellow]Warning:[/yellow] Could not calculate risk metrics due to analysis errors"
            )

    except Exception as e:
        console.print(f"[red]Error analyzing position:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Interactive mode command functions


def position_analyze(state, args):
    """Analyze position details and risk metrics (interactive mode)."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    # Parse arguments
    if not args:
        console.print("[red]Error:[/red] Missing ticker symbol")
        console.print("Usage: position <TICKER> [--show-legs] [--show-greeks]")
        return

    ticker = args[0].upper()
    show_legs = "--show-legs" in args
    show_greeks = "--show-greeks" in args

    try:
        # Group positions by ticker
        grouped_positions = group_positions_by_ticker(state.portfolio.positions)

        # Check if the ticker exists in the portfolio
        if ticker not in grouped_positions:
            console.print(f"[red]Error:[/red] Ticker {ticker} not found in portfolio")
            return

        # Get positions for the ticker
        positions = grouped_positions[ticker]

        # Separate stock and option positions
        stock_positions = [p for p in positions if p.position_type == "stock"]
        option_positions = [p for p in positions if p.position_type == "option"]

        # === POSITION DETAILS SECTION ===
        console.print(f"\n[bold]Position Analysis for {ticker}[/bold]")

        # Display stock positions
        if stock_positions:
            table = Table(title=f"{ticker} Stock Positions")
            table.add_column("Quantity", justify="right")
            table.add_column("Price", justify="right")
            table.add_column("Value", justify="right")
            table.add_column("Cost Basis", justify="right")

            for position in stock_positions:
                table.add_row(
                    format_quantity(position.quantity),
                    format_currency(position.price),
                    format_currency(position.market_value),
                    format_currency(position.cost_basis)
                    if position.cost_basis
                    else "N/A",
                )

            console.print(table)

        # Display option positions
        if option_positions:
            if show_legs:
                # Detailed option information
                table = Table(title=f"{ticker} Option Positions")
                table.add_column("Type", justify="left")
                table.add_column("Strike", justify="right")
                table.add_column("Expiry", justify="left")
                table.add_column("Quantity", justify="right")
                table.add_column("Price", justify="right")
                table.add_column("Value", justify="right")

                for position in option_positions:
                    table.add_row(
                        position.option_type.upper(),
                        format_currency(position.strike),
                        position.expiry.strftime("%Y-%m-%d"),
                        format_quantity(position.quantity),
                        format_currency(position.price),
                        format_currency(position.market_value),
                    )
            else:
                # Summary option information
                table = Table(title=f"{ticker} Option Summary")
                table.add_column("# of Options", justify="right")
                table.add_column("Total Value", justify="right")

                table.add_row(
                    str(len(option_positions)),
                    format_currency(sum(p.market_value for p in option_positions)),
                )

            console.print(table)

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

        # === RISK ANALYSIS SECTION ===

        # Analyze each position for risk metrics
        position_analyses = []
        failed_positions = []
        for position in positions:
            try:
                analysis = analyze_position(position)
                position_analyses.append(analysis)
            except Exception as e:
                failed_positions.append((position, e))
                console.print(
                    f"[red]Error:[/red] Failed to analyze {position.ticker} ({position.position_type}): {e}"
                )

        # Only show risk section if we have successful analyses
        if position_analyses:
            console.print("\n[bold]Risk Metrics[/bold]")

            # Create risk metrics table
            table = Table(title=f"{ticker} Risk Analysis")
            table.add_column("Metric", style="bold")
            table.add_column("Value", justify="right")

            # Calculate total metrics
            total_exposure = sum(a.get("exposure", 0) for a in position_analyses)
            total_beta_adjusted = sum(
                a.get("beta_adjusted_exposure", 0) for a in position_analyses
            )

            # Add rows for risk metrics
            table.add_row("Market Exposure", format_currency(total_exposure))
            table.add_row(
                "Beta-Adjusted Exposure", format_currency(total_beta_adjusted)
            )

            # Get beta if available
            beta = next((a.get("beta") for a in position_analyses if "beta" in a), None)
            if beta is not None:
                table.add_row("Beta", f"{beta:.2f}")

            console.print(table)

            # Display Greeks if requested and available
            if show_greeks and any("delta" in a for a in position_analyses):
                greeks_table = Table(title=f"{ticker} Option Greeks")
                greeks_table.add_column("Greek", style="bold")
                greeks_table.add_column("Value", justify="right")

                # Calculate total Greeks
                total_delta = sum(
                    a.get("delta", 0) * a.get("quantity", 0) * 100
                    for a in position_analyses
                    if "delta" in a
                )

                # Add rows for Greeks
                greeks_table.add_row("Delta", f"{total_delta:.2f}")

                # Add other Greeks when implemented in folib

                console.print(greeks_table)
        else:
            console.print(
                "\n[yellow]Warning:[/yellow] Could not calculate risk metrics due to analysis errors"
            )

    except Exception as e:
        console.print(f"[red]Error analyzing position:[/red] {e!s}")
