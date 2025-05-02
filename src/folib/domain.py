"""
Core domain models for the Folib library.

This module contains the fundamental data structures used throughout the library.
All classes are simple data containers with minimal methods and a clear inheritance hierarchy.

Key design principles:
- Uses frozen dataclasses for immutability
- Separates data models from business logic
- Uses composition over inheritance where appropriate
- Provides minimal computed properties
- Uses strong type hints throughout
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
    raw_data: dict | None = None  # Original CSV data for debugging and recalculation

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price

    def to_dict(self) -> dict:
        """Convert the position to a dictionary for display purposes."""
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "price": self.price,
            "position_type": self.position_type,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
        }


@dataclass(frozen=True)
class StockPosition(Position):
    """Stock position data."""

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        cost_basis: float | None = None,
        raw_data: dict | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "stock")
        object.__setattr__(self, "cost_basis", cost_basis)
        object.__setattr__(self, "raw_data", raw_data)


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
        raw_data: dict | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "option")
        object.__setattr__(self, "strike", strike)
        object.__setattr__(self, "expiry", expiry)
        object.__setattr__(self, "option_type", option_type)
        object.__setattr__(self, "cost_basis", cost_basis)
        object.__setattr__(self, "raw_data", raw_data)

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price * 100  # 100 shares per contract

    def to_dict(self) -> dict:
        """Convert the option position to a dictionary for display purposes."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "strike": self.strike,
                "expiry": self.expiry.isoformat(),
                "option_type": self.option_type,
            }
        )
        return base_dict


@dataclass(frozen=True)
class CashPosition(Position):
    """Cash or cash-equivalent position."""

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        cost_basis: float | None = None,
        raw_data: dict | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "cash")
        object.__setattr__(self, "cost_basis", cost_basis)
        object.__setattr__(self, "raw_data", raw_data)


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
        raw_data: dict | None = None,
    ):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "position_type", "unknown")
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "cost_basis", cost_basis)
        object.__setattr__(self, "raw_data", raw_data)

    def to_dict(self) -> dict:
        """Convert the unknown position to a dictionary for display purposes."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "description": self.description,
            }
        )
        return base_dict


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

    @property
    def market_value(self) -> float:
        """Alias for value to maintain compatibility with Position class."""
        return self.value

    @property
    def position_type(self) -> str:
        """
        Determine the position type based on the description.
        This is a compatibility property to match the Position class interface.

        Returns:
            'option' if the description matches option patterns, 'stock' otherwise
        """
        # Simple check for option description patterns
        if self.description and any(
            x in self.description.upper() for x in [" CALL", " PUT"]
        ):
            return "option"
        return "stock"


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

    def to_dict(self) -> dict:
        """Convert the portfolio summary to a dictionary for display purposes."""
        return {
            "total_value": self.total_value,
            "stock_value": self.stock_value,
            "option_value": self.option_value,
            "cash_value": self.cash_value,
            "unknown_value": self.unknown_value,
            "pending_activity_value": self.pending_activity_value,
            "net_market_exposure": self.net_market_exposure,
            "portfolio_beta": self.portfolio_beta,
        }


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
