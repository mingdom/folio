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


@position_app.command("analyze")
def position_cmd(
    ticker: str = typer.Argument(..., help="Ticker symbol to analyze"),
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
    show_legs: bool = typer.Option(
        False, "--show-legs", help="Show detailed option leg information"
    ),
    show_greeks: bool = typer.Option(False, "--show-greeks", help="Show option Greeks"),
):
    """Analyze a specific position for details and risk."""
    try:
        # Load the portfolio
        result = load_portfolio(file_path)
        portfolio = result["portfolio"]

        # Group positions by ticker
        grouped_positions = group_positions_by_ticker(portfolio.positions)

        # Check if the ticker exists in the portfolio
        ticker_upper = ticker.upper()
        if ticker_upper not in grouped_positions:
            console.print(f"[red]Error:[/red] Ticker {ticker_upper} not found in portfolio")
            raise typer.Exit(code=1)

        # Get positions for the ticker
        positions = grouped_positions[ticker_upper]

        # Separate stock and option positions
        stock_positions = [p for p in positions if p.position_type == "stock"]
        option_positions = [p for p in positions if p.position_type == "option"]

        # Display position details
        console.print(f"\n[bold]Position Details for {ticker_upper}[/bold]")

        # Display stock positions
        if stock_positions:
            table = Table(title=f"{ticker_upper} Stock Positions")
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
            console.print(f"[yellow]No stock positions found for {ticker_upper}[/yellow]")

        # Display option positions
        if option_positions:
            if show_legs:
                # Detailed option information
                table = Table(title=f"{ticker_upper} Option Positions")
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
                table = Table(title=f"{ticker_upper} Option Summary")
                table.add_column("# of Options", justify="right")
                table.add_column("Total Value", justify="right")

                table.add_row(
                    str(len(option_positions)),
                    format_currency(sum(p.market_value for p in option_positions)),
                )
            console.print(table)
        else:
            console.print(f"[yellow]No option positions found for {ticker_upper}[/yellow]")

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

        # Display risk analysis
        console.print(f"\n[bold]Risk Analysis for {ticker_upper}[/bold]")
        position_analyses = []
        # Note: The original instructions mentioned iterating through `positions` for the ticker.
        # The `positions` variable here already holds the list of positions for the specific ticker.
        for position in positions: # Iterate through positions for the current ticker
            try:
                # analyze_position uses ticker_service internally
                analysis = analyze_position(position)
                # Store analysis along with the position itself to access position.quantity later for delta
                position_analyses.append({"analysis": analysis, "position_obj": position})
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not analyze {position.ticker}: {e!s}"
                )

        # Risk Metrics Table
        risk_table = Table(title=f"{ticker_upper} Risk Metrics")
        risk_table.add_column("Metric", style="bold")
        risk_table.add_column("Value", justify="right")

        total_exposure = sum(pa["analysis"].get("exposure", 0) for pa in position_analyses)
        total_beta_adjusted = sum(
            pa["analysis"].get("beta_adjusted_exposure", 0) for pa in position_analyses
        )

        risk_table.add_row("Market Exposure", format_currency(total_exposure))
        risk_table.add_row("Beta-Adjusted Exposure", format_currency(total_beta_adjusted))

        beta = next(
            (pa["analysis"].get("beta") for pa in position_analyses if "beta" in pa["analysis"]),
            None,
        )
        if beta is not None:
            risk_table.add_row("Beta", f"{beta:.2f}")
        console.print(risk_table)

        # Option Greeks
        if show_greeks and any("delta" in pa["analysis"] for pa in position_analyses):
            greeks_table = Table(title=f"{ticker_upper} Option Greeks")
            greeks_table.add_column("Greek", style="bold")
            greeks_table.add_column("Value", justify="right")

            # Calculate total_delta using position.quantity from position_obj
            total_delta = sum(
                pa["analysis"].get("delta", 0) * pa["position_obj"].quantity * 100
                for pa in position_analyses
                if "delta" in pa["analysis"] and pa["position_obj"].position_type == "option"
            )
            greeks_table.add_row("Delta", f"{total_delta:.2f}")
            console.print(greeks_table)

    except Exception as e:
        console.print(f"[red]Error in position command:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Interactive mode command functions


def position_interactive(state, args: list[str]):
    """Analyzes a specific position for details and risk in interactive mode."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    # Parse arguments
    if not args:
        console.print("[red]Error:[/red] Missing ticker symbol.")
        console.print("Usage: position <TICKER> [--show-legs] [--show-greeks]")
        return

    ticker_upper = args[0].upper()
    show_legs = "--show-legs" in args
    show_greeks = "--show-greeks" in args

    try:
        portfolio = state.portfolio
        # Group positions by ticker
        grouped_positions = group_positions_by_ticker(portfolio.positions)

        # Check if the ticker exists in the portfolio
        if ticker_upper not in grouped_positions:
            console.print(f"[red]Error:[/red] Ticker {ticker_upper} not found in portfolio")
            return

        # Get positions for the ticker
        positions = grouped_positions[ticker_upper]

        # Separate stock and option positions
        stock_positions = [p for p in positions if p.position_type == "stock"]
        option_positions = [p for p in positions if p.position_type == "option"]

        # Display position details
        console.print(f"\n[bold]Position Details for {ticker_upper}[/bold]")

        # Display stock positions
        if stock_positions:
            table = Table(title=f"{ticker_upper} Stock Positions")
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
            console.print(f"[yellow]No stock positions found for {ticker_upper}[/yellow]")

        # Display option positions
        if option_positions:
            if show_legs:
                # Detailed option information
                table = Table(title=f"{ticker_upper} Option Positions")
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
                table = Table(title=f"{ticker_upper} Option Summary")
                table.add_column("# of Options", justify="right")
                table.add_column("Total Value", justify="right")

                table.add_row(
                    str(len(option_positions)),
                    format_currency(sum(p.market_value for p in option_positions)),
                )
            console.print(table)
        else:
            console.print(f"[yellow]No option positions found for {ticker_upper}[/yellow]")

        # Display total position value
        total_value = sum(p.market_value for p in positions)
        console.print(
            f"\n[bold]Total Position Value:[/bold] {format_currency(total_value)}"
        )

        # Display risk analysis
        console.print(f"\n[bold]Risk Analysis for {ticker_upper}[/bold]")
        position_analyses = []
        for position in positions:  # Iterate through positions for the current ticker
            try:
                # analyze_position uses ticker_service internally
                analysis = analyze_position(position)
                # Store analysis along with the position itself to access position.quantity later for delta
                position_analyses.append({"analysis": analysis, "position_obj": position})
            except Exception as e:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not analyze {position.ticker}: {e!s}"
                )

        # Risk Metrics Table
        risk_table = Table(title=f"{ticker_upper} Risk Metrics")
        risk_table.add_column("Metric", style="bold")
        risk_table.add_column("Value", justify="right")

        total_exposure = sum(pa["analysis"].get("exposure", 0) for pa in position_analyses)
        total_beta_adjusted = sum(
            pa["analysis"].get("beta_adjusted_exposure", 0) for pa in position_analyses
        )

        risk_table.add_row("Market Exposure", format_currency(total_exposure))
        risk_table.add_row("Beta-Adjusted Exposure", format_currency(total_beta_adjusted))

        beta = next(
            (pa["analysis"].get("beta") for pa in position_analyses if "beta" in pa["analysis"]),
            None,
        )
        if beta is not None:
            risk_table.add_row("Beta", f"{beta:.2f}")
        console.print(risk_table)

        # Option Greeks
        if show_greeks and any("delta" in pa["analysis"] for pa in position_analyses):
            greeks_table = Table(title=f"{ticker_upper} Option Greeks")
            greeks_table.add_column("Greek", style="bold")
            greeks_table.add_column("Value", justify="right")

            # Calculate total_delta using position.quantity from position_obj
            total_delta = sum(
                pa["analysis"].get("delta", 0) * pa["position_obj"].quantity * 100
                for pa in position_analyses
                if "delta" in pa["analysis"] and pa["position_obj"].position_type == "option"
            )
            greeks_table.add_row("Delta", f"{total_delta:.2f}")
            console.print(greeks_table)

    except Exception as e:
        console.print(f"[red]Error analyzing position in interactive mode:[/red] {e!s}")
