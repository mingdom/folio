"""
Core domain models for the Folib library.

This module contains the fundamental data structures used throughout the library.
All classes are simple data containers with minimal methods and a clear inheritance hierarchy.

Migration Plan Notes:
---------------------
This module is part of Phase 1 of the folib migration plan, focusing on Portfolio Loading E2E.
It replaces the functionality in src/folio/data_model.py with a cleaner, more maintainable design.

Key differences from the old implementation:
- Uses frozen dataclasses for immutability
- Separates data models from business logic
- Uses composition over inheritance where appropriate
- Provides minimal computed properties
- Uses strong type hints throughout
- Simplifies the portfolio structure with a flat list of positions

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
from typing import Literal, cast


@dataclass(frozen=True)
class Position:
    """Base position data with common fields for all position types."""

    ticker: str
    quantity: float
    price: float
    position_type: Literal["stock", "option", "cash", "unknown"]
    cost_basis: float | None = None

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price


@dataclass(frozen=True)
class StockPosition(Position):
    """Stock position data."""

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        cost_basis: float | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "stock")
        object.__setattr__(self, "cost_basis", cost_basis)


@dataclass(frozen=True)
class OptionPosition(Position):
    """Option position data."""

    # These fields are added in __init__ and not part of the base Position class
    strike: float = field(init=False)
    expiry: date = field(init=False)
    option_type: Literal["CALL", "PUT"] = field(init=False)

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        strike: float,
        expiry: date,
        option_type: Literal["CALL", "PUT"],
        cost_basis: float | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "option")
        object.__setattr__(self, "strike", strike)
        object.__setattr__(self, "expiry", expiry)
        object.__setattr__(self, "option_type", option_type)
        object.__setattr__(self, "cost_basis", cost_basis)

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price * 100  # 100 shares per contract


@dataclass(frozen=True)
class CashPosition(Position):
    """Cash or cash-equivalent position."""

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        cost_basis: float | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "cash")
        object.__setattr__(self, "cost_basis", cost_basis)


@dataclass(frozen=True)
class UnknownPosition(Position):
    """Position that couldn't be classified as stock, option, or cash."""

    # This field is added in __init__ and not part of the base Position class
    description: str = field(init=False)

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        description: str,
        cost_basis: float | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "unknown")
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "cost_basis", cost_basis)


@dataclass(frozen=True)
class PortfolioHolding:
    """Raw entry from a portfolio CSV file.

    This class represents the essential data from a single row in the portfolio CSV file.
    It only includes the core fields needed for position analysis, excluding any
    private or irrelevant information.

    The source CSV format (portfolio-private.csv) contains these columns:
    - Symbol: The ticker symbol of the security
    - Description: Text description of the security
    - Quantity: Number of shares or contracts
    - Last Price: Current price per share/contract
    - Current Value: Total value of the position
    - Cost Basis Total: Total cost basis of the position

    Other columns in the source CSV (Account Number, Account Name, Last Price Change,
    Today's Gain/Loss, etc.) are intentionally excluded as they're either private
    or not relevant to the core position analysis.
    """

    symbol: str
    description: str
    quantity: float
    price: float  # Last Price in the CSV
    value: float  # Current Value in the CSV
    cost_basis_total: float | None = None  # Cost Basis Total in the CSV


@dataclass(frozen=True)
class Portfolio:
    """Container for the entire portfolio."""

    positions: list[Position]
    pending_activity_value: float = 0.0

    @property
    def stock_positions(self) -> list[StockPosition]:
        """Get all stock positions."""
        return [
            cast(StockPosition, p) for p in self.positions if p.position_type == "stock"
        ]

    @property
    def option_positions(self) -> list[OptionPosition]:
        """Get all option positions."""
        return [
            cast(OptionPosition, p)
            for p in self.positions
            if p.position_type == "option"
        ]

    @property
    def cash_positions(self) -> list[Position]:
        """Get all cash positions."""
        return [p for p in self.positions if p.position_type == "cash"]

    @property
    def unknown_positions(self) -> list[Position]:
        """Get all unknown positions."""
        return [p for p in self.positions if p.position_type == "unknown"]


@dataclass(frozen=True)
class PortfolioSummary:
    """Summary metrics for the portfolio."""

    total_value: float
    stock_value: float
    option_value: float
    cash_value: float
    unknown_value: float
    pending_activity_value: float
    net_market_exposure: float
    portfolio_beta: float | None = None


@dataclass(frozen=True)
class ExposureMetrics:
    """Exposure metrics for a position or group."""

    market_exposure: float
    beta_adjusted_exposure: float | None = None
    delta_exposure: float | None = None  # For options only


# Keep PortfolioGroup for backward compatibility during migration
@dataclass(frozen=True)
class PortfolioGroup:
    """Group of related positions (stock + options).

    Note: This class is deprecated and will be removed in a future version.
    Use the helper functions in portfolio_service.py instead.
    """

    ticker: str
    stock_position: StockPosition | None = None
    option_positions: list[OptionPosition] = field(default_factory=list)
