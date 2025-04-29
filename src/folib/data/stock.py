"""
Market data access.

This module provides access to market data through the StockOracle class.
It serves as a central point for fetching stock prices, beta values, and historical data.

The StockOracle is implemented as a Singleton to ensure only one instance exists
throughout the application. Use StockOracle.get_instance() to get the singleton instance.

Example usage:
    oracle = StockOracle.get_instance()
    price = oracle.get_price("AAPL")
    beta = oracle.get_beta("MSFT")

Migration Plan Notes:
---------------------
This module is part of Phase 1 of the folib migration plan, focusing on Portfolio Loading E2E.
It consolidates market data functionality from src/stockdata.py and src/yfinance.py into a
cleaner, more maintainable design with a single entry point for all market data needs.

Key differences from the old implementation:
- Uses a Singleton StockOracle class instead of separate DataFetcherInterface and YFinanceDataFetcher
- Provides direct methods for common operations (get_price, get_beta) instead of generic fetch_data
- Simplifies the API by hiding implementation details
- Implements the Singleton pattern for consistent access throughout the application

Old Codebase References:
------------------------
- src/stockdata.py: Contains the DataFetcherInterface
- src/yfinance.py: Contains the YFinanceDataFetcher implementation
- src/folio/utils.py: Contains the get_beta function
- src/folio/marketdata.py: Contains the get_stock_price function

Potential Issues:
----------------
- Yahoo Finance API may have rate limits or change its interface
- Beta calculation requires sufficient historical data
- Some tickers may not have data available
- Market data fetching can be slow
"""

import logging
import os
import re
import time
from datetime import datetime

import pandas as pd
import pytz

import yfinance as yf

# Set up logging
logger = logging.getLogger(__name__)


class StockOracle:
    """
    Central service for accessing market data.

    This class provides a unified interface for accessing market data
    from various sources. It is implemented as a Singleton to ensure
    only one instance exists throughout the application.

    Usage:
        oracle = StockOracle.get_instance()
        price = oracle.get_price("AAPL")
    """

    # Singleton instance
    _instance = None

    # Default period for beta calculations (3 months provides more current market behavior)
    beta_period = "3mo"
    # Default market index for beta calculations
    market_index = "SPY"

    @classmethod
    def get_instance(cls, cache_dir=None, cache_ttl=None):
        """
        Get the singleton instance of StockOracle.

        Args:
            cache_dir: Directory to store cached data (default: auto-detected)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)

        Returns:
            The singleton StockOracle instance
        """
        if cls._instance is None:
            cls._instance = cls(cache_dir=cache_dir, cache_ttl=cache_ttl)
        return cls._instance

    def __init__(self, cache_dir=None, cache_ttl=None):
        """
        Initialize the StockOracle.

        Args:
            cache_dir: Directory to store cached data (default: auto-detected)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)

        Note:
            This should not be called directly. Use StockOracle.get_instance() instead.
        """
        # Check if an instance already exists to enforce singleton pattern
        if StockOracle._instance is not None:
            logger.warning(
                "StockOracle instance already exists. Use StockOracle.get_instance() instead."
            )

        # Set default cache directory based on environment
        # In Hugging Face Spaces, use /tmp for cache
        is_huggingface = (
            os.environ.get("HF_SPACE") == "1" or os.environ.get("SPACE_ID") is not None
        )

        if cache_dir is None:
            if is_huggingface:
                # Use /tmp directory for Hugging Face
                cache_dir = "/tmp/cache_yf"
            else:
                # Use local directory for other environments
                cache_dir = ".cache_yf"

        self.cache_dir = cache_dir

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Set cache TTL (default: 1 day)
        self.cache_ttl = 86400 if cache_ttl is None else cache_ttl

    def get_price(self, ticker: str) -> float:
        """
        Get the current price for a ticker.

        This method fetches the latest closing price for the given ticker
        using the Yahoo Finance API.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price
        """
        return self.get_historical_data(ticker, period="1d")["Close"].iloc[-1]

    def get_beta(self, ticker: str, description: str = "") -> float:
        """
        Get the beta for a ticker.

        This method calculates the beta (systematic risk) for a given ticker
        by comparing its price movements to a market index (default: SPY) over a period
        of time (default: 3 months). Results are cached to improve performance.

        Beta measures the volatility of a security in relation to the overall market.
        A beta of 1 indicates the security's price moves with the market.
        A beta less than 1 means the security is less volatile than the market.
        A beta greater than 1 indicates the security is more volatile than the market.

        Returns 0.0 when beta cannot be meaningfully calculated (e.g., for cash-like instruments,
        instruments with insufficient price history, or when market variance is near-zero).

        Args:
            ticker: The ticker symbol
            description: Description of the security, used to identify cash-like positions

        Returns:
            The calculated beta value, or 0.0 if beta cannot be meaningfully calculated

        Raises:
            ValueError: If market variance or covariance calculations result in NaN
            ValueError: If beta calculation results in NaN
            Any exceptions from get_historical_data() are propagated directly
        """
        # For cash-like instruments, return 0 without calculation
        if self.is_cash_like(ticker, description):
            logger.debug(f"Using default beta of 0.0 for cash-like position: {ticker}")
            return 0.0

        # Check cache first
        cached_beta, cache_success = self._read_beta_from_cache(ticker)
        if cache_success:
            return cached_beta

        # Calculate beta if not in cache or cache is invalid
        try:
            # Get historical data for the ticker and market index
            stock_data = self.get_historical_data(ticker, period=self.beta_period)
            market_data = self.get_historical_data(
                self.market_index, period=self.beta_period
            )

            # Calculate returns
            stock_returns = stock_data["Close"].pct_change(fill_method=None).dropna()
            market_returns = market_data["Close"].pct_change(fill_method=None).dropna()

            # Align data by index
            aligned_stock, aligned_market = stock_returns.align(
                market_returns, join="inner"
            )

            if aligned_stock.empty or len(aligned_stock) < 2:
                logger.debug(
                    f"Insufficient overlapping data points for {ticker}, cannot calculate meaningful beta"
                )
                return 0.0

            # Calculate beta components
            market_variance = aligned_market.var()
            covariance = aligned_stock.cov(aligned_market)

            if pd.isna(market_variance):
                raise ValueError(
                    f"Market variance calculation resulted in NaN for {ticker}"
                )

            if abs(market_variance) < 1e-12:
                logger.debug(
                    f"Market variance is near-zero for {ticker}, cannot calculate meaningful beta"
                )
                return 0.0

            if pd.isna(covariance):
                raise ValueError(f"Covariance calculation resulted in NaN for {ticker}")

            beta = covariance / market_variance
            if pd.isna(beta):
                raise ValueError(f"Beta calculation resulted in NaN for {ticker}")

            # Cache the calculated beta
            self._write_beta_to_cache(ticker, beta)

            logger.debug(f"Calculated beta of {beta:.2f} for {ticker}")
            return beta
        except Exception as e:
            logger.warning(f"Error calculating beta for {ticker}: {e}")
            # If we have a cached value, use it as fallback even if expired
            if os.path.exists(self._get_beta_cache_path(ticker)):
                try:
                    with open(self._get_beta_cache_path(ticker)) as f:
                        beta = float(f.read().strip())
                    logger.warning(
                        f"Using expired beta cache for {ticker} as fallback: {beta:.3f}"
                    )
                    return beta
                except Exception as cache_e:
                    logger.error(
                        f"Error reading expired beta cache for {ticker}: {cache_e}"
                    )
            # Re-raise the original exception
            raise

    def get_historical_data(
        self, ticker: str, period: str = "1y", interval: str = "1d"
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

        # Special case for cash-like positions
        if self.is_cash_like(ticker):
            # For cash-like positions, return a DataFrame with constant values
            logger.debug(
                f"Creating synthetic historical data for cash-like position: {ticker}"
            )
            dates = pd.date_range(end=pd.Timestamp.now(), periods=10)
            df = pd.DataFrame(
                {
                    "Open": [1.0] * 10,
                    "High": [1.0] * 10,
                    "Low": [1.0] * 10,
                    "Close": [1.0] * 10,
                    "Volume": [0] * 10,
                },
                index=dates,
            )
            return df

        # Check if the ticker appears to be a valid stock symbol
        if not self.is_valid_stock_symbol(ticker):
            raise ValueError(f"Invalid stock symbol format: {ticker}")

        # Check cache first
        cache_path = self._get_cache_path(ticker, period, interval)
        should_use, reason = self._should_use_cache(cache_path)

        if should_use:
            logger.info(f"Loading {ticker} data from cache: {reason}")
            try:
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)
            except Exception as e:
                logger.warning(f"Error reading cache for {ticker}: {e}")
                # Continue to fetch from API

        # Fetch from yfinance
        try:
            logger.info(f"Fetching data for {ticker} from Yahoo Finance")
            ticker_data = yf.Ticker(ticker)
            df = ticker_data.history(period=period, interval=interval)

            if df.empty:
                raise ValueError(f"No historical data available for {ticker}")

            # Save to cache
            df.to_csv(cache_path)

            return df
        except Exception as e:
            # Check if we have a cache file to use as fallback
            if os.path.exists(cache_path):
                logger.warning(f"Using expired cache for {ticker} as fallback: {e}")
                try:
                    return pd.read_csv(cache_path, index_col=0, parse_dates=True)
                except Exception as cache_e:
                    logger.error(f"Error reading cache for {ticker}: {cache_e}")
                    # Re-raise the original error with context
                    raise e from cache_e
            # No cache fallback, re-raise the original exception
            raise

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

    def _get_cache_path(self, ticker, period, interval="1d"):
        """
        Get the path to the cache file for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Time period
            interval: Data interval

        Returns:
            Path to cache file
        """
        return os.path.join(self.cache_dir, f"{ticker}_{period}_{interval}.csv")

    def _get_beta_cache_path(self, ticker):
        """
        Get the path to the beta cache file for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Path to beta cache file
        """
        return os.path.join(self.cache_dir, f"{ticker}_beta.txt")

    def _is_cache_expired(self, cache_timestamp):
        """
        Determine if cache should be considered expired based on market hours.
        Cache expires daily at 2PM Pacific time to ensure we use EOD pricing.

        Args:
            cache_timestamp: The timestamp of when the cache was created/modified

        Returns:
            True if cache should be considered expired, False otherwise
        """
        # Convert cache timestamp to datetime
        cache_time = datetime.fromtimestamp(cache_timestamp)

        # Get current time in Pacific timezone
        pacific_tz = pytz.timezone("US/Pacific")
        now = datetime.now(pacific_tz)

        # Convert cache time to Pacific timezone (assuming it's in local time)
        cache_time_pacific = pacific_tz.localize(cache_time)

        # Check if cache is from a previous day
        if cache_time_pacific.date() < now.date():
            # If it's after 2PM Pacific, cache from previous days is expired
            if now.hour >= 14:  # 2PM = 14:00 in 24-hour format
                return True
            # If it's before 2PM, cache is still valid
            return False

        # If cache is from today and it's after 2PM, check if cache was created before 2PM
        if now.hour >= 14 and cache_time_pacific.hour < 14:
            return True

        # In all other cases, cache is still valid
        return False

    def _should_use_cache(self, cache_path):
        """
        Determine if cache should be used based on both TTL and market hours.

        Args:
            cache_path: Path to the cache file

        Returns:
            tuple: (should_use, reason)
                - should_use: True if cache should be used, False otherwise
                - reason: Reason for the decision (for logging)
        """
        if not os.path.exists(cache_path):
            return False, "Cache file does not exist"

        # Get cache modification time
        cache_mtime = os.path.getmtime(cache_path)

        # Check TTL
        cache_age = time.time() - cache_mtime
        if cache_age >= self.cache_ttl:
            return (
                False,
                f"Cache TTL expired (age: {cache_age:.0f}s > TTL: {self.cache_ttl}s)",
            )

        # Check market hours
        if self._is_cache_expired(cache_mtime):
            return False, "Cache expired due to market hours (2PM Pacific cutoff)"

        # Cache is valid
        return True, f"Cache is valid (age: {cache_age:.0f}s)"

    def _read_beta_from_cache(self, ticker):
        """
        Read beta value from cache.

        Args:
            ticker: Stock ticker symbol

        Returns:
            tuple: (beta, success)
                - beta: The cached beta value or None
                - success: True if cache read was successful, False otherwise
        """
        cache_path = self._get_beta_cache_path(ticker)
        should_use, reason = self._should_use_cache(cache_path)

        if should_use:
            try:
                with open(cache_path) as f:
                    beta = float(f.read().strip())
                logger.debug(f"Loaded beta for {ticker} from cache: {beta:.3f}")
                return beta, True
            except Exception as e:
                logger.warning(f"Error reading beta cache for {ticker}: {e}")

        return None, False

    def _write_beta_to_cache(self, ticker, beta):
        """
        Write beta value to cache.

        Args:
            ticker: Stock ticker symbol
            beta: Beta value to cache
        """
        cache_path = self._get_beta_cache_path(ticker)
        try:
            with open(cache_path, "w") as f:
                f.write(f"{beta:.6f}")
            logger.debug(f"Cached beta for {ticker}: {beta:.3f}")
        except Exception as e:
            logger.warning(f"Error writing beta cache for {ticker}: {e}")

    def is_cash_like(
        self, ticker: str, description: str = "", beta: float | None = None
    ) -> bool:
        """
        Determine if a position should be considered cash or cash-like.

        This function checks if a position is likely cash or a cash-like instrument
        based on its ticker, beta, and description. Cash-like instruments include
        money market funds, short-term bond funds, and other low-volatility assets.

        Args:
            ticker: The ticker symbol to check
            description: The description of the security (optional)
            beta: The calculated beta value for the position (optional)

        Returns:
            True if the position is likely cash or cash-like, False otherwise
        """
        if not ticker:
            return False

        # Convert to uppercase for case-insensitive matching
        ticker_upper = ticker.upper()
        description_upper = description.upper() if description else ""

        # 1. Check if it's a cash symbol
        if ticker_upper in ["CASH", "USD"]:
            logger.debug(f"Identified {ticker} as cash based on symbol")
            return True

        # 2. Check common patterns for cash-like instruments in ticker
        cash_patterns = [
            "MM",
            "CASH",
            "MONEY",
            "TREASURY",
            "GOVT",
            "GOV",
            "SPAXX",
            "FDRXX",
            "SPRXX",
            "FZFXX",
            "FDIC",
            "BANK",
        ]

        if any(pattern in ticker_upper for pattern in cash_patterns):
            logger.debug(f"Identified {ticker} as cash-like based on ticker pattern")
            return True

        # 3. Check for money market terms in description
        if description:
            money_market_terms = [
                "MONEY MARKET",
                "CASH RESERVES",
                "TREASURY ONLY",
                "GOVERNMENT LIQUIDITY",
                "CASH MANAGEMENT",
                "LIQUID ASSETS",
                "CASH EQUIVALENT",
                "TREASURY FUND",
                "LIQUIDITY FUND",
                "CASH FUND",
                "RESERVE FUND",
            ]

            if any(term in description_upper for term in money_market_terms):
                logger.debug(f"Identified {ticker} as cash-like based on description")
                return True

        # 4. Check for very low beta (near zero)
        if beta is not None and abs(beta) < 0.1:
            logger.debug(f"Identified {ticker} as cash-like based on low beta: {beta}")
            return True

        return False


# Pre-initialized singleton instance for easier access
stockdata = StockOracle.get_instance()
