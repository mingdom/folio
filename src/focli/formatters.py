"""
Output formatting utilities for the Folio CLI.

This module provides functions for formatting CLI output using Rich.
"""

from rich.box import ROUNDED
from rich.console import Console
from rich.table import Table

from src.folio.formatting import format_currency


def display_simulation_results(results, detailed=False, focus_tickers=None, console=None):
    """Display simulation results using Rich.

    Args:
        results: Simulation results from simulate_portfolio_with_spy_changes
        detailed: Whether to show detailed position analysis
        focus_tickers: List of tickers to focus on
        console: Rich console for output
    """
    if console is None:
        console = Console()

    # Get the current value (at 0% SPY change)
    current_value = results["current_value"]

    # Get min and max values
    min_value = min(results["portfolio_values"])
    max_value = max(results["portfolio_values"])
    min_index = results["portfolio_values"].index(min_value)
    max_index = results["portfolio_values"].index(max_value)
    min_spy_change = results["spy_changes"][min_index] * 100  # Convert to percentage
    max_spy_change = results["spy_changes"][max_index] * 100  # Convert to percentage

    # Create a summary table
    console.print("\n[bold cyan]Portfolio Simulation Results[/bold cyan]")

    summary_table = Table(title="Portfolio Summary", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_column("SPY Change", style="yellow")

    summary_table.add_row("Current Value", f"${current_value:,.2f}", "0.0%")
    summary_table.add_row("Minimum Value", f"${min_value:,.2f}", f"{min_spy_change:.1f}%")
    summary_table.add_row("Maximum Value", f"${max_value:,.2f}", f"{max_spy_change:.1f}%")

    console.print(summary_table)

    # Create a detailed table with all values
    value_table = Table(title="Portfolio Values at Different SPY Changes", box=ROUNDED)
    value_table.add_column("SPY Change", style="yellow")
    value_table.add_column("Portfolio Value", style="green")
    value_table.add_column("Change", style="cyan")
    value_table.add_column("% Change", style="magenta")

    for i, spy_change in enumerate(results["spy_changes"]):
        portfolio_value = results["portfolio_values"][i]
        value_change = portfolio_value - current_value
        pct_change = (value_change / current_value) * 100 if current_value != 0 else 0

        # Format the change with color based on positive/negative
        change_str = f"${value_change:+,.2f}"
        pct_change_str = f"{pct_change:+.2f}%"

        value_table.add_row(
            f"{spy_change * 100:.1f}%",
            f"${portfolio_value:,.2f}",
            change_str,
            pct_change_str,
        )

    console.print(value_table)

    # If detailed is True, show position-level analysis
    if detailed:
        display_position_analysis(results, focus_tickers, console)

def display_position_analysis(results, focus_tickers=None, console=None):
    """Display position-level analysis.

    Args:
        results: Simulation results from simulate_portfolio_with_spy_changes
        focus_tickers: List of tickers to focus on
        console: Rich console for output
    """
    if console is None:
        console = Console()

    # Get position details
    position_details = results.get("position_details", {})
    position_changes = results.get("position_changes", {})

    # Filter positions if focus_tickers is provided
    if focus_tickers:
        filtered_details = {}
        filtered_changes = {}
        for ticker in focus_tickers:
            if ticker in position_details:
                filtered_details[ticker] = position_details[ticker]
            if ticker in position_changes:
                filtered_changes[ticker] = position_changes[ticker]
        position_details = filtered_details
        position_changes = filtered_changes

    # Display position details
    console.print("\n[bold cyan]Position Analysis[/bold cyan]")

    for ticker, details in position_details.items():
        # Create a panel for each position
        position_table = Table(title=f"{ticker} Details", box=ROUNDED)
        position_table.add_column("Metric", style="cyan")
        position_table.add_column("Value", style="green")

        # Add basic position details
        position_table.add_row("Beta", f"{details.get('beta', 0):.2f}")
        position_table.add_row("Current Value", format_currency(details.get('current_value', 0)))
        position_table.add_row("Stock Value", format_currency(details.get('stock_value', 0)))
        position_table.add_row("Option Value", format_currency(details.get('option_value', 0)))

        # Add stock details if available
        if details.get('has_stock'):
            position_table.add_row("Stock Quantity", f"{details.get('stock_quantity', 0)}")
            position_table.add_row("Stock Price", format_currency(details.get('stock_price', 0)))

        # Add option details if available
        if details.get('has_options'):
            position_table.add_row("Option Count", f"{details.get('option_count', 0)}")

        console.print(position_table)

        # If we have change data, show it
        if ticker in position_changes:
            changes = position_changes[ticker]

            # Create a table for position changes
            changes_table = Table(title=f"{ticker} Changes with SPY", box=ROUNDED)
            changes_table.add_column("SPY Change", style="yellow")
            changes_table.add_column("Position Value", style="green")
            changes_table.add_column("Change", style="cyan")
            changes_table.add_column("% Change", style="magenta")

            for i, spy_change in enumerate(results["spy_changes"]):
                if i < len(changes["values"]):
                    value = changes["values"][i]
                    change = changes["changes"][i]
                    pct_change = changes["pct_changes"][i]

                    changes_table.add_row(
                        f"{spy_change * 100:.1f}%",
                        format_currency(value),
                        f"{format_currency(change, include_sign=True)}",
                        f"{pct_change:+.2f}%",
                    )

            console.print(changes_table)

def display_position_details(group, detailed=True, console=None):
    """Display detailed information about a position group.

    Args:
        group: PortfolioGroup to display
        detailed: Whether to show detailed option information
        console: Rich console for output
    """
    if console is None:
        console = Console()

    ticker = group.ticker
    console.print(f"\n[bold cyan]Position Details: {ticker}[/bold cyan]")

    # Create a summary table
    summary_table = Table(title=f"{ticker} Summary", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    # Add basic position details
    summary_table.add_row("Beta", f"{group.beta:.2f}")
    summary_table.add_row("Net Exposure", format_currency(group.net_exposure))
    summary_table.add_row("Beta-Adjusted Exposure", format_currency(group.beta_adjusted_exposure))

    # Add stock details if available
    if group.stock_position:
        stock = group.stock_position
        summary_table.add_row("Stock Quantity", f"{stock.quantity}")
        summary_table.add_row("Stock Price", format_currency(stock.price))
        summary_table.add_row("Stock Market Value", format_currency(stock.market_value))

    # Add option summary if available
    if group.option_positions:
        summary_table.add_row("Option Count", f"{len(group.option_positions)}")
        summary_table.add_row("Call Options", f"{group.call_count}")
        summary_table.add_row("Put Options", f"{group.put_count}")
        summary_table.add_row("Total Delta Exposure", format_currency(group.total_delta_exposure))

    console.print(summary_table)

    # If detailed and we have options, show option details
    if detailed and group.option_positions:
        options_table = Table(title=f"{ticker} Option Positions", box=ROUNDED)
        options_table.add_column("Type", style="cyan")
        options_table.add_column("Strike", style="green", justify="right")
        options_table.add_column("Expiry", style="yellow")
        options_table.add_column("Quantity", style="green", justify="right")
        options_table.add_column("Delta", style="magenta", justify="right")
        options_table.add_column("Value", style="green", justify="right")

        for option in group.option_positions:
            options_table.add_row(
                option.option_type,
                format_currency(option.strike),
                option.expiry,
                f"{option.quantity}",
                f"{option.delta:.2f}",
                format_currency(option.market_value),
            )

        console.print(options_table)

def display_portfolio_summary(summary, console=None):
    """Display a summary of the portfolio.

    Args:
        summary: PortfolioSummary object
        console: Rich console for output
    """
    if console is None:
        console = Console()

    console.print("\n[bold cyan]Portfolio Summary[/bold cyan]")

    # Create a summary table
    summary_table = Table(title="Portfolio Overview", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    # Add portfolio metrics
    summary_table.add_row("Total Value", format_currency(summary.portfolio_estimate_value))
    summary_table.add_row("Stock Value", format_currency(summary.stock_value))
    summary_table.add_row("Option Value", format_currency(summary.option_value))
    summary_table.add_row("Cash Value", format_currency(summary.cash_like_value))
    summary_table.add_row("Portfolio Beta", f"{summary.portfolio_beta:.2f}")
    summary_table.add_row("Net Market Exposure", format_currency(summary.net_market_exposure))

    console.print(summary_table)

    # Create an exposure table
    exposure_table = Table(title="Exposure Breakdown", box=ROUNDED)
    exposure_table.add_column("Category", style="cyan")
    exposure_table.add_column("Value", style="green")
    exposure_table.add_column("% of Portfolio", style="magenta")

    # Add exposure metrics
    total_value = summary.portfolio_estimate_value
    if total_value > 0:
        exposure_table.add_row(
            "Long Exposure",
            format_currency(summary.long_exposure.total_value),
            f"{summary.long_exposure.total_value / total_value * 100:.1f}%"
        )
        exposure_table.add_row(
            "Short Exposure",
            format_currency(summary.short_exposure.total_value),
            f"{summary.short_exposure.total_value / total_value * 100:.1f}%"
        )
        exposure_table.add_row(
            "Options Exposure",
            format_currency(summary.options_exposure.total_value),
            f"{summary.options_exposure.total_value / total_value * 100:.1f}%"
        )
        exposure_table.add_row(
            "Cash",
            format_currency(summary.cash_like_value),
            f"{summary.cash_percentage * 100:.1f}%"
        )

    console.print(exposure_table)
