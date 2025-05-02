"""
Output formatting utilities for the Folio CLI.

This module provides functions for formatting CLI output using Rich.
"""

from rich.box import ROUNDED
from rich.console import Console
from rich.table import Table

from src.folio.formatting import format_currency


def display_simulation_results(
    results, detailed=False, focus_tickers=None, console=None
):
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
    summary_table.add_row(
        "Minimum Value", f"${min_value:,.2f}", f"{min_spy_change:.1f}%"
    )
    summary_table.add_row(
        "Maximum Value", f"${max_value:,.2f}", f"{max_spy_change:.1f}%"
    )

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
        position_table.add_row(
            "Current Value", format_currency(details.get("current_value", 0))
        )
        position_table.add_row(
            "Stock Value", format_currency(details.get("stock_value", 0))
        )
        position_table.add_row(
            "Option Value", format_currency(details.get("option_value", 0))
        )

        # Add stock details if available
        if details.get("has_stock"):
            position_table.add_row(
                "Stock Quantity", f"{details.get('stock_quantity', 0)}"
            )
            position_table.add_row(
                "Stock Price", format_currency(details.get("stock_price", 0))
            )

        # Add option details if available
        if details.get("has_options"):
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
    # Handle missing beta attribute
    beta_str = "N/A"
    if hasattr(group, "beta") and group.beta is not None:
        beta_str = f"{group.beta:.2f}"
    summary_table.add_row("Beta", beta_str)

    # Handle missing net_exposure attribute
    if hasattr(group, "net_exposure"):
        summary_table.add_row("Net Exposure", format_currency(group.net_exposure))
    else:
        summary_table.add_row("Net Exposure", "$0.00")

    # Handle missing beta_adjusted_exposure attribute
    if hasattr(group, "beta_adjusted_exposure"):
        summary_table.add_row(
            "Beta-Adjusted Exposure", format_currency(group.beta_adjusted_exposure)
        )
    else:
        summary_table.add_row("Beta-Adjusted Exposure", "$0.00")

    # Add stock details if available
    if group.stock_position:
        stock = group.stock_position
        summary_table.add_row("Stock Quantity", f"{stock.quantity}")
        summary_table.add_row("Stock Price", format_currency(stock.price))
        summary_table.add_row("Stock Market Value", format_currency(stock.market_value))

    # Add option summary if available
    if group.option_positions:
        summary_table.add_row("Option Count", f"{len(group.option_positions)}")

        # Handle missing call_count attribute
        call_count = 0
        if hasattr(group, "call_count"):
            call_count = group.call_count
        else:
            # Calculate call_count manually
            for op in group.option_positions:
                if hasattr(op, "option_type") and op.option_type.upper() == "CALL":
                    call_count += 1
        summary_table.add_row("Call Options", f"{call_count}")

        # Handle missing put_count attribute
        put_count = 0
        if hasattr(group, "put_count"):
            put_count = group.put_count
        else:
            # Calculate put_count manually
            for op in group.option_positions:
                if hasattr(op, "option_type") and op.option_type.upper() == "PUT":
                    put_count += 1
        summary_table.add_row("Put Options", f"{put_count}")

        # Handle missing total_delta_exposure attribute
        delta_exposure = 0
        if hasattr(group, "total_delta_exposure"):
            delta_exposure = group.total_delta_exposure
        else:
            # Try to calculate delta exposure manually
            try:
                for op in group.option_positions:
                    if hasattr(op, "delta_exposure"):
                        delta_exposure += op.delta_exposure
                    elif hasattr(op, "market_value"):
                        # Fallback to market value if delta_exposure is not available
                        delta_exposure += op.market_value
            except Exception:
                # If calculation fails, just use 0
                delta_exposure = 0

        summary_table.add_row("Total Delta Exposure", format_currency(delta_exposure))

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
            # Handle missing delta attribute
            delta_str = "N/A"
            if hasattr(option, "delta") and option.delta is not None:
                delta_str = f"{option.delta:.2f}"

            # Handle missing option_type attribute
            option_type = "UNKNOWN"
            if hasattr(option, "option_type") and option.option_type is not None:
                option_type = option.option_type

            # Handle missing strike attribute
            strike_str = "$0.00"
            if hasattr(option, "strike") and option.strike is not None:
                strike_str = format_currency(option.strike)

            # Handle missing expiry attribute
            expiry_str = "UNKNOWN"
            if hasattr(option, "expiry") and option.expiry is not None:
                expiry_str = str(option.expiry)

            # Handle missing quantity attribute
            quantity_str = "0"
            if hasattr(option, "quantity") and option.quantity is not None:
                quantity_str = f"{option.quantity}"

            # Handle missing market_value attribute
            market_value_str = "$0.00"
            if hasattr(option, "market_value") and option.market_value is not None:
                market_value_str = format_currency(option.market_value)

            options_table.add_row(
                option_type,
                strike_str,
                expiry_str,
                quantity_str,
                delta_str,
                market_value_str,
            )

        console.print(options_table)


def display_portfolio_summary(summary, console=None):
    """Display a summary of the portfolio.

    Args:
        summary: PortfolioSummary object (either old or new folib version)
        console: Rich console for output
    """
    if console is None:
        console = Console()

    console.print("\n[bold cyan]Portfolio Summary[/bold cyan]")

    # Create a summary table
    summary_table = Table(title="Portfolio Overview", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    # Check if this is a folib PortfolioSummary or the old summary
    # The folib version has total_value, the old version has portfolio_estimate_value
    is_folib = hasattr(summary, "total_value")

    try:
        # Add portfolio metrics
        if is_folib:
            # New folib PortfolioSummary
            total_value = summary.total_value
            summary_table.add_row("Total Value", format_currency(total_value))
            summary_table.add_row("Stock Value", format_currency(summary.stock_value))
            summary_table.add_row("Option Value", format_currency(summary.option_value))

            # Check if cash_value exists (it should in the new version)
            if hasattr(summary, "cash_value"):
                summary_table.add_row("Cash Value", format_currency(summary.cash_value))

            # Check if unknown_value exists (it should in the new version)
            if hasattr(summary, "unknown_value"):
                summary_table.add_row(
                    "Unknown Value", format_currency(summary.unknown_value)
                )

            # Portfolio beta might be None in folib
            beta_value = 0.0
            if (
                hasattr(summary, "portfolio_beta")
                and summary.portfolio_beta is not None
            ):
                beta_value = summary.portfolio_beta
            summary_table.add_row("Portfolio Beta", f"{beta_value:.2f}")

            # Check if net_market_exposure exists
            if hasattr(summary, "net_market_exposure"):
                summary_table.add_row(
                    "Net Market Exposure", format_currency(summary.net_market_exposure)
                )
        else:
            # Old PortfolioSummary
            total_value = summary.portfolio_estimate_value
            summary_table.add_row("Total Value", format_currency(total_value))
            summary_table.add_row("Stock Value", format_currency(summary.stock_value))
            summary_table.add_row("Option Value", format_currency(summary.option_value))

            # Check if cash_like_value exists
            if hasattr(summary, "cash_like_value"):
                summary_table.add_row(
                    "Cash Value", format_currency(summary.cash_like_value)
                )

            # Check if portfolio_beta exists
            if hasattr(summary, "portfolio_beta"):
                summary_table.add_row("Portfolio Beta", f"{summary.portfolio_beta:.2f}")

            # Check if net_market_exposure exists
            if hasattr(summary, "net_market_exposure"):
                summary_table.add_row(
                    "Net Market Exposure", format_currency(summary.net_market_exposure)
                )

        console.print(summary_table)

        # Create an exposure table
        exposure_table = Table(title="Exposure Breakdown", box=ROUNDED)
        exposure_table.add_column("Category", style="cyan")
        exposure_table.add_column("Value", style="green")
        exposure_table.add_column("% of Portfolio", style="magenta")

        # Add exposure metrics
        if is_folib and total_value > 0:
            # For folib, we don't have exposure breakdowns yet
            # Just show the basic values as percentages of total
            exposure_table.add_row(
                "Stock Value",
                format_currency(summary.stock_value),
                f"{summary.stock_value / total_value * 100:.1f}%",
            )
            exposure_table.add_row(
                "Option Value",
                format_currency(summary.option_value),
                f"{summary.option_value / total_value * 100:.1f}%",
            )

            # Check if cash_value exists
            if hasattr(summary, "cash_value"):
                exposure_table.add_row(
                    "Cash Value",
                    format_currency(summary.cash_value),
                    f"{summary.cash_value / total_value * 100:.1f}%",
                )

            # Check if unknown_value exists
            if hasattr(summary, "unknown_value"):
                exposure_table.add_row(
                    "Unknown Value",
                    format_currency(summary.unknown_value),
                    f"{summary.unknown_value / total_value * 100:.1f}%",
                )
        # Old exposure breakdown
        elif not is_folib and total_value > 0:
            # Check if long_exposure exists
            if hasattr(summary, "long_exposure") and hasattr(
                summary.long_exposure, "total_value"
            ):
                exposure_table.add_row(
                    "Long Exposure",
                    format_currency(summary.long_exposure.total_value),
                    f"{summary.long_exposure.total_value / total_value * 100:.1f}%",
                )

            # Check if short_exposure exists
            if hasattr(summary, "short_exposure") and hasattr(
                summary.short_exposure, "total_value"
            ):
                exposure_table.add_row(
                    "Short Exposure",
                    format_currency(summary.short_exposure.total_value),
                    f"{summary.short_exposure.total_value / total_value * 100:.1f}%",
                )

            # Check if options_exposure exists
            if hasattr(summary, "options_exposure") and hasattr(
                summary.options_exposure, "total_value"
            ):
                exposure_table.add_row(
                    "Options Exposure",
                    format_currency(summary.options_exposure.total_value),
                    f"{summary.options_exposure.total_value / total_value * 100:.1f}%",
                )

            # Check if cash_like_value and cash_percentage exist
            if hasattr(summary, "cash_like_value") and hasattr(
                summary, "cash_percentage"
            ):
                exposure_table.add_row(
                    "Cash",
                    format_currency(summary.cash_like_value),
                    f"{summary.cash_percentage * 100:.1f}%",
                )

        console.print(exposure_table)
    except Exception as e:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Error displaying portfolio summary: {e}"
        )
        console.print(
            "This may be due to differences between the old and new data structures."
        )
        console.print("Please report this issue to the developers.")


def display_position_risk_analysis(group, detailed=False, console=None):
    """Display risk analysis for a position group.

    Args:
        group: PortfolioGroup to analyze
        detailed: Whether to show detailed information
        console: Rich console for output
    """
    if console is None:
        console = Console()

    ticker = group.ticker
    console.print(f"\n[bold cyan]Risk Analysis: {ticker}[/bold cyan]")

    # Create a risk table
    risk_table = Table(title=f"{ticker} Risk Metrics", box=ROUNDED)
    risk_table.add_column("Metric", style="cyan")
    risk_table.add_column("Value", style="green")
    risk_table.add_column("Description", style="yellow")

    # Add risk metrics
    # Handle missing beta attribute
    beta_str = "N/A"
    if hasattr(group, "beta") and group.beta is not None:
        beta_str = f"{group.beta:.2f}"
    risk_table.add_row("Beta", beta_str, "Sensitivity to market movements")

    # Calculate beta-adjusted exposure
    # Handle missing beta_adjusted_exposure attribute
    if hasattr(group, "beta_adjusted_exposure"):
        beta_adjusted = group.beta_adjusted_exposure
        risk_table.add_row(
            "Beta-Adjusted Exposure",
            format_currency(beta_adjusted),
            "Exposure adjusted for market sensitivity",
        )
    else:
        risk_table.add_row(
            "Beta-Adjusted Exposure",
            "$0.00",
            "Exposure adjusted for market sensitivity",
        )

    # Calculate option exposure
    try:
        option_exposure = (
            sum(op.delta_exposure for op in group.option_positions)
            if group.option_positions
            else 0
        )
    except AttributeError:
        # Handle missing delta_exposure attribute
        option_exposure = 0
        if group.option_positions:
            # Try to calculate a simple delta exposure
            for op in group.option_positions:
                if hasattr(op, "market_value"):
                    option_exposure += op.market_value

    risk_table.add_row(
        "Option Delta Exposure",
        format_currency(option_exposure),
        "Exposure from options delta",
    )

    # Calculate stock exposure
    stock_exposure = 0
    if group.stock_position:
        if hasattr(group.stock_position, "market_value"):
            stock_exposure = group.stock_position.market_value

    risk_table.add_row(
        "Stock Exposure",
        format_currency(stock_exposure),
        "Exposure from stock position",
    )

    # Calculate option/stock ratio
    if stock_exposure != 0:
        option_stock_ratio = option_exposure / stock_exposure
        risk_table.add_row(
            "Option/Stock Ratio",
            f"{option_stock_ratio:.2f}",
            "Ratio of option exposure to stock exposure",
        )

    console.print(risk_table)

    # If we have options and detailed is True, show option greeks
    if detailed and group.option_positions:
        greeks_table = Table(title=f"{ticker} Option Greeks", box=ROUNDED)
        greeks_table.add_column("Type", style="cyan")
        greeks_table.add_column("Strike", style="green", justify="right")
        greeks_table.add_column("Expiry", style="yellow")
        greeks_table.add_column("Delta", style="magenta", justify="right")
        greeks_table.add_column("Gamma", style="blue", justify="right")
        greeks_table.add_column("Theta", style="red", justify="right")
        greeks_table.add_column("Vega", style="green", justify="right")

        for option in group.option_positions:
            # Note: We're using placeholder values for greeks other than delta
            # In a real implementation, these would come from the option data
            greeks_table.add_row(
                option.option_type,
                format_currency(option.strike),
                option.expiry,
                f"{option.delta:.2f}",
                "N/A",  # Gamma
                "N/A",  # Theta
                "N/A",  # Vega
            )

        console.print(greeks_table)


def display_position_simulation(results, console=None):
    """Display position simulation results.

    Args:
        results: Results from simulate_position_with_spy_changes
        console: Rich console for output
    """
    if console is None:
        console = Console()

    ticker = results["ticker"]
    beta = results["beta"]
    current_value = results["current_value"]

    console.print(
        f"\n[bold cyan]Position Simulation: {ticker} (Beta: {beta:.2f})[/bold cyan]"
    )

    # Create a summary table
    summary_table = Table(title=f"{ticker} Simulation Summary", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_column("SPY Change", style="yellow")

    summary_table.add_row("Current Value", format_currency(current_value), "0.0%")
    summary_table.add_row(
        "Minimum Value",
        format_currency(results["min_value"]),
        f"{results['min_spy_change']:.1f}%",
    )
    summary_table.add_row(
        "Maximum Value",
        format_currency(results["max_value"]),
        f"{results['max_spy_change']:.1f}%",
    )

    console.print(summary_table)

    # Create a detailed table with all values
    value_table = Table(title=f"{ticker} Values at Different SPY Changes", box=ROUNDED)
    value_table.add_column("SPY Change", style="yellow")
    value_table.add_column("Position Value", style="green")
    value_table.add_column("Change", style="cyan")
    value_table.add_column("% Change", style="magenta")

    for i, spy_change in enumerate(results["spy_changes"]):
        value = results["values"][i]
        change = results["changes"][i]
        pct_change = results["pct_changes"][i]

        value_table.add_row(
            f"{spy_change * 100:.1f}%",
            format_currency(value),
            f"${change:+,.2f}",
            f"{pct_change:+.2f}%",
        )

    console.print(value_table)
