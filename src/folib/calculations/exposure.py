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
    # Standard contract multiplier for equity options
    CONTRACT_SIZE = 100

    # Calculate exposure
    exposure = quantity * CONTRACT_SIZE * underlying_price * delta
    return exposure if include_sign else abs(exposure)


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


def calculate_beta_adjusted_exposure(exposure: float, beta: float) -> float:
    """
    Calculate beta-adjusted exposure.

    Args:
        exposure: Market exposure
        beta: Beta value

    Returns:
        The beta-adjusted exposure
    """
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
        market_exposure = calculate_option_exposure(
            option_position.quantity,
            option_position.price,  # Using option price as a proxy for underlying
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
