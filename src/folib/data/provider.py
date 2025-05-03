"""
Market data provider interface.

This module defines the base interface that all market data providers must implement.
It follows the Strategy pattern to allow for interchangeable data sources while
maintaining a consistent interface.
"""

import logging
from abc import ABC, abstractmethod

import pandas as pd

# Set up logging
logger = logging.getLogger(__name__)


class MarketDataProvider(ABC):
    """
    Interface for market data providers.

    All concrete market data providers must implement this interface to ensure
    consistent behavior across different data sources.
    """

    # Default period for beta calculations
    beta_period = "3mo"

    # Default market index for beta calculations
    market_index = "SPY"

    @abstractmethod
    def get_historical_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Get historical price data for a ticker.

        Args:
            ticker: The ticker symbol
            period: Time period in provider format (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            interval: Data interval (e.g., "1d", "1wk", "1mo")

        Returns:
            DataFrame with historical price data (columns: Open, High, Low, Close, Volume)

        Raises:
            ValueError: If the ticker is invalid or no historical data is available
        """
        pass

    def try_get_beta_from_provider(self, ticker: str) -> float | None:  # noqa: ARG002
        """
        Try to get beta directly from the provider's API.

        This method should be implemented by providers that can fetch beta directly.
        If not implemented or if the provider doesn't support direct beta retrieval,
        it should return None.

        Args:
            ticker: The ticker symbol

        Returns:
            The beta value from the provider, or None if not available
        """
        # Unused argument is intentional - this is a base method that subclasses will override
        # with their own implementation that uses the ticker parameter
        return None
