"""
Position commands for the Folio CLI.

This module provides implementations of the position commands for the Folio CLI,
including details and risk.
"""

import typer
from rich.console import Console
from rich.table import Table

from src.folib.services.portfolio_service import group_positions_by_ticker
from src.folib.services.position_service import analyze_position
from src.folib.services.ticker_service import ticker_service

from ..formatters import format_currency, format_quantity
from .utils import load_portfolio

# Create Typer app for position commands
position_app = typer.Typer(help="Analyze a specific position")

# Create console for rich output
console = Console()


@position_app.callback()
def position_callback():
    """Analyze a specific position in the portfolio."""
    pass


@position_app.command("details")
def position_details_cmd(
    ticker: str = typer.Argument(..., help="Ticker symbol to analyze"),
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
    show_legs: bool = typer.Option(
        False, "--show-legs", help="Show detailed option leg information"
    ),
):
    """View detailed composition of a position."""
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

        # Display position details
        console.print(f"\n[bold]Position Details for {ticker}[/bold]")

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
        else:
            console.print(f"[yellow]No stock positions found for {ticker}[/yellow]")

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
        else:
            console.print(f"[yellow]No option positions found for {ticker}[/yellow]")

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

    except Exception as e:
        console.print(f"[red]Error analyzing position:[/red] {e!s}")
        raise typer.Exit(code=1) from e


@position_app.command("risk")
def position_risk_cmd(
    ticker: str = typer.Argument(..., help="Ticker symbol to analyze"),
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
    show_greeks: bool = typer.Option(False, "--show-greeks", help="Show option Greeks"),
):
    """Analyze risk metrics for a position."""
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

        # Analyze each position
        position_analyses = []
        for position in positions:
            try:
                analysis = analyze_position(position, ticker_service)
                position_analyses.append(analysis)
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not analyze {position.ticker}: {e!s}"
                )

        # Display risk metrics
        console.print(f"\n[bold]Risk Analysis for {ticker}[/bold]")

        # Create risk metrics table
        table = Table(title=f"{ticker} Risk Metrics")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        # Calculate total metrics
        total_exposure = sum(a.get("exposure", 0) for a in position_analyses)
        total_beta_adjusted = sum(
            a.get("beta_adjusted_exposure", 0) for a in position_analyses
        )

        # Add rows for risk metrics
        table.add_row("Market Exposure", format_currency(total_exposure))
        table.add_row("Beta-Adjusted Exposure", format_currency(total_beta_adjusted))

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

    except Exception as e:
        console.print(f"[red]Error analyzing position risk:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Interactive mode command functions


def position_details(state, args):
    """View detailed composition of a position (interactive mode)."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    # Parse arguments
    if not args:
        console.print("[red]Error:[/red] Missing ticker symbol")
        console.print("Usage: position <TICKER> details [--show-legs]")
        return

    ticker = args[0].upper()
    show_legs = "--show-legs" in args

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

        # Display position details
        console.print(f"\n[bold]Position Details for {ticker}[/bold]")

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
        else:
            console.print(f"[yellow]No stock positions found for {ticker}[/yellow]")

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
        else:
            console.print(f"[yellow]No option positions found for {ticker}[/yellow]")

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

    except Exception as e:
        console.print(f"[red]Error analyzing position:[/red] {e!s}")


def position_risk(state, args):
    """Analyze risk metrics for a position (interactive mode)."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    # Parse arguments
    if not args:
        console.print("[red]Error:[/red] Missing ticker symbol")
        console.print("Usage: position <TICKER> risk [--show-greeks]")
        return

    ticker = args[0].upper()
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

        # Analyze each position
        position_analyses = []
        for position in positions:
            try:
                analysis = analyze_position(position, ticker_service)
                position_analyses.append(analysis)
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not analyze {position.ticker}: {e!s}"
                )

        # Display risk metrics
        console.print(f"\n[bold]Risk Analysis for {ticker}[/bold]")

        # Create risk metrics table
        table = Table(title=f"{ticker} Risk Metrics")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        # Calculate total metrics
        total_exposure = sum(a.get("exposure", 0) for a in position_analyses)
        total_beta_adjusted = sum(
            a.get("beta_adjusted_exposure", 0) for a in position_analyses
        )

        # Add rows for risk metrics
        table.add_row("Market Exposure", format_currency(total_exposure))
        table.add_row("Beta-Adjusted Exposure", format_currency(total_beta_adjusted))

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

    except Exception as e:
        console.print(f"[red]Error analyzing position risk:[/red] {e!s}")
