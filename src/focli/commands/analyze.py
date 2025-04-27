"""
Portfolio analysis command for the Folio CLI.

This command provides detailed analysis of portfolio performance and position contributions
under different market scenarios.
"""

import os

import numpy as np
import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from src.folio.portfolio import process_portfolio_data
from src.folio.position_analysis import (
    analyze_position_contributions,
    find_key_spy_levels,
)
from src.folio.simulator_v2 import simulate_portfolio

app = typer.Typer(help="Analyze portfolio performance and position contributions")
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
    focus_spy: float | None = typer.Option(
        None, help="Focus on a specific SPY change level (as a decimal)"
    ),
    top_n: int = typer.Option(5, help="Number of top contributors to display"),
):
    """
    Analyze portfolio performance and position contributions under different market scenarios.

    This command helps identify which positions contribute most to portfolio movements
    at different SPY change levels, with a focus on understanding counterintuitive behavior
    like portfolio value decreasing when SPY increases.
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

    # Generate SPY changes
    spy_changes = list(
        pd.Series(np.linspace(min_spy_change, max_spy_change, steps)).round(3)
    )

    # Run simulation
    console.print("Running portfolio simulation...")
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

    # Analyze position contributions
    console.print("Analyzing position contributions...")
    contribution_analysis = analyze_position_contributions(simulation_result)
    key_levels = find_key_spy_levels(simulation_result)

    # Display key insights
    display_key_insights(simulation_result, key_levels)

    # Display position contributions
    if focus_spy is not None:
        # Find the closest SPY change level
        closest_spy = min(spy_changes, key=lambda x: abs(x - focus_spy))
        display_contributions_at_level(contribution_analysis, closest_spy, top_n)
    else:
        # Display contributions at key levels
        display_contributions_at_key_levels(contribution_analysis, key_levels, top_n)

    # Display problematic positions in rising markets
    display_problematic_positions(contribution_analysis)


def display_key_insights(simulation_result, key_levels):
    """Display key insights about portfolio behavior."""
    console.print("\n[bold cyan]Key Portfolio Insights[/bold cyan]")

    # Create a table for key insights
    table = Table(title="Portfolio Behavior Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    table.add_column("Details", style="green")

    # Add maximum P&L information
    max_pnl_index = simulation_result["portfolio_pnls"].index(
        max(simulation_result["portfolio_pnls"])
    )
    max_pnl = simulation_result["portfolio_pnls"][max_pnl_index]
    max_pnl_spy = simulation_result["spy_changes"][max_pnl_index]
    table.add_row(
        "Maximum P&L",
        f"${max_pnl:+,.2f}",
        f"At SPY change of {max_pnl_spy * 100:+.1f}%",
    )

    # Add minimum P&L information
    min_pnl_index = simulation_result["portfolio_pnls"].index(
        min(simulation_result["portfolio_pnls"])
    )
    min_pnl = simulation_result["portfolio_pnls"][min_pnl_index]
    min_pnl_spy = simulation_result["spy_changes"][min_pnl_index]
    table.add_row(
        "Minimum P&L",
        f"${min_pnl:+,.2f}",
        f"At SPY change of {min_pnl_spy * 100:+.1f}%",
    )

    # Add inflection points
    if key_levels["inflection_points"]:
        inflection_points_str = ", ".join(
            [f"{spy * 100:+.1f}%" for spy, _ in key_levels["inflection_points"]]
        )
        table.add_row(
            "Inflection Points",
            inflection_points_str,
            "SPY levels where P&L changes sign",
        )

    # Add declining in rising market information
    if key_levels["declining_in_rising_market"] is not None:
        declining_spy = key_levels["declining_in_rising_market"]
        table.add_row(
            "Declining in Rising Market",
            f"{declining_spy * 100:+.1f}%",
            "SPY level where portfolio starts declining despite rising market",
        )

    console.print(table)


def display_contributions_at_level(contribution_analysis, spy_level, top_n):
    """Display position contributions at a specific SPY change level."""
    console.print(
        f"\n[bold cyan]Position Contributions at {spy_level * 100:+.1f}% SPY Change[/bold cyan]"
    )

    # Get contributions at this level
    contributions = contribution_analysis["contributions"][spy_level]

    # Sort positions by absolute contribution
    sorted_contributions = sorted(
        contributions.items(), key=lambda x: abs(x[1]), reverse=True
    )

    # Create a table for top contributors
    table = Table(title=f"Top {top_n} Contributors by Absolute Value")
    table.add_column("Position", style="cyan")
    table.add_column("Contribution", style="yellow")
    table.add_column("% of Total P&L", style="green")

    # Get total P&L at this level
    total_pnl = sum(contributions.values())

    # Add rows for top contributors
    for ticker, pnl in sorted_contributions[:top_n]:
        # Calculate percentage of total P&L
        if abs(total_pnl) < 0.01:
            percent = 0.0
        else:
            percent = (pnl / abs(total_pnl)) * 100

        # Format values
        pnl_str = f"${pnl:+,.2f}"
        percent_str = f"{percent:+.2f}%"

        # Add row with color based on P&L
        pnl_style = "green" if pnl >= 0 else "red"
        table.add_row(
            ticker,
            f"[{pnl_style}]{pnl_str}[/{pnl_style}]",
            f"[{pnl_style}]{percent_str}[/{pnl_style}]",
        )

    console.print(table)


def display_contributions_at_key_levels(contribution_analysis, key_levels, top_n):
    """Display position contributions at key SPY change levels."""
    # Display contributions at maximum P&L
    display_contributions_at_level(
        contribution_analysis, key_levels["max_pnl_spy_change"], top_n
    )

    # Display contributions at minimum P&L
    display_contributions_at_level(
        contribution_analysis, key_levels["min_pnl_spy_change"], top_n
    )

    # Display contributions at declining in rising market point
    if key_levels["declining_in_rising_market"] is not None:
        display_contributions_at_level(
            contribution_analysis, key_levels["declining_in_rising_market"], top_n
        )


def display_problematic_positions(contribution_analysis):
    """Display positions that contribute to negative performance in rising markets."""
    problematic_positions = contribution_analysis["problematic_positions"]

    if not problematic_positions:
        return

    console.print(
        "\n[bold red]Positions Contributing to Negative Performance in Rising Markets[/bold red]"
    )

    # Create a table for problematic positions
    table = Table(title="Positions with Negative Contributions in Rising Markets")
    table.add_column("SPY Change", style="cyan")
    table.add_column("Position", style="yellow")
    table.add_column("Negative Contribution", style="red")

    # Add rows for each SPY level with problematic positions
    for spy_change, positions in sorted(problematic_positions.items()):
        if not positions:
            continue

        # Add the top 3 negative contributors
        for i, (ticker, pnl) in enumerate(positions[:3]):
            if i == 0:
                spy_change_str = f"{spy_change * 100:+.1f}%"
            else:
                spy_change_str = ""

            pnl_str = f"${pnl:,.2f}"
            table.add_row(spy_change_str, ticker, pnl_str)

    console.print(table)


if __name__ == "__main__":
    app()
