"""
Yahoo Finance market data provider.

This module implements the MarketDataProvider interface using the Yahoo Finance API
via the yfinance package.
"""

import logging
import os
import re

import pandas as pd

import yfinance as yf

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
        from .cache import DataCache

        self.cache = DataCache(cache_dir=cache_dir, cache_ttl=cache_ttl or 86400)

        # Store cache directory for reference
        self.cache_dir = cache_dir

    def get_price(self, ticker: str) -> float:
        """
        Get the current price for a ticker.

        This method fetches the latest closing price for the given ticker
        using the Yahoo Finance API.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price

        Raises:
            ValueError: If the ticker is invalid or no price data is available
        """
        from .stock import get_current_price

        historical_data = self.get_historical_data(ticker, period="1d")
        return get_current_price(historical_data)

    def _get_beta_yfinance(self, ticker: str) -> float | None:
        """
        Try to get beta directly from Yahoo Finance API.

        This internal method attempts to get the beta value directly from the
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

    def get_beta(self, ticker: str) -> float | None:
        """
        Get the beta for a ticker.

        This method first tries to get beta directly from Yahoo Finance.
        If that fails, it calculates the beta (systematic risk) for a given ticker
        by comparing its price movements to a market index (default: SPY) over a period
        of time (default: 3 months). Results are cached to improve performance.

        Beta measures the volatility of a security in relation to the overall market.
        A beta of 1 indicates the security's price moves with the market.
        A beta less than 1 means the security is less volatile than the market.
        A beta greater than 1 indicates the security is more volatile than the market.

        Args:
            ticker: The ticker symbol

        Returns:
            The calculated beta value, or None if beta cannot be calculated
            (e.g., for invalid stock symbols, insufficient data points, or calculation errors)

        Raises:
            ValueError: If market variance calculation results in NaN
        """
        # Only proceed if this is a valid stock symbol
        if not self.is_valid_stock_symbol(ticker):
            logger.warning(f"Invalid stock symbol format: {ticker}")
            return None

        # Check cache first
        cache_path = self.cache.get_beta_cache_path(ticker)
        beta = self.cache.read_value_from_cache(cache_path)
        if beta is not None:
            return beta

        # Try to get beta directly from Yahoo Finance
        beta = self._get_beta_yfinance(ticker)
        if not beta:
            # If Yahoo Finance beta retrieval failed, calculate it manually
            logger.debug(f"Calculating beta manually for {ticker}")

            # Import the utility function
            from .stock import calculate_beta_from_history

            # Get historical data for the ticker and market index
            stock_data = self.get_historical_data(ticker, period=self.beta_period)
            market_data = self.get_historical_data(
                self.market_index, period=self.beta_period
            )

            # Calculate beta using the utility function
            beta = calculate_beta_from_history(
                stock_data=stock_data,
                market_data=market_data,
                cache_instance=self.cache,
                ticker=ticker,
            )

        logger.debug(f"Calculated beta of {beta:.2f} for {ticker}")
        return beta

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
            return df

        # Fetch from yfinance
        logger.info(f"Fetching data for {ticker} from yfinance: {period}, {interval}")
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period=period, interval=interval)

        if df.empty:
            raise ValueError(f"No historical data available for {ticker}")

        # Save to cache
        self.cache.write_dataframe_to_cache(df, cache_path)

        return df

    def is_valid_stock_symbol(self, ticker: str) -> bool:
        """
        Check if a ticker symbol is likely a valid stock symbol.

        This method uses a simple regex pattern to check if a ticker symbol follows
        common stock symbol patterns. It's designed to filter out obviously invalid
        symbols before sending them to yfinance.

        Common stock symbol patterns:
        - 1-5 uppercase letters (most US stocks: AAPL, MSFT, GOOGL)
        - 1-5 uppercase letters with a period (some international stocks: BHP.AX)
        - 1-5 uppercase letters with a hyphen (some ETFs: SPY-X)
        - 1-5 uppercase letters followed by 1-3 uppercase letters after a period (ADRs: SONY.TO)

        Args:
            ticker: The ticker symbol to check

        Returns:
            True if the ticker appears to be a valid stock symbol, False otherwise
        """
        if not ticker:
            return False

        # Simple regex pattern for common stock symbols
        # This covers most US stocks, ETFs, and common international formats
        pattern = r"^[A-Z]{1,5}(\.[A-Z]{1,3}|-[A-Z]{1})?$"

        # Special case for fund symbols that often have numbers and special formats
        fund_pattern = r"^[A-Z]{1,5}[0-9X]{0,3}$"

        # Check if the ticker matches either pattern
        if re.match(pattern, ticker) or re.match(fund_pattern, ticker):
            return True

        # Log invalid symbols for debugging
        logger.debug(f"Symbol '{ticker}' does not match standard stock symbol patterns")
        return False
