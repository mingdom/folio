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

import pandas as pd

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
            cache_dir: Directory to store cached data (default: .cache_yf)
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
            cache_dir: Directory to store cached data (default: .cache_yf)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)

        Note:
            This should not be called directly. Use StockOracle.get_instance() instead.
        """
        # Check if an instance already exists to enforce singleton pattern
        if StockOracle._instance is not None:
            logger.warning(
                "StockOracle instance already exists. Use StockOracle.get_instance() instead."
            )

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
        cache_path = self._get_beta_cache_path(ticker)
        if os.path.exists(cache_path) and not self._is_cache_expired(
            os.path.getmtime(cache_path)
        ):
            try:
                with open(cache_path) as f:
                    beta = float(f.read().strip())
                logger.debug(f"Loaded beta for {ticker} from cache: {beta:.3f}")
                return beta
            except Exception as e:
                logger.warning(f"Error reading beta cache for {ticker}: {e}")
                # Continue to calculate beta if cache read fails

        # Try to get beta directly from Yahoo Finance
        beta = self._get_beta_yfinance(ticker)
        if not beta:
            # If Yahoo Finance beta retrieval failed, calculate it manually
            logger.debug(f"Calculating beta manually for {ticker}")

            # Get historical data for the ticker and market index
            stock_data = self.get_historical_data(
                ticker, period=self.beta_period, skip_cash_check=True
            )
            market_data = self.get_historical_data(
                self.market_index, period=self.beta_period, skip_cash_check=True
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
                return None

            # Calculate beta components
            market_variance = aligned_market.var()
            covariance = aligned_stock.cov(aligned_market)

            if pd.isna(market_variance):
                raise ValueError(
                    f"Market variance calculation resulted in NaN for {ticker}"
                )

            if pd.isna(covariance):
                logger.warning(f"Covariance calculation resulted in NaN for {ticker}")
                return None

            beta = covariance / market_variance

        # Cache the calculated beta
        try:
            with open(cache_path, "w") as f:
                f.write(f"{beta:.6f}")
            logger.debug(f"Cached beta for {ticker}: {beta:.3f}")
        except Exception as e:
            logger.warning(f"Error writing beta cache for {ticker}: {e}")
            # Continue even if cache write fails

        logger.debug(f"Calculated beta of {beta:.2f} for {ticker}")
        return beta

    def get_historical_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        skip_cash_check: bool = False,
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
            skip_cash_check: If True, skip checking if the ticker is cash-like (to avoid circular dependencies)

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

        # Special case for cash-like positions, but only if not skipping the check
        if not skip_cash_check:
            # Check for obvious cash symbols without calling is_cash_like
            ticker_upper = ticker.upper()
            if ticker_upper in ["CASH", "USD"] or any(
                pattern in ticker_upper
                for pattern in [
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
                ]
            ):
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
        if os.path.exists(cache_path) and not self._is_cache_expired(
            os.path.getmtime(cache_path)
        ):
            try:
                logger.info(f"Loading {ticker} data from cache")
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)
            except Exception as e:
                logger.warning(f"Error reading cache for {ticker}: {e}")
                # Continue to fetch from API if cache read fails

        # Fetch from yfinance
        logger.info(f"Fetching data for {ticker} from Yahoo Finance")
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period=period, interval=interval)

        if df.empty:
            raise ValueError(f"No historical data available for {ticker}")

        # Save to cache
        try:
            df.to_csv(cache_path)
            logger.debug(f"Cached historical data for {ticker}")
        except Exception as e:
            logger.warning(f"Error writing cache for {ticker}: {e}")
            # Continue even if cache write fails

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
        Determine if cache should be considered expired based on TTL.

        Args:
            cache_timestamp: The timestamp of when the cache was created/modified

        Returns:
            True if cache should be considered expired, False otherwise
        """
        # Check TTL
        cache_age = time.time() - cache_timestamp
        return cache_age >= self.cache_ttl

    def is_cash_like(self, ticker: str, description: str = "") -> bool:
        """
        Determine if a position should be considered cash or cash-like.

        This function checks if a position is likely cash or a cash-like instrument
        based on its ticker, description, and beta (calculated internally if needed).
        Cash-like instruments include money market funds, short-term bond funds,
        and other low-volatility assets.

        Args:
            ticker: The ticker symbol to check
            description: The description of the security (optional)

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

        # 4. Check for very low beta (near zero), but only for valid stock symbols
        if self.is_valid_stock_symbol(ticker):
            beta = self.get_beta(ticker)
            if beta is not None and abs(beta) < 0.1:
                logger.debug(
                    f"Identified {ticker} as cash-like based on low beta: {beta}"
                )
                return True

        return False


# Pre-initialized singleton instance for easier access
stockdata = StockOracle.get_instance()
