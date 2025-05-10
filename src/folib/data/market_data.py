"""
Market data provider for financial data.

This module provides a unified interface for fetching market data from FMP API.
It is a low-level component that should only be used by the ticker service,
not directly by other parts of the application.

The market data provider is responsible only for fetching data from external sources.
It does not implement any caching, as caching is handled by the ticker service.
"""

import logging
import os
from typing import Any

import fmpsdk

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """Low-level interface for accessing market data.

    Uses Financial Modeling Prep (FMP) API to fetch stock price and beta data.
    This class should only be used by the ticker service, not directly by other parts
    of the application.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the market data provider.

        Args:
            api_key: FMP API key. If None, will attempt to read from FMP_API_KEY environment variable.

        Raises:
            ValueError: If no API key is provided and FMP_API_KEY environment variable is not set.
        """
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY is required.")

    def __str__(self) -> str:
        """Return a string representation of the market data provider."""
        return "MarketDataProvider"

    def __repr__(self) -> str:
        """Return a string representation of the market data provider."""
        return f"MarketDataProvider(api_key='{self.api_key[:4]}...')"

    def _fetch_profile(self, ticker: str) -> dict[str, Any] | None:
        """Fetch company profile data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Company profile data dictionary or None if not found or error occurred.
        """
        ticker_upper = ticker.upper()
        logger.debug(f"Fetching FMP profile for {ticker_upper}")
        try:
            profile_data = fmpsdk.company_profile(
                apikey=self.api_key, symbol=ticker_upper
            )
            if profile_data:
                profile = profile_data[0]
                return profile
            else:
                logger.debug(f"No profile data found for {ticker_upper}")
                return None
        except Exception as e:
            logger.error(f"Error fetching FMP profile for {ticker_upper}: {e}")
            raise

    def get_price(self, ticker: str) -> float | None:
        """Get the current price for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Current stock price as float or None if not available.
        """
        ticker_upper = ticker.upper()
        profile = self._fetch_profile(ticker_upper)
        price = profile.get("price") if profile else None
        if price is not None:
            try:
                return float(price)
            except (ValueError, TypeError):
                logger.error(f"Invalid price value for {ticker_upper}: {price}")
                return None
        return None

    def get_beta(self, ticker: str) -> float | None:
        """Get the beta value for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Beta value as float or None if not available.
        """
        ticker_upper = ticker.upper()
        profile = self._fetch_profile(ticker_upper)
        beta = profile.get("beta") if profile else None
        if beta is not None:
            try:
                return float(beta)
            except (ValueError, TypeError):
                logger.error(f"Invalid beta value for {ticker_upper}: {beta}")
                return None
        return None

    def get_data_with_cache_option(
        self, ticker: str
    ) -> tuple[float | None, float | None]:
        """
        Get price and beta data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Tuple of (price, beta)
        """
        price = self.get_price(ticker)
        beta = self.get_beta(ticker)
        return price, beta


# Default instance (requires FMP_API_KEY env var)
try:
    market_data_provider = MarketDataProvider()
    logger.info("Default MarketDataProvider initialized successfully")
except ValueError as e:
    logger.error(f"Failed to initialize default MarketDataProvider: {e}")
    market_data_provider = None
