"""
Yahoo Finance data fetcher using yfinance.

This module provides a YFinanceDataFetcher class that mirrors the functionality
of the DataFetcher class in src/v2/data_fetcher.py but uses yfinance as the data source.
"""

import logging
import os

import pandas as pd

import yfinance as yf
from src.stockdata import DataFetcherInterface

logger = logging.getLogger(__name__)


class YFinanceDataFetcher(DataFetcherInterface):
    """Class to fetch stock data from Yahoo Finance API using yfinance"""

    # Default period for beta calculations (3 months provides more current market behavior)
    beta_period = "3m"

    def __init__(self, cache_dir=".cache_yf", cache_ttl=None):
        """
        Initialize the YFinanceDataFetcher.

        Args:
            cache_dir (str): Directory to store cached data
            cache_ttl (int, optional): Cache TTL in seconds. If None, uses config or default.
        """
        self.cache_dir = cache_dir

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Get cache TTL from config or use default (1 day)
        if cache_ttl is None:
            try:
                from src.v2.config import config

                self.cache_ttl = config.get("app.cache.ttl", 86400)
            except ImportError:
                self.cache_ttl = 86400
        else:
            self.cache_ttl = cache_ttl

    def fetch_data(self, ticker, period="3m", interval="1d"):
        """
        Fetch stock data for a ticker from Yahoo Finance.

        Args:
            ticker (str): Stock ticker symbol
            period (str): Time period ('1y', '5y', etc.)
            interval (str): Data interval ('1d', '1wk', etc.)

        Returns:
            pandas.DataFrame: DataFrame with stock data
        """
        # Check cache first
        cache_path = self._get_cache_path(ticker, period, interval)

        # Use the centralized cache validation logic
        from src.stockdata import should_use_cache

        should_use, reason = should_use_cache(cache_path, self.cache_ttl)

        if should_use:
            logger.info(f"Loading {ticker} data from cache: {reason}")
            try:
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)
            except Exception as e:
                logger.warning(f"Error reading cache for {ticker}: {e}")
                # Continue to fetch from API
        else:
            logger.info(f"Cache for {ticker} is not valid: {reason}")

        # Fetch from yfinance
        try:
            logger.info(f"Fetching data for {ticker} from Yahoo Finance")
            df = self._fetch_from_yfinance(ticker, period, interval)

            # Save to cache
            df.to_csv(cache_path)

            return df
        except (ValueError, pd.errors.EmptyDataError) as e:
            # These are expected errors that can happen with valid inputs
            # For example, a valid ticker that has no data available
            logger.warning(f"Data fetch error for {ticker}: {e}")

            # Only use expired cache for expected data errors, not for programming errors
            if os.path.exists(cache_path):
                logger.warning(f"Using expired cache for {ticker} as fallback")
                try:
                    return pd.read_csv(cache_path, index_col=0, parse_dates=True)
                except (pd.errors.ParserError, pd.errors.EmptyDataError) as cache_e:
                    logger.error(f"Error reading cache for {ticker}: {cache_e}")
                    # Re-raise the original error since cache fallback failed
                    raise e from cache_e

            # Re-raise the original exception if no cache fallback
            raise
        except (ImportError, NameError, AttributeError, TypeError, SyntaxError) as e:
            # These are programming errors that should never be caught silently
            logger.critical(f"Critical error in data fetcher: {e}", exc_info=True)
            raise
        except Exception as e:
            # For other unexpected errors, log and re-raise
            logger.error(
                f"Unexpected error fetching data for {ticker}: {e}", exc_info=True
            )
            raise

    def fetch_market_data(self, market_index="SPY", period=None, interval="1d"):
        """
        Fetch market index data for beta calculations.

        Args:
            market_index (str): Market index ticker symbol (default: 'SPY' for S&P 500 ETF)
            period (str, optional): Time period ('1y', '5y', etc.). If None, uses the class beta_period.
            interval (str): Data interval ('1d', '1wk', etc.)

        Returns:
            pandas.DataFrame: DataFrame with market index data
        """
        # Use the class beta_period if period is None
        if period is None:
            period = self.beta_period
            logger.info(f"Using default beta period: {period}")

        # Call fetch_data with the market index ticker
        return self.fetch_data(market_index, period, interval)

    def _fetch_from_yfinance(self, ticker, period="1y", interval="1d"):
        """
        Fetch data from Yahoo Finance using yfinance.

        Args:
            ticker (str): Stock ticker symbol
            period (str): Time period ('1y', '5y', etc.)
            interval (str): Data interval ('1d', '1wk', etc.)

        Returns:
            pandas.DataFrame: DataFrame with stock data
        """
        # Map period to yfinance format if needed
        # yfinance already accepts '1y', '5y', etc.
        yf_period = self._map_period_to_yfinance(period)

        # Fetch data
        try:
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period=yf_period, interval=interval)

            if df.empty:
                raise ValueError(f"No historical data found for {ticker}")

            # Rename columns to match expected format
            # yfinance returns columns with capitalized names already, but let's ensure consistency
            column_mapping = {
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Volume": "Volume",
                "Dividends": "Dividends",
                "Stock Splits": "Stock Splits",
            }

            # Only rename columns that exist
            rename_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=rename_cols)

            # Ensure index is named 'date'
            df.index.name = "date"

            # Convert timezone-aware timestamps to naive timestamps
            # This is important for compatibility with the current implementation
            if df.index.tzinfo is not None:
                df.index = df.index.tz_localize(None)

            return df

        except Exception as e:
            # Map yfinance-specific errors to consistent error messages
            if "No data found" in str(e):
                raise ValueError(f"No historical data found for {ticker}") from e
            elif "Invalid ticker" in str(e):
                raise ValueError(f"Invalid ticker: {ticker}") from e
            else:
                # Re-raise with more context
                raise ValueError(f"Error fetching data for {ticker}: {e}") from e

    def _map_period_to_yfinance(self, period):
        """
        Map period string to yfinance format.

        Args:
            period (str): Period string ('1y', '5y', etc.)

        Returns:
            str: Period string in yfinance format
        """
        # yfinance accepts these period formats:
        # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

        # Initialize result with default value
        result = "1y"  # Default value

        # Check if period is already in yfinance format
        valid_periods = [
            "1d",
            "5d",
            "1mo",
            "3mo",
            "6mo",
            "1y",
            "2y",
            "5y",
            "10y",
            "ytd",
            "max",
        ]
        if period in valid_periods:
            result = period
        elif period.endswith("y"):
            try:
                years = int(period[:-1])
                if years == 1:
                    result = "1y"
                elif years == 2:
                    result = "2y"
                elif years <= 5:
                    result = "5y"
                else:
                    result = "10y"
            except ValueError:
                # Keep default value
                logger.warning(f"Invalid year format: {period}, defaulting to '1y'")
        elif period.endswith("m"):
            try:
                months = int(period[:-1])
                if months <= 1:
                    result = "1mo"
                elif months <= 3:
                    result = "3mo"
                elif months <= 6:
                    result = "6mo"
                else:
                    result = "1y"
            except ValueError:
                # Keep default value
                logger.warning(f"Invalid month format: {period}, defaulting to '1y'")
        elif period.endswith("d"):
            try:
                days = int(period[:-1])
                if days <= 1:
                    result = "1d"
                elif days <= 5:
                    result = "5d"
                else:
                    result = "1mo"
            except ValueError:
                # Keep default value
                logger.warning(f"Invalid day format: {period}, defaulting to '1y'")
        else:
            # Default to 1y if period format is not recognized
            logger.warning(f"Unrecognized period format: {period}, defaulting to '1y'")

        return result

    def _get_cache_path(self, ticker, period, interval):
        """
        Get the path to the cache file for a ticker.

        Args:
            ticker (str): Stock ticker symbol
            period (str): Time period
            interval (str): Data interval

        Returns:
            str: Path to cache file
        """
        return os.path.join(self.cache_dir, f"{ticker}_{period}_{interval}.csv")
