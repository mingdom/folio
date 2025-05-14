"""
Formatting utilities for the Folio CLI.

This module provides utilities for formatting output in the Folio CLI,
including functions for formatting currency, percentages, and tables.
"""

import math
from decimal import Decimal
from typing import Any

from rich.table import Table


def format_currency(
    value: float | Decimal | None,
    include_sign: bool = False,
    round_to_dollar: bool = True,
) -> str:
    """
    Format a value as currency.

    Args:
        value: The value to format
        include_sign: Whether to include a sign for positive values
        round_to_dollar: Whether to round to the nearest dollar (no decimal places)

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

    # Round to nearest dollar if requested
    if round_to_dollar:
        value = round(value)

        # Format with commas and no decimal places
        if value < 0:
            # For negative values, don't use abs() - preserve the sign semantics
            # but display in brackets without the minus sign
            formatted = f"${-value:,.0f}"  # Negate to get positive number for display
            return f"({formatted})"  # Negative values in brackets
        elif include_sign and value > 0:
            formatted = f"${value:,.0f}"
            return f"+{formatted}"
        else:
            formatted = f"${value:,.0f}"
            return formatted
    else:
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
    table.add_column("% of Total", justify="right")

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
        # net_exposure_pct is no longer needed
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
        # net_exposure_pct is no longer needed

    def percent(val):
        if total_value in (None, 0) or val is None:
            return "N/A"
        pct = val / total_value
        return format_percentage(pct)

    table.add_row("Total Value", format_currency(total_value), "100.00%")
    table.add_row("Stock Value", format_currency(stock_value), percent(stock_value))
    table.add_row("Option Value", format_currency(option_value), percent(option_value))
    table.add_row("Cash Value", format_currency(cash_value), percent(cash_value))

    if unknown_value != 0:
        table.add_row(
            "Unknown Value", format_currency(unknown_value), percent(unknown_value)
        )

    if pending_activity_value != 0:
        table.add_row(
            "Pending Activity",
            format_currency(pending_activity_value),
            percent(pending_activity_value),
        )

    table.add_row(
        "Net Market Exposure",
        format_currency(net_market_exposure),
        percent(net_market_exposure),
    )
    table.add_row(
        "Beta Adjusted Exposure",
        format_currency(beta_adjusted_exposure),
        percent(beta_adjusted_exposure),
    )

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
    table.add_column("Beta", justify="right")  # Beta column
    table.add_column("Beta-Adj Exp", justify="right")  # Beta-adjusted exposure column

    for i, position in enumerate(positions, 1):
        # Check if position is a dictionary or a Position object
        if hasattr(position, "get"):
            # It's a dictionary
            position_type = position.get("position_type", "unknown")
            ticker = position.get("ticker", "")
            quantity = position.get("quantity")
            price = position.get("price")
            market_value = position.get("market_value")
            # Get beta and exposure values if available, otherwise default to 0
            beta = position.get("beta", 1.0)
            beta_adjusted_exposure = position.get("beta_adjusted_exposure", 0.0)
        else:
            # It's a Position object
            position_type = position.position_type
            ticker = position.ticker
            quantity = position.quantity
            price = position.price
            market_value = position.market_value
            # Get beta and exposure values if available, otherwise default to 0
            beta = getattr(position, "beta", 1.0)
            beta_adjusted_exposure = getattr(position, "beta_adjusted_exposure", 0.0)

        # Round values to nearest dollar
        if price is not None and isinstance(price, (int, float)):
            price = round(price, 2)  # Keep 2 decimal places for price
        if market_value is not None and isinstance(market_value, (int, float)):
            market_value = round(market_value)  # Round to nearest dollar
        if beta_adjusted_exposure is not None and isinstance(
            beta_adjusted_exposure, (int, float)
        ):
            beta_adjusted_exposure = round(
                beta_adjusted_exposure
            )  # Round to nearest dollar

        # Format the row based on position type
        table.add_row(
            str(i),
            ticker,
            position_type,
            format_quantity(quantity),
            format_currency(
                price, round_to_dollar=False
            ),  # Keep decimal places for price
            format_currency(
                market_value, round_to_dollar=True
            ),  # Round to nearest dollar
            f"{beta:.2f}" if isinstance(beta, (int, float)) else "1.00",  # Format beta
            format_currency(
                beta_adjusted_exposure, round_to_dollar=True
            ),  # Round to nearest dollar
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
    table.add_column("Beta Adjusted Exposure", justify="right")
    table.add_column("Beta Adjusted %", justify="right")

    # Ensure we're working with a dictionary
    if not isinstance(exposures, dict):
        exposures = {
            k: getattr(exposures, k)
            for k in dir(exposures)
            if not k.startswith("_") and not callable(getattr(exposures, k))
        }

    # Gather per-category values
    rows = [
        (
            "Long Stock",
            exposures.get("long_stock_exposure", 0.0),
            exposures.get("long_stock_beta_adjusted", 0.0),
        ),
        (
            "Short Stock",
            exposures.get("short_stock_exposure", 0.0),
            exposures.get("short_stock_beta_adjusted", 0.0),
        ),
        (
            "Long Option",
            exposures.get("long_option_exposure", 0.0),
            exposures.get("long_option_beta_adjusted", 0.0),
        ),
        (
            "Short Option",
            exposures.get("short_option_exposure", 0.0),
            exposures.get("short_option_beta_adjusted", 0.0),
        ),
    ]
    total_beta_adjusted = sum(abs(row[2]) for row in rows)
    if total_beta_adjusted == 0:
        total_beta_adjusted = None

    for label, value, beta_adj in rows:
        percent = (beta_adj / total_beta_adjusted) if total_beta_adjusted else None
        table.add_row(
            label,
            format_currency(value),
            format_currency(beta_adj),
            format_percentage(percent),
        )

    return table
