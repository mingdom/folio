"""
Portfolio-level calculation functions.

This module provides functions for portfolio-level calculations, including:
- Value breakdowns
- Portfolio metrics
- Aggregation functions
"""


def create_value_breakdowns(
    long_stocks: dict, short_stocks: dict, long_options: dict, short_options: dict
) -> tuple[float, float, float]:
    """
    Create value breakdowns for a portfolio.

    Args:
        long_stocks: Dictionary with long stock metrics
        short_stocks: Dictionary with short stock metrics
        long_options: Dictionary with long option metrics
        short_options: Dictionary with short option metrics

    Returns:
        Tuple of (long_value, short_value, options_value)
    """
    # Calculate long value (positive exposure)
    long_value = long_stocks["value"]

    # Calculate short value (negative exposure)
    short_value = short_stocks["value"]

    # Calculate options value (both long and short)
    options_value = long_options["value"] + short_options["value"]

    return long_value, short_value, options_value


def calculate_portfolio_metrics(
    long_value: float, short_value: float
) -> tuple[float, float, float]:
    """
    Calculate portfolio-level metrics.

    Args:
        long_value: Total long exposure value
        short_value: Total short exposure value

    Returns:
        Tuple of (net_market_exposure, portfolio_beta, short_percentage)
    """
    # Calculate net market exposure
    net_market_exposure = long_value - short_value

    # Calculate portfolio beta (simplified version)
    # In a real implementation, this would use weighted betas
    portfolio_beta = 1.0

    # Calculate short percentage
    total_exposure = long_value + short_value
    short_percentage = (
        (short_value / total_exposure * 100) if total_exposure > 0 else 0.0
    )

    return net_market_exposure, portfolio_beta, short_percentage
