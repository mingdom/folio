"""
Formatting utilities for the Folio CLI.

This module provides utilities for formatting output in the Folio CLI,
including functions for formatting currency, percentages, and tables.
"""

from decimal import Decimal
from typing import Any

from rich.table import Table


def format_currency(value: float | Decimal | None, include_sign: bool = False) -> str:
    """
    Format a value as currency.

    Args:
        value: The value to format
        include_sign: Whether to include a sign for positive values

    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"

    # Convert to float if Decimal
    if isinstance(value, Decimal):
        value = float(value)

    # Format with commas and 2 decimal places
    if abs(value) >= 1_000_000:
        # Use millions format for large numbers
        formatted = f"${abs(value) / 1_000_000:.2f}M"
    else:
        formatted = f"${abs(value):,.2f}"

    # Add sign
    if value < 0:
        return f"-{formatted}"
    elif include_sign and value > 0:
        return f"+{formatted}"
    else:
        return formatted


def format_percentage(value: float | Decimal | None, include_sign: bool = False) -> str:
    """
    Format a value as a percentage.

    Args:
        value: The value to format (as a decimal, e.g., 0.05 for 5%)
        include_sign: Whether to include a sign for positive values

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    # Convert to float if Decimal
    if isinstance(value, Decimal):
        value = float(value)

    # Convert to percentage and format with 2 decimal places
    percentage = value * 100

    # Format the percentage
    if percentage < 0:
        return f"-{abs(percentage):.2f}%"
    elif include_sign and percentage > 0:
        return f"+{percentage:.2f}%"
    else:
        return f"{percentage:.2f}%"


def format_quantity(value: float | int | None) -> str:
    """
    Format a quantity value.

    Args:
        value: The value to format

    Returns:
        Formatted quantity string
    """
    if value is None:
        return "N/A"

    # Format with commas and no decimal places for whole numbers
    if value == int(value):
        return f"{int(value):,}"
    else:
        return f"{value:,.2f}"


def create_portfolio_summary_table(summary: Any) -> Table:
    """
    Create a table for portfolio summary.

    Args:
        summary: Portfolio summary data (either a PortfolioSummary object or a dictionary)

    Returns:
        Rich Table object
    """
    table = Table(title="Portfolio Summary")

    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    # Handle both dictionary and PortfolioSummary object
    if hasattr(summary, "get"):
        # It's a dictionary
        total_value = summary.get("total_value")
        stock_value = summary.get("stock_value")
        option_value = summary.get("option_value")
        cash_value = summary.get("cash_value")
        unknown_value = summary.get("unknown_value", 0)
        pending_activity_value = summary.get("pending_activity_value", 0)
        net_market_exposure = summary.get("net_market_exposure")
        portfolio_beta = summary.get("portfolio_beta")
    else:
        # It's a PortfolioSummary object
        total_value = summary.total_value
        stock_value = summary.stock_value
        option_value = summary.option_value
        cash_value = summary.cash_value
        unknown_value = summary.unknown_value
        pending_activity_value = summary.pending_activity_value
        net_market_exposure = summary.net_market_exposure
        portfolio_beta = summary.portfolio_beta

    table.add_row("Total Value", format_currency(total_value))
    table.add_row("Stock Value", format_currency(stock_value))
    table.add_row("Option Value", format_currency(option_value))
    table.add_row("Cash Value", format_currency(cash_value))

    if unknown_value != 0:
        table.add_row("Unknown Value", format_currency(unknown_value))

    if pending_activity_value != 0:
        table.add_row("Pending Activity", format_currency(pending_activity_value))

    table.add_row("Net Market Exposure", format_currency(net_market_exposure))

    if portfolio_beta is not None:
        table.add_row("Portfolio Beta", f"{portfolio_beta:.2f}")

    return table


def create_positions_table(
    positions: list[Any], title: str = "Portfolio Positions"
) -> Table:
    """
    Create a table for portfolio positions.

    Args:
        positions: List of position data (either dictionaries or Position objects)
        title: Table title

    Returns:
        Rich Table object
    """
    table = Table(title=title)

    table.add_column("#", style="dim")
    table.add_column("Ticker", style="bold")
    table.add_column("Type", style="dim")
    table.add_column("Quantity", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Value", justify="right")

    for i, position in enumerate(positions, 1):
        # Check if position is a dictionary or a Position object
        if hasattr(position, "get"):
            # It's a dictionary
            position_type = position.get("position_type", "unknown")
            ticker = position.get("ticker", "")
            quantity = position.get("quantity")
            price = position.get("price")
            market_value = position.get("market_value")
        else:
            # It's a Position object
            position_type = position.position_type
            ticker = position.ticker
            quantity = position.quantity
            price = position.price
            market_value = position.market_value

        # Format the row based on position type
        table.add_row(
            str(i),
            ticker,
            position_type,
            format_quantity(quantity),
            format_currency(price),
            format_currency(market_value),
        )

    return table


def create_exposures_table(exposures: dict[str, Any]) -> Table:
    """
    Create a table for portfolio exposures.

    Args:
        exposures: Portfolio exposure data (dictionary)

    Returns:
        Rich Table object
    """
    table = Table(title="Portfolio Exposures")

    table.add_column("Exposure Type", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("% of Portfolio", justify="right")

    # Ensure we're working with a dictionary
    if not isinstance(exposures, dict):
        # Convert to dictionary if it's not already
        exposures = {
            k: getattr(exposures, k)
            for k in dir(exposures)
            if not k.startswith("_") and not callable(getattr(exposures, k))
        }

    total_value = exposures.get("total_value", 0)

    # Add rows for each exposure type
    for exposure_type, value in exposures.items():
        if exposure_type == "total_value":
            continue

        # Calculate percentage of portfolio
        percentage = (value / total_value) if total_value != 0 else 0

        table.add_row(
            exposure_type.replace("_", " ").title(),
            format_currency(value),
            format_percentage(percentage),
        )

    return table
