"""
Yahoo Finance market data provider.

This module implements the MarketDataProvider interface using the yfinance package,
providing access to stock prices, historical data, and beta values from Yahoo Finance.
"""

import logging
import os

import pandas as pd

import yfinance as yf

from .cache import DataCache
from .provider import MarketDataProvider

# Set up logging
logger = logging.getLogger(__name__)


class YFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance implementation of market data provider.

    This class provides access to market data from Yahoo Finance using the yfinance package.
    It implements caching to improve performance and reduce API calls.
    """

    # Default period for beta calculations (3 months provides more current market behavior)
    beta_period = "3mo"

    # Default market index for beta calculations
    market_index = "SPY"

    def __init__(self, cache_dir=None, cache_ttl=None):
        """
        Initialize the YFinanceProvider.

        Args:
            cache_dir: Directory to store cached data (default: .cache_yf)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)
        """
        # Set default cache directory
        # Special case for Hugging Face Spaces
        if cache_dir is None:
            if (
                os.environ.get("HF_SPACE") == "1"
                or os.environ.get("SPACE_ID") is not None
            ):
                cache_dir = "/tmp/cache_yf"
            else:
                cache_dir = ".cache_yf"

        # Initialize the cache manager

        self.cache = DataCache(cache_dir=cache_dir, cache_ttl=cache_ttl or 86400)

        # Store cache directory for reference
        self.cache_dir = cache_dir

    def try_get_beta_from_provider(self, ticker: str) -> float | None:
        """
        Try to get beta directly from Yahoo Finance API.

        This method attempts to get the beta value directly from the
        ticker's info property in yfinance, which is more efficient than
        calculating it manually.

        Args:
            ticker: The ticker symbol

        Returns:
            The beta value from Yahoo Finance, or None if not available
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            ticker_info = ticker_obj.info

            if "beta" in ticker_info and ticker_info["beta"] is not None:
                beta_value = float(ticker_info["beta"])
                logger.debug(
                    f"Got beta of {beta_value:.2f} for {ticker} directly from Yahoo Finance"
                )
                return beta_value
            else:
                logger.debug(f"Beta not available in Yahoo Finance info for {ticker}")
                return None
        except Exception as e:
            logger.debug(f"Error getting beta from Yahoo Finance for {ticker}: {e}")
            return None

    def get_historical_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Get historical price data for a ticker.

        This method fetches historical price data for the given ticker
        using the Yahoo Finance API, with caching to improve performance
        and reduce API calls.

        Args:
            ticker: The ticker symbol
            period: Time period in yfinance format: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
            interval: Data interval ("1d", "1wk", "1mo", etc.)

        Returns:
            DataFrame with historical price data (columns: Open, High, Low, Close, Volume)

        Raises:
            ValueError: If the ticker is empty
            ValueError: If the ticker doesn't appear to be a valid stock symbol
            ValueError: If no historical data is available
            Any exceptions from yfinance are propagated directly
        """
        if not ticker:
            raise ValueError("Ticker cannot be empty")

        # Check if the ticker appears to be a valid stock symbol
        if not self.is_valid_stock_symbol(ticker):
            raise ValueError(f"Invalid stock symbol format: {ticker}")

        # Check cache first
        cache_path = self.cache.get_cache_path(ticker, period, interval)
        df = self.cache.read_dataframe_from_cache(cache_path)
        if df is not None:
            logger.debug(
                f"Using cached historical data for {ticker} ({period}, {interval})"
            )
            return df
        else:
            logger.debug(f"No valid cache found for {ticker} historical data")

        # Fetch from yfinance
        logger.debug(f"Fetching data for {ticker} from yfinance: {period}, {interval}")
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period=period, interval=interval)

        if df.empty:
            raise ValueError(f"No historical data available for {ticker}")

        # Save to cache
        self.cache.write_dataframe_to_cache(df, cache_path)
        logger.debug(f"Cached historical data for {ticker} ({period}, {interval})")

        return df
