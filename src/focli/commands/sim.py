"""
Portfolio simulator command using the new simulator_v2 module.

This command simulates portfolio performance under different market scenarios
using the improved simulator_v2 implementation.
"""

import os

import numpy as np
import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from src.folio.portfolio import process_portfolio_data
from src.folio.simulator_v2 import simulate_portfolio

app = typer.Typer(
    help="Simulate portfolio performance under different market scenarios"
)
console = Console()


@app.command()
def main(
    file_path: str = typer.Argument(..., help="Path to the portfolio CSV file"),
    min_spy_change: float = typer.Option(
        -0.2, help="Minimum SPY change to simulate (as a decimal)"
    ),
    max_spy_change: float = typer.Option(
        0.2, help="Maximum SPY change to simulate (as a decimal)"
    ),
    steps: int = typer.Option(
        21, help="Number of steps between min and max SPY change"
    ),
    ticker: str | None = typer.Option(
        None, help="Focus on a specific ticker (optional)"
    ),
    detailed: bool = typer.Option(False, help="Show detailed position-level results"),
):
    """
    Simulate portfolio performance under different market scenarios.

    This command uses the improved simulator_v2 implementation for more accurate
    calculations, especially for option positions.
    """
    # Validate file path
    if not os.path.exists(file_path):
        error = FileNotFoundError(f"File not found: {file_path}")
        console.print(f"[bold red]Error:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    # Load portfolio data
    try:
        df = pd.read_csv(file_path)
        portfolio_groups, portfolio_summary, _ = process_portfolio_data(df)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load portfolio: {e!s}")
        raise typer.Exit(code=1) from e

    # Filter portfolio groups if ticker is specified
    if ticker:
        portfolio_groups = [
            g for g in portfolio_groups if g.ticker.upper() == ticker.upper()
        ]
        if not portfolio_groups:
            error = ValueError(f"Ticker {ticker} not found in portfolio")
            console.print(f"[bold red]Error:[/bold red] {error}")
            raise typer.Exit(code=1) from error

    # Generate SPY changes
    spy_changes = list(
        pd.Series(np.linspace(min_spy_change, max_spy_change, steps)).round(3)
    )

    # Run simulation
    simulation_result = simulate_portfolio(
        portfolio_groups=portfolio_groups,
        spy_changes=spy_changes,
        cash_value=portfolio_summary.cash_like_value,
    )

    # Set the original portfolio value to the total portfolio value from the summary
    original_portfolio_value = portfolio_summary.portfolio_estimate_value
    simulation_result["original_portfolio_value"] = original_portfolio_value

    # Recalculate the P&L % of Orig correctly
    portfolio_pnls = simulation_result["portfolio_pnls"]
    simulation_result["portfolio_pnl_vs_original_percents"] = [
        (pnl / original_portfolio_value) * 100 if original_portfolio_value else 0
        for pnl in portfolio_pnls
    ]

    # Display results
    display_simulation_results(simulation_result, detailed)


def display_simulation_results(simulation_result, detailed=False):
    """Display simulation results in a formatted table."""
    # Create portfolio-level table
    table = Table(title="Portfolio Simulation Results")

    # Add columns
    table.add_column("SPY Change", style="cyan")
    table.add_column("Portfolio Value", style="green")
    table.add_column("P&L", style="yellow")
    table.add_column("P&L %", style="magenta")
    table.add_column("P&L % of Orig", style="blue")

    # Add rows
    for i, spy_change in enumerate(simulation_result["spy_changes"]):
        spy_change_str = f"{spy_change * 100:+.1f}%"
        portfolio_value = simulation_result["portfolio_values"][i]
        portfolio_pnl = simulation_result["portfolio_pnls"][i]
        portfolio_pnl_percent = simulation_result["portfolio_pnl_percents"][i]
        portfolio_pnl_vs_original_percent = simulation_result[
            "portfolio_pnl_vs_original_percents"
        ][i]

        # Format values
        portfolio_value_str = f"${portfolio_value:,.2f}"
        portfolio_pnl_str = f"${portfolio_pnl:+,.2f}" if portfolio_pnl else "$0.00"
        portfolio_pnl_percent_str = (
            f"{portfolio_pnl_percent:+.2f}%" if portfolio_pnl_percent else "0.00%"
        )
        portfolio_pnl_vs_original_percent_str = (
            f"{portfolio_pnl_vs_original_percent:+.2f}%"
            if portfolio_pnl_vs_original_percent
            else "0.00%"
        )

        # Add row with color based on P&L
        pnl_style = "green" if portfolio_pnl >= 0 else "red"
        table.add_row(
            spy_change_str,
            portfolio_value_str,
            f"[{pnl_style}]{portfolio_pnl_str}[/{pnl_style}]",
            f"[{pnl_style}]{portfolio_pnl_percent_str}[/{pnl_style}]",
            f"[{pnl_style}]{portfolio_pnl_vs_original_percent_str}[/{pnl_style}]",
        )

    # Display the table
    console.print(table)

    # Display portfolio values
    current_value = simulation_result.get("current_portfolio_value", 0)
    original_value = simulation_result.get("original_portfolio_value", 0)
    console.print(f"\nCurrent Portfolio Value (0% baseline): ${current_value:,.2f}")
    console.print(f"Original Portfolio Value: ${original_value:,.2f}\n")

    # Display detailed position results if requested
    if detailed and simulation_result["position_results"]:
        display_detailed_results(simulation_result)


def display_detailed_results(simulation_result):
    """Display detailed position-level results."""
    # Get the middle SPY change (closest to 0)
    spy_changes = simulation_result["spy_changes"]
    middle_index = len(spy_changes) // 2

    # Display position-level results for each ticker
    for ticker, results in simulation_result["position_results"].items():
        # Create a table for this ticker
        table = Table(title=f"{ticker} Simulation Results")

        # Add columns
        table.add_column("SPY Change", style="cyan")
        table.add_column("New Price", style="blue")
        table.add_column("Original Value", style="green")
        table.add_column("New Value", style="green")
        table.add_column("P&L", style="yellow")
        table.add_column("P&L %", style="magenta")

        # Add rows
        for i, result in enumerate(results):
            spy_change = spy_changes[i]
            spy_change_str = f"{spy_change * 100:+.1f}%"
            new_price = result["new_price"]
            original_value = result["original_value"]
            new_value = result["new_value"]
            pnl = result["pnl"]
            pnl_percent = result["pnl_percent"]

            # Format values
            new_price_str = f"${new_price:.2f}"
            original_value_str = f"${original_value:,.2f}"
            new_value_str = f"${new_value:,.2f}"
            pnl_str = f"${pnl:+,.2f}" if pnl else "$0.00"
            pnl_percent_str = f"{pnl_percent:+.2f}%" if pnl_percent else "0.00%"

            # Add row with color based on P&L
            pnl_style = "green" if pnl >= 0 else "red"
            table.add_row(
                spy_change_str,
                new_price_str,
                original_value_str,
                new_value_str,
                f"[{pnl_style}]{pnl_str}[/{pnl_style}]",
                f"[{pnl_style}]{pnl_percent_str}[/{pnl_style}]",
            )

        # Display the table
        console.print(table)
        console.print("")

        # Display position details for the middle SPY change
        middle_result = results[middle_index]
        if middle_result.get("positions"):
            display_position_details(
                middle_result["positions"], spy_changes[middle_index]
            )


def display_position_details(positions, spy_change):
    """Display details for individual positions."""
    spy_change_str = f"{spy_change * 100:+.1f}%"
    table = Table(title=f"Position Details (SPY Change: {spy_change_str})")

    # Add columns
    table.add_column("Type", style="cyan")
    table.add_column("Details", style="blue")
    table.add_column("Original Value", style="green")
    table.add_column("New Value", style="green")
    table.add_column("P&L", style="yellow")
    table.add_column("P&L %", style="magenta")

    # Add rows for each position
    for position in positions:
        # Get position type and details
        position_type = position["position_type"]

        if position_type == "stock":
            details = f"Stock: {position['ticker']}"
        elif position_type == "option":
            option_type = position["option_type"]
            strike = position["strike"]
            expiry = position["expiry"]
            details = f"{option_type} {strike} {expiry}"
        else:
            details = "Unknown"

        # Get values
        original_value = position["original_value"]
        new_value = position["new_value"]
        pnl = position["pnl"]
        pnl_percent = position["pnl_percent"]

        # Format values
        original_value_str = f"${original_value:,.2f}"
        new_value_str = f"${new_value:,.2f}"
        pnl_str = f"${pnl:+,.2f}" if pnl else "$0.00"
        pnl_percent_str = f"{pnl_percent:+.2f}%" if pnl_percent else "0.00%"

        # Add row with color based on P&L
        pnl_style = "green" if pnl >= 0 else "red"
        table.add_row(
            position_type.capitalize(),
            details,
            original_value_str,
            new_value_str,
            f"[{pnl_style}]{pnl_str}[/{pnl_style}]",
            f"[{pnl_style}]{pnl_percent_str}[/{pnl_style}]",
        )

    # Display the table
    console.print(table)
    console.print("")


if __name__ == "__main__":
    app()
