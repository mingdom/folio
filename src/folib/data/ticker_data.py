"""
Ticker data structures for the Folib library.

This module contains data structures for representing ticker-related data,
including prices, beta values, and company profiles.
"""

from dataclasses import dataclass
from datetime import datetime

from src.folio.cash_detection import is_cash_or_short_term


@dataclass(frozen=True)
class TickerData:
    """Data associated with a ticker symbol."""

    ticker: str
    price: float | None = None
    beta: float | None = None
    last_updated: datetime | None = None
    description: str | None = None

    @property
    def is_cash_like(self) -> bool:
        """Determine if this ticker represents a cash-like instrument."""
        return is_cash_or_short_term(self.ticker, description=self.description)

    @property
    def effective_beta(self) -> float:
        """
        Get the effective beta value, handling special cases.

        Returns:
            - 0.0 for cash-like instruments
            - The stored beta value if available
            - 1.0 as a default fallback
        """
        if self.is_cash_like:
            return 0.0
        return self.beta if self.beta is not None else 1.0

    @property
    def effective_price(self) -> float:
        """
        Get the effective price, handling special cases.

        Returns:
            - The stored price if available
            - 1.0 for cash-like instruments with no price
            - 0.0 as a default fallback
        """
        if self.price is not None:
            return self.price
        if self.is_cash_like:
            return 1.0
        return 0.0
