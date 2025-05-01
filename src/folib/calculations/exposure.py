"""
Market exposure calculations for stocks and options positions.

This module provides pure functions for calculating market exposure for different
position types, as well as aggregating exposures across positions.

Key functions follow the functional programming paradigm:
- Take all inputs as parameters
- No side effects
- No state
- No class hierarchies

TODO:
- Finish implementation
- Integrate with portfolio_service.py
"""

from collections.abc import Sequence

from ..domain import ExposureMetrics, Position


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
    raise NotImplementedError("Function not yet implemented")
