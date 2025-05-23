"""
Ticker service for the Folib library.

This module provides a service for accessing ticker-related data,
including prices and beta values.

Caching Strategy:
- The ticker service is the primary caching layer for all ticker-related data
- It uses both in-memory caching (self._ticker_data) and persistent caching (@cached decorator)
- The market data provider no longer has its own persistent cache to avoid redundancy
- TTLs are configured to balance data freshness with performance
- Uses cachetools for improved method caching with better key generation
"""

import logging
from datetime import datetime, timedelta

from ..data.cache import cached
from ..data.cache import clear_cache as clear_persistent_cache
from ..data.market_data import MarketDataProvider, market_data_provider
from ..data.ticker_data import TickerData

# Set up logging
logger = logging.getLogger(__name__)


class CacheTTL:
    BETA = 7 * 86400  # 7 days
    PRICE = 3 * 3600  # 3h
    TICKER_DATA = 3 * 3600  # 3h


class TickerService:
    """Service for accessing ticker data."""

    def __init__(self, market_data_provider: MarketDataProvider = market_data_provider):
        """
        Initialize the ticker service.

        Args:
            market_data_provider: The market data provider to use for fetching data.
                                 Defaults to the global market_data_provider instance.
        """
        self._market_data_provider = market_data_provider
        self._ticker_data: dict[str, TickerData] = {}
        self._price_cache_duration = timedelta(
            minutes=15
        )  # Cache prices for 15 minutes
        self._beta_cache_duration = timedelta(days=1)  # Cache beta values for 1 day

    @cached(ttl=CacheTTL.TICKER_DATA, key_prefix="ticker_data")
    def get_ticker_data(self, ticker: str) -> TickerData:
        """
        Get data for a ticker, fetching if necessary.

        Args:
            ticker: The ticker symbol

        Returns:
            TickerData object containing all available data for the ticker
        """
        ticker = ticker.upper()  # Normalize ticker to uppercase
        logger.debug(f"Getting ticker data for: {ticker}")

        # Check if we already have data for this ticker in memory
        if ticker in self._ticker_data:
            # Check if the data is still valid
            ticker_data = self._ticker_data[ticker]
            if self._is_data_valid(ticker_data):
                logger.debug(f"Using in-memory cache for ticker: {ticker}")
                return ticker_data

        # Fetch new data
        logger.debug(f"Fetching new data for ticker: {ticker}")
        return self._fetch_ticker_data(ticker)

    @cached(ttl=CacheTTL.PRICE, key_prefix="ticker_price")  # 15 minutes TTL
    def get_price(self, ticker: str) -> float:
        """
        Get the price for a ticker.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price, or an appropriate default value
        """
        logger.debug(f"Getting price for ticker: {ticker}")
        ticker_data = self.get_ticker_data(ticker)
        return ticker_data.effective_price

    @cached(ttl=CacheTTL.BETA, key_prefix="ticker_beta")
    def get_beta(self, ticker: str) -> float:
        """
        Get the beta for a ticker.

        Args:
            ticker: The ticker symbol

        Returns:
            The beta value, or an appropriate default value
        """
        logger.debug(f"Getting beta for ticker: {ticker}")
        ticker_data = self.get_ticker_data(ticker)
        return ticker_data.effective_beta

    def prefetch_tickers(self, tickers: list[str]) -> None:
        """
        Prefetch data for multiple tickers.

        Args:
            tickers: List of ticker symbols to prefetch
        """
        for ticker in tickers:
            try:
                self.get_ticker_data(ticker)
            except Exception as e:
                logger.warning(f"Failed to prefetch data for {ticker}: {e}")

    def clear_cache(self, backup: bool = False) -> None:
        """
        Clear both in-memory and persistent ticker data caches.

        Args:
            backup: If True, backs up the persistent cache before clearing it.
        """
        # Clear in-memory cache
        self._ticker_data = {}
        logger.info("Ticker data in-memory cache cleared")

        # Clear persistent cache
        clear_persistent_cache(backup=backup)
        logger.info("Ticker data persistent cache cleared")

    def _fetch_ticker_data(self, ticker: str) -> TickerData:
        """
        Fetch data for a ticker from the market data provider.

        Args:
            ticker: The ticker symbol

        Returns:
            TickerData object with the fetched data
        """
        logger.debug(f"Fetching data for ticker: {ticker}")

        # Get existing data if available
        existing_data = self._ticker_data.get(ticker)

        # Fetch price if needed
        price = None
        try:
            price = self._market_data_provider.get_price(ticker)
            logger.debug(f"Fetched price for {ticker}: {price}")
        except Exception as e:
            logger.warning(f"Failed to fetch price for {ticker}: {e}")
            # Use existing price if available
            if existing_data and existing_data.price is not None:
                price = existing_data.price

        # Fetch beta if needed
        beta = None
        try:
            beta = self._market_data_provider.get_beta(ticker)
            logger.debug(f"Fetched beta for {ticker}: {beta}")
        except Exception as e:
            logger.warning(f"Failed to fetch beta for {ticker}: {e}")
            # Use existing beta if available
            if existing_data and existing_data.beta is not None:
                beta = existing_data.beta

        # Get description if available from existing data
        description = None
        if existing_data and existing_data.description:
            description = existing_data.description

        # Create ticker data
        ticker_data = TickerData(
            ticker=ticker,
            price=price,
            beta=beta,
            last_updated=datetime.now(),
            description=description,
        )

        # Store in cache
        self._ticker_data[ticker] = ticker_data

        return ticker_data

    def _is_data_valid(self, ticker_data: TickerData) -> bool:
        """
        Check if the ticker data is still valid.

        Args:
            ticker_data: The ticker data to check

        Returns:
            True if the data is still valid, False otherwise
        """
        if ticker_data.last_updated is None:
            return False

        now = datetime.now()

        # Check if price is valid
        if ticker_data.price is not None:
            price_expiry = ticker_data.last_updated + self._price_cache_duration
            if now > price_expiry:
                return False

        # Check if beta is valid
        if ticker_data.beta is not None:
            beta_expiry = ticker_data.last_updated + self._beta_cache_duration
            if now > beta_expiry:
                return False

        # We no longer store company profiles - YAGNI

        return True


# Create a global instance for convenience
ticker_service = TickerService()
