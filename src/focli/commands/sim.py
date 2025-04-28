"""
Portfolio simulator command using the new simulator_v2 module.

This command simulates portfolio performance under different market scenarios
using the improved simulator_v2 implementation.
"""

import os
from typing import Any

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
    # Get current SPY price
    try:
        import yfinance as yf

        spy_data = yf.Ticker("SPY")
        current_spy_price = spy_data.history(period="1d")["Close"].iloc[-1]
    except Exception:
        # If there's an error getting the price, use a default value
        current_spy_price = 500.0  # Default SPY price
        console.print(
            "[yellow]Warning: Could not get current SPY price. Using default value.[/yellow]"
        )

    # Create portfolio-level table
    table = Table(title="Portfolio Simulation Results")

    # Add columns
    table.add_column("SPY Change", style="cyan")
    table.add_column("SPY Price", style="blue")
    table.add_column("Portfolio Value", style="green")
    table.add_column("P&L", style="yellow")
    table.add_column("P&L %", style="magenta")
    table.add_column("P&L % of Orig", style="blue")

    # Add rows
    for i, spy_change in enumerate(simulation_result["spy_changes"]):
        spy_change_str = f"{spy_change * 100:+.1f}%"

        # Calculate SPY price at this change level
        spy_price = current_spy_price * (1 + spy_change)
        spy_price_str = f"${spy_price:.2f}"

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
            spy_price_str,
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
    console.print(f"\nCurrent SPY Price: ${current_spy_price:.2f}")
    console.print(f"Current Portfolio Value (0% baseline): ${current_value:,.2f}")
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


def analyze_spy_correlation(simulation_result, console):
    """
    Analyze which positions have negative correlation with SPY.

    This function identifies positions that perform worse when SPY increases,
    which helps explain why a portfolio might have poor returns in up markets.

    Args:
        simulation_result: Simulation results dictionary
        console: Rich console for output
    """
    # Get the SPY changes and find the positive change indices
    spy_changes = simulation_result["spy_changes"]
    positive_indices = [i for i, change in enumerate(spy_changes) if change > 0]

    if not positive_indices:
        console.print(
            "[yellow]No positive SPY changes in simulation to analyze.[/yellow]"
        )
        return

    # Find the position results for each ticker
    position_results = simulation_result["position_results"]

    # Calculate correlation metrics for each position
    correlation_data = []

    for ticker, results in position_results.items():
        # Skip if no results
        if not results:
            continue

        # Get the position PNLs at each SPY change
        position_pnls = [result["pnl"] for result in results]

        # Calculate average P&L for positive SPY changes
        positive_pnls = [position_pnls[i] for i in positive_indices]
        avg_positive_pnl = (
            sum(positive_pnls) / len(positive_pnls) if positive_pnls else 0
        )

        # Get the original value (same for all results)
        original_value = results[0]["original_value"] if results else 0

        # Calculate correlation coefficient between position values and SPY changes
        # (simplified approach - just check if position tends to lose money when SPY goes up)
        correlation_score = avg_positive_pnl

        # Calculate impact on portfolio (weighted by position size)
        portfolio_impact = correlation_score

        # Store the data
        correlation_data.append(
            {
                "ticker": ticker,
                "original_value": original_value,
                "correlation_score": correlation_score,
                "portfolio_impact": portfolio_impact,
                "avg_positive_pnl": avg_positive_pnl,
            }
        )

    # Sort by portfolio impact (most negative first)
    correlation_data.sort(key=lambda x: x["portfolio_impact"])

    # Create a table for the results
    table = Table(title="Position Performance When SPY Increases (Avg of +2% to +20%)")

    # Add columns with clearer headers
    table.add_column("Ticker", style="cyan")
    table.add_column("Current Position Size", style="green")
    table.add_column("Avg P&L When SPY Up", style="yellow")
    table.add_column("Return on Position", style="magenta")
    table.add_column("Portfolio Weight", style="blue")

    # Add rows
    total_portfolio_value = sum(
        abs(item["original_value"]) for item in correlation_data
    )

    for item in correlation_data:
        ticker = item["ticker"]
        original_value = item["original_value"]
        avg_positive_pnl = item["avg_positive_pnl"]

        # Calculate percentage return on position (handle negative position values properly)
        abs_original = abs(original_value)
        if abs_original > 0:
            # If position value is negative (short), flip the sign of the percentage
            sign_multiplier = -1 if original_value < 0 else 1
            pnl_percent = (avg_positive_pnl / abs_original) * 100 * sign_multiplier
        else:
            pnl_percent = 0

        # Calculate percentage of portfolio (always use absolute value for portfolio weight)
        portfolio_percent = (
            (abs_original / total_portfolio_value) * 100 if total_portfolio_value else 0
        )

        # Format values
        original_value_str = f"${abs_original:,.2f}"
        if original_value < 0:
            original_value_str = f"${abs_original:,.2f} (Short)"

        avg_positive_pnl_str = (
            f"${avg_positive_pnl:+,.2f}" if avg_positive_pnl else "$0.00"
        )

        # Cap percentage display at ±100% for readability
        display_pnl_percent = min(max(pnl_percent, -100), 100)
        pnl_percent_str = f"{display_pnl_percent:+.2f}%"
        if abs(pnl_percent) > 100:
            pnl_percent_str += f" (actual: {pnl_percent:+.2f}%)"

        portfolio_weight_str = f"{portfolio_percent:.2f}% of portfolio"

        # Add row with color based on P&L
        pnl_style = "green" if avg_positive_pnl >= 0 else "red"
        table.add_row(
            ticker,
            original_value_str,
            f"[{pnl_style}]{avg_positive_pnl_str}[/{pnl_style}]",
            f"[{pnl_style}]{pnl_percent_str}[/{pnl_style}]",
            portfolio_weight_str,
        )

    # Display the table with clearer explanations
    console.print("\n[bold]Analysis: How Positions Perform When SPY Increases[/bold]")
    console.print(
        "[italic]This analysis shows the average performance of each position across all positive SPY changes (+2% to +20%)[/italic]"
    )
    console.print(
        "[italic]Positions are ranked from worst to best performance when SPY increases[/italic]"
    )
    console.print(table)

    # Show the SPY range used for this analysis
    positive_spy_changes = [
        f"+{change * 100:.1f}%"
        for change in simulation_result["spy_changes"]
        if change > 0
    ]
    console.print(f"\n[bold]SPY Changes Used:[/bold] {', '.join(positive_spy_changes)}")

    # Provide analysis summary
    negative_performers = [
        item for item in correlation_data if item["avg_positive_pnl"] < 0
    ]
    if negative_performers:
        total_negative_impact = sum(
            item["avg_positive_pnl"] for item in negative_performers
        )
        console.print(
            f"\n[bold]Key Finding:[/bold] {len(negative_performers)} positions consistently lose money when SPY increases."
        )
        console.print(
            f"Total negative impact across all up-market scenarios: [red]${total_negative_impact:,.2f}[/red]"
        )

        # Recommend positions to investigate
        console.print("\n[bold]Positions to investigate:[/bold]")
        for item in negative_performers[:3]:  # Top 3 worst performers
            console.print(
                f"- {item['ticker']}: [red]${item['avg_positive_pnl']:,.2f}[/red] average loss when SPY increases"
            )
            console.print(
                f"  Try: [cyan]position {item['ticker']} simulate[/cyan] for detailed analysis"
            )

        # Add explanation about what this means
        console.print("\n[bold]What This Means:[/bold]")
        console.print(
            "These positions are negatively correlated with SPY - they tend to lose money when the market goes up."
        )
        console.print(
            "This explains why your portfolio's overall performance decreases when SPY increases beyond certain levels."
        )
    else:
        console.print(
            "\n[bold green]Good news![/bold green] No positions show consistent losses when SPY increases."
        )
        console.print("Your portfolio appears to be well-positioned for up markets.")


def shell_command(args: list[str], state: dict[str, Any], console: Console):
    """
    Execute the sim command in the shell context.

    This function is called when the user types 'sim' in the Folio CLI shell.
    It uses the portfolio already loaded in the shell's state.

    Args:
        args: Command arguments
        state: Application state containing the loaded portfolio
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio_groups") or not state.get("portfolio_summary"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Parse arguments
    min_spy_change = -0.2
    max_spy_change = 0.2
    steps = 21
    ticker = None
    detailed = False
    analyze_correlation = False

    # Process arguments
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--min-spy-change" and i + 1 < len(args):
            try:
                min_spy_change = float(args[i + 1])
                i += 2
            except ValueError:
                console.print(
                    f"[bold red]Error:[/bold red] Invalid value for --min-spy-change: {args[i + 1]}"
                )
                return
        elif arg == "--max-spy-change" and i + 1 < len(args):
            try:
                max_spy_change = float(args[i + 1])
                i += 2
            except ValueError:
                console.print(
                    f"[bold red]Error:[/bold red] Invalid value for --max-spy-change: {args[i + 1]}"
                )
                return
        elif arg == "--steps" and i + 1 < len(args):
            try:
                steps = int(args[i + 1])
                i += 2
            except ValueError:
                console.print(
                    f"[bold red]Error:[/bold red] Invalid value for --steps: {args[i + 1]}"
                )
                return
        elif arg == "--ticker" and i + 1 < len(args):
            ticker = args[i + 1]
            i += 2
        elif arg == "--detailed":
            detailed = True
            i += 1
        elif arg in {"--analyze-correlation", "--analyze"}:
            analyze_correlation = True
            i += 1
        else:
            console.print(f"[bold red]Error:[/bold red] Unknown argument: {arg}")
            console.print(
                "Usage: sim [--min-spy-change VALUE] [--max-spy-change VALUE] [--steps VALUE] [--ticker TICKER] [--detailed] [--analyze-correlation]"
            )
            return

    # Get portfolio groups and summary from state
    portfolio_groups = state["portfolio_groups"]
    portfolio_summary = state["portfolio_summary"]

    # Filter portfolio groups if ticker is specified
    if ticker:
        portfolio_groups = [
            g for g in portfolio_groups if g.ticker.upper() == ticker.upper()
        ]
        if not portfolio_groups:
            console.print(
                f"[bold red]Error:[/bold red] Ticker {ticker} not found in portfolio."
            )
            return

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

    # Display results
    display_simulation_results(simulation_result, detailed)

    # If analyze_correlation flag is set, run the correlation analysis
    if analyze_correlation:
        analyze_spy_correlation(simulation_result, console)


if __name__ == "__main__":
    app()
