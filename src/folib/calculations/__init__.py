"""
Calculation functions for portfolio analysis.

This package contains pure functions for financial calculations with no side effects.
All functions follow functional programming principles:
- Take all inputs as parameters
- Return results without modifying inputs
- No global state or side effects
- No class hierarchies or inheritance

Module Overview:
--------------
- exposure.py: Functions for calculating position and portfolio exposures
  - calculate_stock_exposure: Calculate exposure for stock positions
  - calculate_option_exposure: Calculate exposure for option positions
  - calculate_position_exposure: Calculate exposure for any position type
  - calculate_beta_adjusted_exposure: Adjust exposure based on beta
  - aggregate_exposures: Combine exposures from multiple positions

- options.py: Functions for option pricing and Greeks calculations
  - calculate_option_price: Calculate option price using QuantLib
  - calculate_option_delta: Calculate option delta (price sensitivity)
  - calculate_implied_volatility: Calculate implied volatility from option price

- portfolio.py: Functions for portfolio-level calculations
  - calculate_portfolio_metrics: Calculate summary metrics for a portfolio
  - create_value_breakdowns: Create breakdowns of portfolio value by category

Usage:
-----
These functions are typically used by the service layer rather than called directly.
They operate on data classes from the domain module or on primitive types.
"""

from .exposure import (
    aggregate_exposures,
    calculate_beta_adjusted_exposure,
    calculate_option_exposure,
    calculate_position_exposure,
    calculate_stock_exposure,
)
from .options import (
    calculate_implied_volatility,
    calculate_option_delta,
    calculate_option_price,
)
from .portfolio import calculate_portfolio_metrics, create_value_breakdowns

__all__ = [
    # Exposure calculations
    "aggregate_exposures",
    "calculate_beta_adjusted_exposure",
    # Options calculations
    "calculate_implied_volatility",
    "calculate_option_delta",
    "calculate_option_exposure",
    "calculate_option_price",
    # Portfolio calculations
    "calculate_portfolio_metrics",
    "calculate_position_exposure",
    "calculate_stock_exposure",
    "create_value_breakdowns",
]
