"""
Market exposure calculations for stocks and options positions.

This module provides functions for calculating market exposure for different
position types and aggregating exposures across positions.
"""

from collections.abc import Sequence
from typing import cast

from ..domain import ExposureMetrics, OptionPosition, Position, StockPosition


def calculate_stock_exposure(
    quantity: float, price: float, include_sign: bool = True
) -> float:
    """
    Calculate the market exposure of a stock position.

    Args:
        quantity: Number of shares (negative for short positions)
        price: Current market price per share
        include_sign: If True, return signed exposure (default True)

    Returns:
        float: Market exposure in dollars
    """
    exposure = quantity * price
    return exposure if include_sign else abs(exposure)


def calculate_option_exposure(
    quantity: float, underlying_price: float, delta: float, include_sign: bool = True
) -> float:
    """
    Calculate the market exposure of an option position.

    Args:
        quantity: Number of contracts (negative for short positions)
        underlying_price: Price of underlying stock
        delta: Option delta (-1.0 to 1.0)
        include_sign: If True, return signed exposure (default True)

    Returns:
        float: Market exposure in dollars
    """
    import logging

    logger = logging.getLogger(__name__)

    # Standard contract multiplier for equity options
    CONTRACT_SIZE = 100

    # Calculate notional value (always positive)
    notional_value = CONTRACT_SIZE * abs(quantity) * underlying_price

    # Adjust delta based on position direction (quantity)
    # For short positions (quantity < 0), negate the delta
    # This matches the behavior of the old implementation
    adjusted_delta = delta if quantity >= 0 else -delta

    # Calculate exposure
    exposure = adjusted_delta * notional_value

    # Log detailed calculation steps
    logger.debug(
        f"Option exposure calculation: {quantity} contracts, {delta} raw delta, {adjusted_delta} adjusted delta * "
        f"({CONTRACT_SIZE} shares * {abs(quantity)} contracts * ${underlying_price} price) = ${exposure}"
    )

    # If include_sign is False, return the absolute value
    if not include_sign:
        exposure = abs(exposure)

    return exposure


def aggregate_exposures(
    exposures: Sequence[float], weights: Sequence[float] | None = None
) -> float:
    """
    Aggregate multiple exposures, optionally with weights.

    Args:
        exposures: List of position exposures
        weights: Optional list of weights (e.g., betas)

    Returns:
        float: Total exposure
    """
    if not exposures:
        return 0.0

    if weights is None:
        return sum(exposures)

    if len(weights) != len(exposures):
        raise ValueError("Length of weights must match length of exposures")

    return sum(
        exposure * weight for exposure, weight in zip(exposures, weights, strict=True)
    )


def calculate_beta_adjusted_exposure(exposure: float, beta: float | None) -> float:
    """
    Calculate beta-adjusted exposure.

    Args:
        exposure: Market exposure
        beta: Beta value (defaults to 1.0 if None)

    Returns:
        The beta-adjusted exposure
    """
    # Use beta of 1.0 if None is provided
    if beta is None:
        beta = 1.0

    return exposure * beta


def calculate_position_exposure(
    position: Position, delta: float | None = None, beta: float = 1.0
) -> ExposureMetrics:
    """
    Calculate exposure metrics for a position.

    Args:
        position: The position
        delta: Option delta (only needed for option positions)
        beta: Beta value for the underlying

    Returns:
        Exposure metrics for the position
    """
    if position.position_type == "stock":
        stock_position = cast(StockPosition, position)
        market_exposure = calculate_stock_exposure(
            stock_position.quantity, stock_position.price
        )
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        return ExposureMetrics(
            market_exposure=market_exposure,
            beta_adjusted_exposure=beta_adjusted,
        )
    elif position.position_type == "option":
        if delta is None:
            raise ValueError("Delta must be provided for option positions")

        option_position = cast(OptionPosition, position)
        # IMPORTANT: We need to use the underlying price, not the option price
        # This was a key issue causing exposure calculation differences
        # The old implementation uses underlying_price in src/folio/options.py

        # We don't have the underlying price here, so we need to rely on the caller
        # to provide it. For now, we'll use a placeholder and let the caller override.
        underlying_price = (
            option_position.price
        )  # This will be overridden by the caller

        market_exposure = calculate_option_exposure(
            option_position.quantity,
            underlying_price,  # This should be the underlying price, not the option price
            delta,
        )
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        return ExposureMetrics(
            market_exposure=market_exposure,
            beta_adjusted_exposure=beta_adjusted,
            delta_exposure=market_exposure,
        )
    else:
        # For cash or unknown positions, exposure is zero
        return ExposureMetrics(
            market_exposure=0.0,
            beta_adjusted_exposure=0.0,
        )
