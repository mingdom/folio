"""
Position analysis service.

This module provides high-level functions for analyzing individual positions,
calculating metrics like market exposure, beta-adjusted exposure, and P&L.

Key functions:
- analyze_position: Analyze a single position, calculating all relevant metrics
- analyze_stock_position: Calculate metrics for a stock position
- analyze_option_position: Calculate metrics for an option position
- get_position_beta: Get the beta value for a position
- get_position_market_exposure: Calculate the market exposure for a position
- get_position_beta_adjusted_exposure: Calculate the beta-adjusted exposure for a position
"""

import logging
from typing import cast

from ..calculations import (
    calculate_option_delta,
    calculate_option_exposure,
    calculate_option_price,
    calculate_stock_exposure,
)
from ..domain import OptionPosition, Position, StockPosition
from ..services.ticker_service import ticker_service

# Set up logging
logger = logging.getLogger(__name__)


def analyze_position(
    position: StockPosition | OptionPosition,
) -> dict:
    """
    Analyze a single position, calculating all relevant metrics.

    Args:
        position: The position to analyze

    Returns:
        Dictionary containing:
        - Market value
        - Exposure (delta/beta-adjusted)
        - Greeks (for options)
        - P&L metrics
    """
    if isinstance(position, StockPosition):
        return analyze_stock_position(position)
    else:
        return analyze_option_position(position)


def analyze_stock_position(position: StockPosition) -> dict:
    """
    Analyze a stock position.

    Args:
        position: The stock position to analyze

    Returns:
        Dictionary with analysis results
    """
    # Use the ticker service to get the price and beta
    current_price = ticker_service.get_price(position.ticker)
    beta = ticker_service.get_beta(position.ticker)

    # Calculate exposure
    exposure = calculate_stock_exposure(position.quantity, current_price)
    beta_adjusted = exposure * beta

    return {
        "type": "stock",
        "exposure": exposure,
        "beta_adjusted_exposure": beta_adjusted,
        "market_value": position.quantity * current_price,
        "beta": beta,
        # Add P&L if cost basis is available
        "unrealized_pnl": (current_price - position.cost_basis) * position.quantity
        if position.cost_basis is not None
        else None,
    }


def analyze_option_position(
    position: OptionPosition,
) -> dict:
    """
    Analyze an option position using market price for implied volatility (fail-fast).

    Args:
        position: The option position to analyze

    Returns:
        Dictionary with analysis results

    Raises:
        ValueError, RuntimeError: If option price or IV calculation fails
    """
    underlying_price = ticker_service.get_price(position.ticker)
    beta = ticker_service.get_beta(position.ticker)

    if underlying_price == 0:
        underlying_price = position.strike

    # Use the option's market price (fail if not present or <= 0)
    option_price = position.price
    if option_price is None or option_price <= 0:
        raise ValueError(f"Option market price must be positive, got {option_price}")

    # Calculate delta using market price (implied volatility is calculated internally)
    delta = calculate_option_delta(
        option_type=position.option_type,
        strike=position.strike,
        expiry=position.expiry,
        underlying_price=underlying_price,
        option_price=option_price,
    )

    # Calculate theoretical price (for completeness, not used for IV)
    price = calculate_option_price(
        option_type=position.option_type,
        strike=position.strike,
        expiry=position.expiry,
        underlying_price=underlying_price,
        volatility=None,  # Not used, but kept for compatibility if needed
    )

    # Calculate exposures
    exposure = calculate_option_exposure(
        position.quantity, underlying_price, delta, True
    )
    beta_adjusted = exposure * beta

    return {
        "type": "option",
        "exposure": exposure,
        "beta_adjusted_exposure": beta_adjusted,
        "market_value": position.quantity * position.price * 100,
        "beta": beta,
        "delta": delta,
        "price": price,
        "unrealized_pnl": (position.price - position.cost_basis)
        * position.quantity
        * 100
        if position.cost_basis is not None
        else None,
    }


def get_position_beta(position: Position) -> float:
    """
    Get the beta value for a position.

    Args:
        position: The position to get the beta for

    Returns:
        The beta value for the position
    """
    # Cash positions always have a beta of 0
    if position.position_type == "cash":
        return 0.0

    # Unknown positions default to beta of 0
    if position.position_type == "unknown":
        return 0.0

    # Use the ticker service to get the beta
    return ticker_service.get_beta(position.ticker)


def get_position_price(position: Position) -> float:
    """
    Get the current price for a position's ticker.

    Args:
        position: The position to get the price for

    Returns:
        The current price for the position's ticker
    """
    # For existing positions, use the price stored in the position
    # This ensures we don't change the position's value unexpectedly
    if position.price is not None and position.price > 0:
        return position.price

    # For positions with no price or zero price, get the current price
    return ticker_service.get_price(position.ticker)


def get_position_market_exposure(position: Position) -> float:
    """
    Calculate the market exposure for a position (fail-fast for options).

    Args:
        position: The position to calculate exposure for

    Returns:
        The market exposure for the position

    Raises:
        ValueError, RuntimeError: If option price or IV calculation fails
    """
    if position.position_type == "stock":
        stock_position = cast(StockPosition, position)
        return calculate_stock_exposure(
            stock_position.quantity, get_position_price(stock_position)
        )
    elif position.position_type == "option":
        option_position = cast(OptionPosition, position)
        underlying_price = ticker_service.get_price(option_position.ticker)
        if underlying_price == 0:
            underlying_price = option_position.strike
        option_price = option_position.price
        if option_price is None or option_price <= 0:
            raise ValueError(
                f"Option market price must be positive, got {option_price}"
            )
        delta = calculate_option_delta(
            option_type=option_position.option_type,
            strike=option_position.strike,
            expiry=option_position.expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )
        return calculate_option_exposure(
            option_position.quantity, underlying_price, delta, True
        )
    return 0.0


def get_position_beta_adjusted_exposure(position: Position) -> float:
    """
    Calculate the beta-adjusted exposure for a position.

    Args:
        position: The position to calculate beta-adjusted exposure for

    Returns:
        The beta-adjusted exposure for the position
    """
    # Get the market exposure
    market_exposure = get_position_market_exposure(position)

    # Get the beta
    beta = get_position_beta(position)

    # Calculate beta-adjusted exposure
    return market_exposure * beta
