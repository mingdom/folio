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
- Supports multiple data providers (Yahoo Finance, Financial Modeling Prep) through a provider interface

Old Codebase References:
------------------------
- src/stockdata.py: Contains the DataFetcherInterface
- src/yfinance.py: Contains the YFinanceDataFetcher implementation
- src/folio/utils.py: Contains the get_beta function
- src/folio/marketdata.py: Contains the get_stock_price function

Potential Issues:
----------------
- Yahoo Finance API may have rate limits or change its interface
- FMP API requires an API key and has its own rate limits
- Beta calculation requires sufficient historical data
- Some tickers may not have data available
- Market data fetching can be slow
"""

import logging
import os
import re
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from .provider_fmp import FMPProvider
from .provider_yfinance import YFinanceProvider

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


def get_current_price(historical_data: pd.DataFrame) -> float:
    """
    Get the current price from historical data.

    This function extracts the latest closing price from historical data.
    It can be used by any provider that returns historical data in a DataFrame
    with a 'Close' column.

    Args:
        historical_data: DataFrame with historical price data (must have 'Close' column)

    Returns:
        The latest closing price

    Raises:
        ValueError: If the historical data is empty or doesn't have a 'Close' column
    """
    if historical_data.empty:
        raise ValueError("Historical data is empty")

    if "Close" not in historical_data.columns:
        raise ValueError("Historical data doesn't have a 'Close' column")

    return historical_data["Close"].iloc[-1]


def is_valid_stock_symbol(ticker: str) -> bool:
    """
    Check if a ticker symbol is likely a valid stock symbol.

    This function uses a simple regex pattern to check if a ticker symbol follows
    common stock symbol patterns. It's designed to filter out obviously invalid
    symbols before sending them to provider APIs.

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


def calculate_beta_from_history(
    stock_data: pd.DataFrame,
    market_data: pd.DataFrame,
    cache_instance: Any | None = None,
    ticker: str | None = None,
) -> float | None:
    """
    Calculate beta from historical stock and market data.

    Beta measures the volatility of a security in relation to the overall market.
    A beta of 1 indicates the security's price moves with the market.
    A beta less than 1 means the security is less volatile than the market.
    A beta greater than 1 indicates the security is more volatile than the market.

    Args:
        stock_data: DataFrame with historical price data for the stock (must have 'Close' column)
        market_data: DataFrame with historical price data for the market index (must have 'Close' column)
        cache_instance: Optional DataCache instance for caching the result
        ticker: Optional ticker symbol (required if cache_instance is provided)

    Returns:
        The calculated beta value, or None if beta cannot be calculated
        (e.g., insufficient data points or calculation errors)

    Raises:
        ValueError: If market variance calculation results in NaN
    """
    # Calculate returns
    stock_returns = stock_data["Close"].pct_change(fill_method=None).dropna()
    market_returns = market_data["Close"].pct_change(fill_method=None).dropna()

    # Align data by index
    aligned_stock, aligned_market = stock_returns.align(market_returns, join="inner")

    if aligned_stock.empty or len(aligned_stock) < 2:
        logger.debug(
            "Insufficient overlapping data points, cannot calculate meaningful beta"
        )
        return None

    # Calculate beta components
    market_variance = aligned_market.var()
    covariance = aligned_stock.cov(aligned_market)

    if pd.isna(market_variance):
        raise ValueError("Market variance calculation resulted in NaN")

    if pd.isna(covariance):
        logger.warning("Covariance calculation resulted in NaN")
        return None

    beta = covariance / market_variance

    # Cache the calculated beta if a cache instance is provided
    if cache_instance and ticker:
        cache_path = cache_instance.get_beta_cache_path(ticker)
        cache_instance.write_value_to_cache(beta, cache_path)

    return beta


class StockOracle:
    """
    Central service for accessing market data.

    This class provides a unified interface for accessing market data
    from various sources. It is implemented as a Singleton to ensure
    only one instance exists throughout the application.

    Usage:
        # Using default YFinance provider
        oracle = StockOracle.get_instance()
        price = oracle.get_price("AAPL")

        # Using FMP provider
        oracle = StockOracle.get_instance(provider_name="fmp", fmp_api_key="your_api_key")
        price = oracle.get_price("AAPL")
    """

    # Singleton instance
    _instance = None

    # Available providers
    PROVIDER_YFINANCE = "yfinance"
    PROVIDER_FMP = "fmp"

    @classmethod
    def get_instance(
        cls, provider_name=None, fmp_api_key=None, cache_dir=None, cache_ttl=None
    ):
        """
        Get the singleton instance of StockOracle.

        Args:
            provider_name: Name of the market data provider to use ("yfinance" or "fmp")
                           If None, will use the DATA_SOURCE environment variable or default to "yfinance"
            fmp_api_key: API key for FMP provider (required if provider_name is "fmp")
                         If None, will use the FMP_API_KEY environment variable
            cache_dir: Directory to store cached data (default: .cache_yf or .cache_fmp based on provider)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)

        Returns:
            The singleton StockOracle instance

        Raises:
            ValueError: If provider_name is "fmp" but no API key is provided
        """
        # If no instance exists, create one
        if cls._instance is None:
            # Get provider name from arguments or environment variable
            if provider_name is None:
                provider_name = os.environ.get("DATA_SOURCE", "yfinance").lower()

            # Get FMP API key from arguments or environment variable
            if fmp_api_key is None and provider_name == "fmp":
                fmp_api_key = os.environ.get("FMP_API_KEY")

            # Create the instance
            cls._instance = cls(
                provider_name=provider_name,
                fmp_api_key=fmp_api_key,
                cache_dir=cache_dir,
                cache_ttl=cache_ttl,
            )

        return cls._instance

    def __init__(
        self, provider_name="yfinance", fmp_api_key=None, cache_dir=None, cache_ttl=None
    ):
        """
        Initialize the StockOracle.

        Args:
            provider_name: Name of the market data provider to use ("yfinance" or "fmp")
            fmp_api_key: API key for FMP provider (required if provider_name is "fmp")
            cache_dir: Directory to store cached data (default: .cache_yf or .cache_fmp based on provider)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)

        Note:
            This should not be called directly. Use StockOracle.get_instance() instead.

        Raises:
            ValueError: If provider_name is "fmp" but no API key is provided
            ValueError: If provider_name is not recognized
        """
        # Check if an instance already exists to enforce singleton pattern
        if StockOracle._instance is not None:
            logger.warning(
                "StockOracle instance already exists. Use StockOracle.get_instance() instead."
            )

        # Validate provider name
        if provider_name not in [self.PROVIDER_YFINANCE, self.PROVIDER_FMP]:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Validate FMP API key if FMP provider is selected
        if provider_name == self.PROVIDER_FMP and not fmp_api_key:
            raise ValueError("API key is required for FMP provider")

        # Set default cache directory based on provider
        if cache_dir is None:
            # Special case for Hugging Face Spaces
            if (
                os.environ.get("HF_SPACE") == "1"
                or os.environ.get("SPACE_ID") is not None
            ):
                cache_dir = f"/tmp/cache_{provider_name}"
            else:
                cache_dir = f".cache_{provider_name}"

        # Set cache TTL (default: 1 day)
        cache_ttl = 86400 if cache_ttl is None else cache_ttl

        # Initialize the appropriate provider
        if provider_name == self.PROVIDER_YFINANCE:
            self.provider = YFinanceProvider(cache_dir=cache_dir, cache_ttl=cache_ttl)
        elif provider_name == self.PROVIDER_FMP:
            self.provider = FMPProvider(
                api_key=fmp_api_key, cache_dir=cache_dir, cache_ttl=cache_ttl
            )

        # Store provider name for reference
        self.provider_name = provider_name

        # Store cache directory and TTL for reference
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl

        logger.info(f"Initialized StockOracle with {provider_name} provider")

    def get_price(self, ticker: str) -> float:
        """
        Get the current price for a ticker.

        This method fetches the latest closing price for the given ticker
        using the selected market data provider.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price

        Raises:
            ValueError: If the ticker is invalid or no price data is available
        """
        # Validate ticker
        if not is_valid_stock_symbol(ticker):
            raise ValueError(f"Invalid stock symbol format: {ticker}")

        # Get historical data for the most recent day
        historical_data = self.get_historical_data(ticker, period="1d")

        # Extract the current price
        return get_current_price(historical_data)

    def get_beta(self, ticker: str) -> float | None:
        """
        Get the beta for a ticker.

        This method first tries to get beta directly from the provider.
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
        # Validate ticker
        if not is_valid_stock_symbol(ticker):
            logger.warning(f"Invalid stock symbol format: {ticker}")
            return None

        # Check cache first
        from .cache import DataCache

        cache = getattr(self.provider, "cache", None)
        if cache and isinstance(cache, DataCache):
            cache_path = cache.get_beta_cache_path(ticker)
            beta = cache.read_value_from_cache(cache_path)
            if beta is not None:
                return beta

        # Try to get beta directly from the provider
        beta = self.provider.try_get_beta_from_provider(ticker)
        if beta is not None:
            # Cache the result if possible
            if cache and isinstance(cache, DataCache):
                cache.write_value_to_cache(beta, cache_path)
            return beta

        # If provider beta retrieval failed, calculate it manually
        logger.debug(f"Calculating beta manually for {ticker}")

        # Get historical data for the ticker and market index
        try:
            # Get the beta period and market index from the provider if available
            beta_period = getattr(self.provider, "beta_period", "3mo")
            market_index = getattr(self.provider, "market_index", "SPY")

            # Get historical data
            stock_data = self.get_historical_data(ticker, period=beta_period)
            market_data = self.get_historical_data(market_index, period=beta_period)

            # Calculate beta
            beta = calculate_beta_from_history(
                stock_data=stock_data,
                market_data=market_data,
                cache_instance=cache,
                ticker=ticker,
            )

            if beta is not None:
                logger.debug(f"Calculated beta of {beta:.2f} for {ticker}")
            return beta

        except Exception as e:
            logger.error(f"Error calculating beta for {ticker}: {e}")
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
        using the selected market data provider, with caching to improve performance
        and reduce API calls.

        Args:
            ticker: The ticker symbol
            period: Time period in provider format (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            interval: Data interval (e.g., "1d", "1wk", "1mo")

        Returns:
            DataFrame with historical price data (columns: Open, High, Low, Close, Volume)

        Raises:
            ValueError: If the ticker is empty
            ValueError: If the ticker doesn't appear to be a valid stock symbol
            ValueError: If no historical data is available
        """
        return self.provider.get_historical_data(ticker, period, interval)

    def is_valid_stock_symbol(self, ticker: str) -> bool:
        """
        Check if a ticker symbol is likely a valid stock symbol.

        This method uses a simple regex pattern to check if a ticker symbol follows
        common stock symbol patterns. It's designed to filter out obviously invalid
        symbols before sending them to the provider API.

        Args:
            ticker: The ticker symbol to check

        Returns:
            True if the ticker appears to be a valid stock symbol, False otherwise
        """
        return is_valid_stock_symbol(ticker)

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

        # Check common patterns for cash-like instruments in ticker
        cash_or_bond_patterns = [
            "MMKT",
            "CASH",
            "MONEY",
            "TREASURY",
            "GOVT",
            "GOV",
            "SPAXX",
            "FDRXX",
            "FZDXX",
            "FMPXX",
            "FZFXX",
            "FDIC",
            "BANK",
            "SGOV",
            "TLT",
            "USD",
        ]

        if any(pattern in ticker_upper for pattern in cash_or_bond_patterns):
            logger.debug(f"Identified {ticker} as cash-like based on ticker pattern")
            return True

        # Check for money market terms in description
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
                "MMKT",  # Money Market
            ]

            if any(term in description_upper for term in money_market_terms):
                logger.debug(f"Identified {ticker} as cash-like based on description")
                return True

        return False


# Get provider configuration from environment variables
DATA_SOURCE = os.environ.get("DATA_SOURCE", "yfinance").lower()
FMP_API_KEY = os.environ.get("FMP_API_KEY")

# Pre-initialized singleton instance for easier access
if DATA_SOURCE == "fmp" and FMP_API_KEY:
    logger.info("Using FMP provider from environment configuration")
    stockdata = StockOracle.get_instance(provider_name="fmp", fmp_api_key=FMP_API_KEY)
else:
    if DATA_SOURCE == "fmp" and not FMP_API_KEY:
        logger.warning(
            "FMP provider selected in environment but no API key provided, falling back to yfinance"
        )
    logger.info("Using YFinance provider")
    stockdata = StockOracle.get_instance()
