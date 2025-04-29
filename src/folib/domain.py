"""
Core domain models for the Folib library.

This module contains the fundamental data structures used throughout the library.
All classes are simple data containers with no methods or complex inheritance.

Migration Plan Notes:
---------------------
This module is part of Phase 1 of the folib migration plan, focusing on Portfolio Loading E2E.
It replaces the functionality in src/folio/data_model.py with a cleaner, more maintainable design.

Key differences from the old implementation:
- Uses frozen dataclasses for immutability
- Separates data models from business logic
- Uses composition over inheritance
- Provides minimal computed properties
- Uses strong type hints throughout

Old Codebase References:
------------------------
- src/folio/data_model.py: Contains the original Position, StockPosition, OptionPosition,
  PortfolioGroup, and PortfolioSummary classes
- src/folio/portfolio_value.py: Contains functions for calculating exposures and portfolio metrics
- src/folio/options.py: Contains functions for option pricing and greeks calculations

Potential Issues:
----------------
- The old codebase mixed data models with business logic, which needs to be separated
- The old Position class used inheritance, while the new design uses composition
- The old implementation had many computed properties that are now moved to utility functions
- The old implementation used mutable classes, while the new design uses immutable dataclasses
- Some field types have changed (e.g., expiry is now a date object instead of a string)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

# Use the built-in NotImplementedError exception instead of creating our own


@dataclass(frozen=True)
class Position:
    """Base position data."""

    ticker: str
    quantity: float
    position_type: Literal["stock", "option"]


@dataclass(frozen=True)
class StockPosition:
    """Stock position data."""

    ticker: str
    quantity: float
    price: float
    cost_basis: float | None = None

    @property
    def position_type(self) -> Literal["stock"]:
        """Return the position type."""
        return "stock"

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price


@dataclass(frozen=True)
class OptionPosition:
    """Option position data."""

    ticker: str
    quantity: float
    strike: float
    expiry: date
    option_type: Literal["CALL", "PUT"]
    price: float
    underlying_price: float
    cost_basis: float | None = None

    @property
    def position_type(self) -> Literal["option"]:
        """Return the position type."""
        return "option"

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price * 100  # 100 shares per contract


@dataclass(frozen=True)
class PortfolioHolding:
    """Raw entry from a portfolio CSV file."""

    symbol: str
    description: str
    quantity: float
    price: float
    value: float
    account_type: str
    cost_basis: float | None = None
    percent_of_account: float | None = None


@dataclass(frozen=True)
class PortfolioGroup:
    """Group of related positions (stock + options)."""

    ticker: str
    stock_position: StockPosition | None = None
    option_positions: list[OptionPosition] = field(default_factory=list)


@dataclass(frozen=True)
class Portfolio:
    """Container for the entire portfolio."""

    groups: list[PortfolioGroup]
    cash_positions: list[StockPosition] = field(default_factory=list)
    pending_activity_value: float = 0.0


@dataclass(frozen=True)
class PortfolioSummary:
    """Summary metrics for the portfolio."""

    total_value: float
    stock_value: float
    option_value: float
    cash_value: float
    pending_activity_value: float
    net_market_exposure: float
    portfolio_beta: float | None = None


@dataclass(frozen=True)
class ExposureMetrics:
    """Exposure metrics for a position or group."""

    market_exposure: float
    beta_adjusted_exposure: float | None = None
    delta_exposure: float | None = None  # For options only
