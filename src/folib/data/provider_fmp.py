"""
Financial Modeling Prep (FMP) market data provider.

This module implements the MarketDataProvider interface using the Financial Modeling Prep API
via the fmpsdk package.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import ClassVar

import fmpsdk
import pandas as pd

from .provider import MarketDataProvider

# Set up logging
logger = logging.getLogger(__name__)


class FMPProvider(MarketDataProvider):
    """
    Financial Modeling Prep implementation of market data provider.

    This class provides access to market data from Financial Modeling Prep API.
    It implements caching to improve performance and reduce API calls.
    """

    # Default period for beta calculations
    beta_period = "3mo"

    # Default market index for beta calculations
    market_index = "SPY"

    # Period mapping from yfinance format to FMP days
    period_mapping: ClassVar[dict[str, str]] = {
        "1d": "1",
        "5d": "5",
        "1mo": "30",
        "3mo": "90",
        "6mo": "180",
        "1y": "365",
        "2y": "730",
        "5y": "1825",
        "10y": "3650",
        "ytd": "ytd",
        "max": "max",
    }

    def __init__(self, api_key: str, cache_dir=None, cache_ttl=None):
        """
        Initialize the FMPProvider.

        Args:
            api_key: FMP API key
            cache_dir: Directory to store cached data (default: .cache_fmp)
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)
        """
        if not api_key:
            raise ValueError("API key is required for FMP provider")

        self.api_key = api_key

        # Set default cache directory
        # Special case for Hugging Face Spaces
        if cache_dir is None:
            if (
                os.environ.get("HF_SPACE") == "1"
                or os.environ.get("SPACE_ID") is not None
            ):
                cache_dir = "/tmp/cache_fmp"
            else:
                cache_dir = ".cache_fmp"

        # Initialize the cache manager
        from .cache import DataCache

        self.cache = DataCache(cache_dir=cache_dir, cache_ttl=cache_ttl or 86400)

        # Store cache directory for reference
        self.cache_dir = cache_dir

    def get_price(self, ticker: str) -> float:
        """
        Get the current price for a ticker.

        This method fetches the latest closing price for the given ticker
        using the FMP API.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price

        Raises:
            ValueError: If the ticker is invalid or no price data is available
        """
        if not ticker:
            raise ValueError("Ticker cannot be empty")

        # Check if the ticker appears to be a valid stock symbol
        if not self.is_valid_stock_symbol(ticker):
            raise ValueError(f"Invalid stock symbol format: {ticker}")

        try:
            # Using fmpsdk
            quote_data = fmpsdk.quote(apikey=self.api_key, symbol=ticker)

            if not quote_data:
                raise ValueError(f"No quote data available for {ticker}")

            price = quote_data[0].get("price")
            if price is None:
                raise ValueError(f"No price data available for {ticker}")

            return float(price)
        except Exception as e:
            logger.error(f"Error getting price from FMP for {ticker}: {e}")

            # Fallback to historical data
            logger.info(f"Falling back to historical data for {ticker} price")
            from .stock import get_current_price

            historical_data = self.get_historical_data(ticker, period="1d")
            return get_current_price(historical_data)

    def get_beta(self, ticker: str) -> float | None:
        """
        Get the beta for a ticker.

        This method fetches the beta value for the given ticker using the FMP API.
        If the beta is not available directly, it calculates it manually using
        historical price data.

        Args:
            ticker: The ticker symbol

        Returns:
            The beta value, or None if beta cannot be calculated
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

        # Try to get beta directly from FMP
        try:
            # Using fmpsdk
            profile_data = fmpsdk.company_profile(apikey=self.api_key, symbol=ticker)

            if profile_data and "beta" in profile_data[0]:
                beta_value = profile_data[0]["beta"]
                if beta_value is not None:
                    beta = float(beta_value)
                    logger.debug(
                        f"Got beta of {beta:.2f} for {ticker} directly from FMP"
                    )

                    # Cache the beta value
                    self.cache.write_value_to_cache(beta, cache_path)

                    return beta

            logger.debug(f"Beta not available in FMP profile for {ticker}")
        except Exception as e:
            logger.debug(f"Error getting beta from FMP for {ticker}: {e}")

        # If FMP beta retrieval failed, calculate it manually
        logger.debug(f"Calculating beta manually for {ticker}")

        try:
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
        using the FMP API, with caching to improve performance
        and reduce API calls.

        Args:
            ticker: The ticker symbol
            period: Time period in yfinance format: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
            interval: Data interval ("1d", "1wk", "1mo", etc.) - Note: FMP has limited interval options

        Returns:
            DataFrame with historical price data (columns: Open, High, Low, Close, Volume)

        Raises:
            ValueError: If the ticker is empty
            ValueError: If the ticker doesn't appear to be a valid stock symbol
            ValueError: If no historical data is available
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

        # Map period to FMP timeframe
        days = self._map_period_to_days(period)

        # Calculate from_date based on period
        to_date = datetime.now().strftime("%Y-%m-%d")

        if days == "ytd":
            from_date = f"{datetime.now().year}-01-01"
        elif days == "max":
            from_date = "1970-01-01"  # A very early date to get all available data
        else:
            from_date = (datetime.now() - timedelta(days=int(days))).strftime(
                "%Y-%m-%d"
            )

        logger.info(f"Fetching data for {ticker} from FMP: {from_date} to {to_date}")

        try:
            # Using fmpsdk
            if interval.lower() == "1d":
                # Use historical price endpoint for daily data
                logger.info(
                    f"Calling FMP API for {ticker} historical data from {from_date} to {to_date}"
                )
                historical_data = fmpsdk.historical_price_full(
                    apikey=self.api_key,
                    symbol=ticker,
                    from_date=from_date,
                    to_date=to_date,
                )

                logger.info(f"Response type for {ticker}: {type(historical_data)}")

                if not historical_data:
                    raise ValueError(f"No historical data returned for {ticker}")

                # Handle different response formats
                if isinstance(historical_data, list):
                    # If the response is a list, use it directly
                    logger.info(f"Response is a list with {len(historical_data)} items")
                    if not historical_data:
                        raise ValueError(f"Empty list returned for {ticker}")

                    # Convert to DataFrame
                    df = pd.DataFrame(historical_data)
                elif isinstance(historical_data, dict):
                    # If the response is a dict, check for the 'historical' key
                    logger.info(
                        f"Response is a dict with keys: {historical_data.keys()}"
                    )

                    if "historical" not in historical_data:
                        logger.error(
                            f"Missing 'historical' key in response for {ticker}. Keys: {historical_data.keys()}"
                        )
                        raise ValueError(f"No historical data returned for {ticker}")

                    # Convert to DataFrame
                    df = pd.DataFrame(historical_data["historical"])
                else:
                    # Unexpected response type
                    logger.error(f"Unexpected response type: {type(historical_data)}")
                    raise ValueError(
                        f"Unexpected response type for {ticker}: {type(historical_data)}"
                    )

            else:
                # For intraday data, use a different endpoint
                # Note: FMP has limited interval options
                # Map interval to FMP format
                fmp_interval = self._map_interval_to_fmp(interval)

                # For intraday data, we might need to limit the date range
                # as FMP might have restrictions on how far back intraday data goes
                logger.info(
                    f"Calling FMP API for {ticker} intraday data with interval {fmp_interval}"
                )
                historical_data = fmpsdk.historical_chart(
                    apikey=self.api_key,
                    symbol=ticker,
                    time_delta=fmp_interval,
                    from_date=from_date,
                    to_date=to_date,
                )

                logger.info(f"Response type for {ticker}: {type(historical_data)}")

                if not historical_data:
                    raise ValueError(f"No historical data returned for {ticker}")

                # Handle different response formats
                if isinstance(historical_data, list):
                    # If the response is a list, use it directly
                    logger.info(f"Response is a list with {len(historical_data)} items")
                    if not historical_data:
                        raise ValueError(f"Empty list returned for {ticker}")

                    # Convert to DataFrame
                    df = pd.DataFrame(historical_data)
                elif isinstance(historical_data, dict):
                    # If the response is a dict, check for data
                    logger.info(
                        f"Response is a dict with keys: {historical_data.keys()}"
                    )

                    # Try to extract data based on common FMP API response formats
                    if "historical" in historical_data:
                        df = pd.DataFrame(historical_data["historical"])
                    else:
                        # If no recognized format, raise an error
                        logger.error(
                            f"Unrecognized dict format: {historical_data.keys()}"
                        )
                        raise ValueError(f"Unrecognized response format for {ticker}")
                else:
                    # Unexpected response type
                    logger.error(f"Unexpected response type: {type(historical_data)}")
                    raise ValueError(
                        f"Unexpected response type for {ticker}: {type(historical_data)}"
                    )

            # Process the DataFrame
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

            # Rename columns to match yfinance format
            df.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                },
                inplace=True,
            )

            # Save to cache
            self.cache.write_dataframe_to_cache(df, cache_path)

            return df

        except Exception as e:
            logger.error(f"Error getting historical data from FMP for {ticker}: {e}")
            raise ValueError(f"Failed to get historical data for {ticker}: {e}") from e

    def _map_period_to_days(self, period: str) -> str:
        """
        Map yfinance period format to FMP days.

        Args:
            period: Period in yfinance format

        Returns:
            Period in FMP format (days)
        """
        return self.period_mapping.get(period, "365")  # Default to 1 year

    def _map_interval_to_fmp(self, interval: str) -> str:
        """
        Map yfinance interval format to FMP interval.

        Args:
            interval: Interval in yfinance format

        Returns:
            Interval in FMP format
        """
        # FMP has limited interval options
        interval_mapping = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1hour",
            "4h": "4hour",
            "1d": "daily",
            "1wk": "weekly",
            "1mo": "monthly",
        }
        return interval_mapping.get(interval, "daily")  # Default to daily
