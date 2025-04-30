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
    def get_price(self, ticker: str) -> float:
        """
        Get the current price for a ticker.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price

        Raises:
            ValueError: If the ticker is invalid or no price data is available
        """
        pass

    @abstractmethod
    def get_beta(self, ticker: str) -> float | None:
        """
        Get the beta for a ticker.

        Beta measures the volatility of a security in relation to the overall market.
        A beta of 1 indicates the security's price moves with the market.
        A beta less than 1 means the security is less volatile than the market.
        A beta greater than 1 indicates the security is more volatile than the market.

        Args:
            ticker: The ticker symbol

        Returns:
            The beta value, or None if beta cannot be calculated
            (e.g., for invalid stock symbols, insufficient data points, or calculation errors)
        """
        pass

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

    @abstractmethod
    def is_valid_stock_symbol(self, ticker: str) -> bool:
        """
        Check if a ticker symbol is likely a valid stock symbol.

        Args:
            ticker: The ticker symbol to check

        Returns:
            True if the ticker appears to be a valid stock symbol, False otherwise
        """
        pass
