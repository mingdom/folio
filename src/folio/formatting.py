"""Formatting utilities for displaying financial data."""


def format_currency(value: float) -> str:
    """Formats a numerical value as a currency string (USD).

    Includes a dollar sign, comma separators for thousands, and two decimal places.
    Negative values are represented with a leading minus sign.

    Args:
        value: The numerical value to format.

    Returns:
        A string representing the value in USD currency format (e.g., "$1,234.56", "-$500.00").
    """
    return f"${value:,.2f}"


def format_compact_currency(value: float) -> str:
    """Formats a numerical value as a compact currency string (USD).

    Uses K for thousands, M for millions, B for billions.
    Negative values are represented with a leading minus sign.

    Args:
        value: The numerical value to format.

    Returns:
        A string representing the value in compact USD format (e.g., "$1.23K", "$1.5M", "-$2.1B").
    """
    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        return f"{sign}${abs_value / 1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        return f"{sign}${abs_value / 1_000_000:.1f}M"
    elif abs_value >= 1_000:
        return f"{sign}${abs_value / 1_000:.1f}K"
    else:
        return f"{sign}${abs_value:.2f}"


def format_percentage(value: float) -> str:
    """Formats a numerical value as a percentage string.

    Multiplies the value by 100 and appends a percentage sign. Displays one decimal place.

    Args:
        value: The numerical value to format (e.g., 0.25 for 25%).

    Returns:
        A string representing the value as a percentage (e.g., "25.0%").

    Note:
        This function assumes the input value is a decimal representation of the percentage.
        If you have a whole number (e.g., 25 for 25%), divide it by 100 first.
    """
    return f"{value * 100:.1f}%"


def format_beta(value: float) -> str:
    """Formats a beta value with a trailing Greek beta symbol (β).

    Displays the value with two decimal places.

    Args:
        value: The numerical beta value.

    Returns:
        A string representing the beta value followed by 'β' (e.g., "1.23β").
    """
    return f"{value:.2f}β"


def format_delta(value: float) -> str:
    """Formats an option delta value as a decimal with 2 decimal places.

    Option delta is conventionally displayed as a decimal value between -1.00 and 1.00,
    not as a percentage.

    Args:
        value: The numerical delta value.

    Returns:
        A string representing the delta value with 2 decimal places (e.g., "0.75", "-0.45").
    """
    return f"{value:.2f}"
