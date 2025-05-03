"""
Formatting utilities for the Folio CLI.

This module provides utilities for formatting output in the Folio CLI,
including functions for formatting currency, percentages, and tables.
"""

import math
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

    # Check for NaN values
    if isinstance(value, float) and math.isnan(value):  # NaN check
        return "N/A"

    # Convert to float if Decimal
    if isinstance(value, Decimal):
        value = float(value)

    # Format with commas and 2 decimal places
    # Always use full numbers with commas for financial display
    # Format according to financial reporting standards
    # Negative values in brackets, positive values as is
    if value < 0:
        # For negative values, don't use abs() - preserve the sign semantics
        # but display in brackets without the minus sign
        formatted = f"${-value:,.2f}"  # Negate to get positive number for display
        return f"({formatted})"  # Negative values in brackets
    elif include_sign and value > 0:
        formatted = f"${value:,.2f}"
        return f"+{formatted}"
    else:
        formatted = f"${value:,.2f}"
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

    # Format the percentage according to financial reporting standards
    # Negative values in brackets, positive values as is
    if percentage < 0:
        # For negative values, don't use abs() - preserve the sign semantics
        # but display in brackets without the minus sign
        return f"({-percentage:.2f}%)"  # Negative percentages in brackets
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

    # Check for NaN values
    if isinstance(value, float) and math.isnan(value):  # NaN check
        return "N/A"

    # Format with commas and no decimal places for whole numbers
    # Use brackets for negative values according to financial reporting standards
    if value < 0:
        # For negative values, don't use abs() - preserve the sign semantics
        # but display in brackets without the minus sign
        if value == int(value):
            return f"({-int(value):,})"  # Negate to get positive number for display
        else:
            return f"({-value:,.2f})"  # Negate to get positive number for display
    elif value == int(value):
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
        unknown_value = summary.get("unknown_value")
        pending_activity_value = summary.get("pending_activity_value")
        net_market_exposure = summary.get("net_market_exposure")
        beta_adjusted_exposure = summary.get("beta_adjusted_exposure")
        net_exposure_pct = summary.get("net_exposure_pct")
    else:
        # It's a PortfolioSummary object
        total_value = summary.total_value
        stock_value = summary.stock_value
        option_value = summary.option_value
        cash_value = summary.cash_value
        unknown_value = summary.unknown_value
        pending_activity_value = summary.pending_activity_value
        net_market_exposure = summary.net_market_exposure
        beta_adjusted_exposure = summary.beta_adjusted_exposure
        net_exposure_pct = summary.net_exposure_pct

    table.add_row("Total Value", format_currency(total_value))
    table.add_row("Stock Value", format_currency(stock_value))
    table.add_row("Option Value", format_currency(option_value))
    table.add_row("Cash Value", format_currency(cash_value))

    if unknown_value != 0:
        table.add_row("Unknown Value", format_currency(unknown_value))

    if pending_activity_value != 0:
        table.add_row("Pending Activity", format_currency(pending_activity_value))

    table.add_row("Net Market Exposure", format_currency(net_market_exposure))
    table.add_row("Net Exposure %", format_percentage(net_exposure_pct))
    table.add_row("Beta Adjusted Exposure", format_currency(beta_adjusted_exposure))

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

    total_value = exposures.get("total_value")

    # Add rows for each exposure type
    for exposure_type, value in exposures.items():
        if exposure_type == "total_value":
            continue

        # Calculate percentage of portfolio
        if total_value is None or total_value == 0:
            percentage = None
        else:
            percentage = value / total_value

        table.add_row(
            exposure_type.replace("_", " ").title(),
            format_currency(value),
            format_percentage(percentage),
        )

    return table
