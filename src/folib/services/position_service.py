"""
Position analysis service.

This module provides high-level functions for analyzing individual positions,
calculating metrics like market exposure, beta-adjusted exposure, and P&L.

Key functions:
- analyze_position: Analyze a single position, calculating all relevant metrics
- analyze_stock_position: Calculate metrics for a stock position
- analyze_option_position: Calculate metrics for an option position
"""

from typing import Protocol

from ..calculations import (
    calculate_option_delta,
    calculate_option_exposure,
    calculate_option_price,
    calculate_stock_exposure,
)
from ..domain import OptionPosition, StockPosition


class MarketData(Protocol):
    """Protocol defining the required market data interface."""

    def get_price(self, ticker: str) -> float:
        """Get current price for a ticker."""
        ...

    def get_beta(self, ticker: str) -> float:
        """Get beta for a ticker."""
        ...

    def get_volatility(self, ticker: str) -> float:
        """Get historical volatility for a ticker."""
        ...


def analyze_position(
    position: StockPosition | OptionPosition,
    market_data: MarketData,
) -> dict:
    """
    Analyze a single position, calculating all relevant metrics.

    Args:
        position: The position to analyze
        market_data: Market data provider

    Returns:
        Dictionary containing:
        - Market value
        - Exposure (delta/beta-adjusted)
        - Greeks (for options)
        - P&L metrics
    """
    if isinstance(position, StockPosition):
        return analyze_stock_position(position, market_data)
    else:
        return analyze_option_position(position, market_data)


def analyze_stock_position(
    position: StockPosition,
    market_data: MarketData,
) -> dict:
    """Analyze a stock position."""
    current_price = market_data.get_price(position.ticker)
    beta = market_data.get_beta(position.ticker)

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
    market_data: MarketData,
) -> dict:
    """Analyze an option position."""
    underlying_price = market_data.get_price(position.ticker)
    beta = market_data.get_beta(position.ticker)
    volatility = market_data.get_volatility(position.ticker)

    # Calculate Greeks
    delta = calculate_option_delta(
        option_type=position.option_type,
        strike=position.strike,
        expiry=position.expiry,
        underlying_price=underlying_price,
        volatility=volatility,
    )

    # Calculate theoretical price
    price = calculate_option_price(
        option_type=position.option_type,
        strike=position.strike,
        expiry=position.expiry,
        underlying_price=underlying_price,
        volatility=volatility,
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
        "market_value": position.quantity
        * position.price
        * 100,  # Standard contract size
        "beta": beta,
        "delta": delta,
        "price": price,
        # Add P&L if cost basis is available
        "unrealized_pnl": (position.price - position.cost_basis)
        * position.quantity
        * 100
        if position.cost_basis is not None
        else None,
    }
