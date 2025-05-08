"""
Market data provider for financial data.

This module provides a unified interface for fetching market data from FMP API.
It includes both in-session and persistent caching to minimize redundant API calls.
"""

import logging
import os
from typing import Any

import fmpsdk

from src.folib.data.cache import cached, clear_cache, log_cache_stats

logger = logging.getLogger(__name__)

# Cache TTLs in seconds
PRICE_TTL = 3600  # 1 hour
BETA_TTL = 604800  # 1 week (7 days)
PROFILE_TTL = 2592000  # 1 month (30 days)


class MarketDataProvider:
    """Primary interface for accessing market data.

    Uses Financial Modeling Prep (FMP) API to fetch stock price and beta data.
    Implements both in-session and persistent caching to minimize redundant API calls.
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
        # In-session cache: {ticker: {price: value, beta: value, profile: raw_data}}
        self._session_cache: dict[str, dict[str, Any]] = {}

    def __str__(self) -> str:
        """Return a string representation of the market data provider."""
        return "MarketDataProvider"

    def __repr__(self) -> str:
        """Return a string representation of the market data provider."""
        return f"MarketDataProvider(api_key='{self.api_key[:4]}...')"

    @cached(ttl=PROFILE_TTL, key_prefix="profile")
    def _fetch_profile(
        self, ticker: str, skip_cache: bool = False
    ) -> dict[str, Any] | None:
        """Fetch company profile data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            skip_cache: If True, bypass the cache and fetch fresh data.

        Returns:
            Company profile data dictionary or None if not found or error occurred.
        """
        ticker_upper = ticker.upper()
        if (
            ticker_upper not in self._session_cache
            or "profile" not in self._session_cache[ticker_upper]
        ):
            logger.debug(f"Fetching FMP profile for {ticker_upper}")
            try:
                profile_data = fmpsdk.company_profile(
                    apikey=self.api_key, symbol=ticker_upper
                )
                if profile_data:
                    profile = profile_data[0]
                    self._session_cache.setdefault(ticker_upper, {})["profile"] = (
                        profile
                    )
                    self._session_cache[ticker_upper]["price"] = profile.get("price")
                    self._session_cache[ticker_upper]["beta"] = profile.get("beta")
                    return profile
                else:
                    logger.warning(f"No profile data found for {ticker_upper}")
                    self._session_cache.setdefault(ticker_upper, {})["profile"] = None
                    return None
            except Exception as e:
                logger.error(f"Error fetching FMP profile for {ticker_upper}: {e}")
                self._session_cache.setdefault(ticker_upper, {})["profile"] = None
                raise
        return self._session_cache[ticker_upper].get("profile")

    @cached(ttl=PRICE_TTL, key_prefix="price")
    def get_price(self, ticker: str, skip_cache: bool = False) -> float | None:
        """Get the current price for a stock ticker.

        Args:
            ticker: Stock ticker symbol.
            skip_cache: If True, bypass the cache and fetch fresh data.

        Returns:
            Current stock price as float or None if not available.
        """
        ticker_upper = ticker.upper()
        if (
            not skip_cache
            and ticker_upper in self._session_cache
            and self._session_cache[ticker_upper].get("price") is not None
        ):
            return self._session_cache[ticker_upper]["price"]
        profile = self._fetch_profile(ticker, skip_cache=skip_cache)
        price = profile.get("price") if profile else None
        if price is not None:
            try:
                return float(price)
            except (ValueError, TypeError):
                logger.error(f"Invalid price value for {ticker_upper}: {price}")
                return None
        return None

    @cached(ttl=BETA_TTL, key_prefix="beta")
    def get_beta(self, ticker: str, skip_cache: bool = False) -> float | None:
        """Get the beta value for a stock ticker.

        Args:
            ticker: Stock ticker symbol.
            skip_cache: If True, bypass the cache and fetch fresh data.

        Returns:
            Beta value as float or None if not available.
        """
        ticker_upper = ticker.upper()
        if (
            not skip_cache
            and ticker_upper in self._session_cache
            and self._session_cache[ticker_upper].get("beta") is not None
        ):
            return self._session_cache[ticker_upper]["beta"]
        profile = self._fetch_profile(ticker, skip_cache=skip_cache)
        beta = profile.get("beta") if profile else None
        if beta is not None:
            try:
                return float(beta)
            except (ValueError, TypeError):
                logger.error(f"Invalid beta value for {ticker_upper}: {beta}")
                return None
        return None

    def clear_session_cache(self) -> None:
        """Clear the in-session cache."""
        self._session_cache.clear()
        logger.info("In-session market data cache cleared.")

    def clear_all_cache(self, backup: bool = False) -> None:
        """
        Clear both in-session and disk cache.

        Args:
            backup: If True, backs up the cache before clearing it.
        """
        self.clear_session_cache()
        clear_cache(backup=backup)
        logger.info("All caches cleared (in-session and disk).")

    def log_cache_statistics(self, aggregate: bool = True) -> None:
        """
        Log cache hit/miss statistics.

        Args:
            aggregate: If True, log all statistics in a single message.
                      If False, log overall statistics and detailed statistics separately.
        """
        log_cache_stats(aggregate=aggregate)

    def get_data_with_cache_option(
        self, ticker: str, skip_cache: bool = False
    ) -> tuple[float | None, float | None]:
        """
        Get price and beta data for a ticker with option to skip cache.

        Args:
            ticker: Stock ticker symbol
            skip_cache: If True, bypass the cache and fetch fresh data

        Returns:
            Tuple of (price, beta)
        """
        price = self.get_price(ticker, skip_cache=skip_cache)
        beta = self.get_beta(ticker, skip_cache=skip_cache)
        return price, beta


# Default instance (requires FMP_API_KEY env var)
try:
    market_data_provider = MarketDataProvider()
    logger.info("Default MarketDataProvider initialized successfully")
except ValueError as e:
    logger.error(f"Failed to initialize default MarketDataProvider: {e}")
    market_data_provider = None
