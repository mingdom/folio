"""Common calculation functions used across the codebase.

This module contains pure calculation functions that are used by multiple modules
in the codebase. By centralizing these functions here, we avoid circular dependencies
between modules like data_model.py and portfolio_value.py.

These functions should be pure and not depend on any other modules in the codebase
except for basic utility functions and logging.
"""

from .logger import logger


def calculate_notional_value(quantity: float, underlying_price: float) -> float:
    """Calculate the notional value of an option position.

    This is the canonical implementation that should be used throughout the codebase.
    Notional value represents the total value controlled by the option contracts.

    Args:
        quantity: Number of contracts (can be negative for short positions)
        underlying_price: Price of the underlying asset

    Returns:
        The absolute notional value (always positive)
    """
    return 100 * abs(quantity) * underlying_price


def calculate_net_exposure(stock_position, option_positions) -> float:
    """Calculate net exposure for a portfolio group.

    This is the canonical implementation that should be used everywhere in the codebase.

    Args:
        stock_position: The stock position (if any)
        option_positions: List of option positions

    Returns:
        Net exposure (stock market exposure + sum of option delta exposures)
    """
    stock_exposure = stock_position.market_exposure if stock_position else 0.0
    option_delta_exposure = sum(opt.delta_exposure for opt in option_positions)

    logger.debug("Calculating net exposure:")
    logger.debug(f"  Stock exposure: {stock_exposure}")
    logger.debug(f"  Option delta exposure: {option_delta_exposure}")
    logger.debug(f"  Net exposure: {stock_exposure + option_delta_exposure}")

    return stock_exposure + option_delta_exposure


def calculate_beta_adjusted_exposure(stock_position, option_positions) -> float:
    """Calculate beta-adjusted exposure for a portfolio group.

    This is the canonical implementation that should be used everywhere in the codebase.

    Args:
        stock_position: The stock position (if any)
        option_positions: List of option positions

    Returns:
        Beta-adjusted exposure (stock beta-adjusted exposure + sum of option beta-adjusted exposures)
    """
    stock_beta_adjusted = (
        stock_position.beta_adjusted_exposure if stock_position else 0.0
    )
    options_beta_adjusted = sum(opt.beta_adjusted_exposure for opt in option_positions)

    logger.debug("Calculating beta-adjusted exposure:")
    logger.debug(f"  Stock beta-adjusted: {stock_beta_adjusted}")
    logger.debug(f"  Options beta-adjusted: {options_beta_adjusted}")
    logger.debug(
        f"  Beta-adjusted exposure: {stock_beta_adjusted + options_beta_adjusted}"
    )

    return stock_beta_adjusted + options_beta_adjusted


def calculate_option_exposure(
    option_contract, underlying_price, risk_free_rate=0.05, implied_volatility=None
) -> dict:
    """Calculate exposure metrics for an option position.

    This function calculates various exposure metrics for an option position, including
    delta, delta exposure (delta * notional_value), and beta-adjusted exposure
    (delta_exposure * beta).

    Args:
        option_contract: The option contract
        underlying_price: The price of the underlying asset
        risk_free_rate: The risk-free interest rate. Defaults to 0.05 (5%).
        implied_volatility: Optional override for implied volatility. Defaults to None.

    Returns:
        A dictionary containing exposure metrics:
        - 'delta': The option's delta
        - 'delta_exposure': The delta-adjusted exposure (delta * notional_value)
        - 'beta_adjusted_exposure': The beta-adjusted exposure (delta_exposure * beta)
    """
    # Import here to avoid circular imports
    from .options import calculate_option_delta

    # Calculate delta using the options module
    delta = calculate_option_delta(
        option_contract,
        underlying_price,
        risk_free_rate=risk_free_rate,
        implied_volatility=implied_volatility,
    )

    # Calculate notional value
    notional_value = calculate_notional_value(
        option_contract.quantity, underlying_price
    )

    # Calculate delta exposure
    delta_exposure = delta * notional_value

    # Calculate beta-adjusted exposure
    beta = getattr(option_contract, "underlying_beta", 1.0)
    beta_adjusted_exposure = delta_exposure * beta

    return {
        "delta": delta,
        "delta_exposure": delta_exposure,
        "beta_adjusted_exposure": beta_adjusted_exposure,
        "notional_value": notional_value,
    }
