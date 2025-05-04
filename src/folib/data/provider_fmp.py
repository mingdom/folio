"""
Financial Modeling Prep (FMP) market data provider.

This module implements the MarketDataProvider interface using the fmpsdk package,
providing access to stock prices, historical data, and beta values from the FMP API.

Note: This provider no longer implements caching. Caching is now handled by the
StockDataService class in stock_data.py.
"""

import re
from datetime import datetime, timedelta

import fmpsdk
import pandas as pd

from src.folib.logger import logger

from .provider import MarketDataProvider
from .utils import is_valid_stock_symbol


class FMPProvider(MarketDataProvider):
    """
    Financial Modeling Prep implementation of market data provider.

    This class provides access to market data from Financial Modeling Prep API.
    """

    # Default period for beta calculations
    beta_period = "3mo"

    # Default market index for beta calculations
    market_index = "SPY"

    # No longer using static period mapping - using dynamic parsing instead

    def __init__(self, api_key: str, cache_dir=None, cache_ttl=None):  # noqa: ARG002
        """
        Initialize the FMPProvider.

        Args:
            api_key: FMP API key
            cache_dir: Deprecated. No longer used.
            cache_ttl: Deprecated. No longer used.
        """
        if not api_key:
            raise ValueError("API key is required for FMP provider")

        self.api_key = api_key
        # cache_dir and cache_ttl parameters are kept for backward compatibility but are no longer used

    def try_get_beta_from_provider(self, ticker: str) -> float | None:
        """
        Try to get beta directly from FMP API.

        This method attempts to get the beta value directly from the
        company profile in FMP API, which is more efficient than
        calculating it manually.

        Args:
            ticker: The ticker symbol

        Returns:
            The beta value from FMP, or None if not available
        """
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
                    return beta

            logger.debug(f"Beta not available in FMP profile for {ticker}")
            return None
        except Exception as e:
            logger.debug(f"Error getting beta from FMP for {ticker}: {e}")
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
        using the FMP API.

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
        if not is_valid_stock_symbol(ticker):
            raise ValueError(f"Invalid stock symbol format: {ticker}")

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

        logger.debug(f"Fetching data for {ticker} from FMP: {from_date} to {to_date}")

        try:
            # Using fmpsdk
            if interval.lower() == "1d":
                # Use historical price endpoint for daily data
                logger.debug(
                    f"Calling FMP API for {ticker} historical data from {from_date} to {to_date}"
                )
                historical_data = fmpsdk.historical_price_full(
                    apikey=self.api_key,
                    symbol=ticker,
                    from_date=from_date,
                    to_date=to_date,
                )

                logger.debug(f"Response type for {ticker}: {type(historical_data)}")

                if not historical_data:
                    raise ValueError(f"No historical data returned for {ticker}")

                # Handle different response formats
                if isinstance(historical_data, list):
                    # If the response is a list, use it directly
                    logger.debug(
                        f"Response is a list with {len(historical_data)} items"
                    )
                    if not historical_data:
                        raise ValueError(f"Empty list returned for {ticker}")

                    # Convert to DataFrame
                    df = pd.DataFrame(historical_data)
                elif isinstance(historical_data, dict):
                    # If the response is a dict, check for the 'historical' key
                    logger.debug(
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
                logger.debug(
                    f"Calling FMP API for {ticker} intraday data with interval {fmp_interval}"
                )
                historical_data = fmpsdk.historical_chart(
                    apikey=self.api_key,
                    symbol=ticker,
                    time_delta=fmp_interval,
                    from_date=from_date,
                    to_date=to_date,
                )

                logger.debug(f"Response type for {ticker}: {type(historical_data)}")

                if not historical_data:
                    raise ValueError(f"No historical data returned for {ticker}")

                # Handle different response formats
                if isinstance(historical_data, list):
                    # If the response is a list, use it directly
                    logger.debug(
                        f"Response is a list with {len(historical_data)} items"
                    )
                    if not historical_data:
                        raise ValueError(f"Empty list returned for {ticker}")

                    # Convert to DataFrame
                    df = pd.DataFrame(historical_data)
                elif isinstance(historical_data, dict):
                    # If the response is a dict, check for data
                    logger.debug(
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

            return df

        except Exception as e:
            logger.error(f"Error getting historical data from FMP for {ticker}: {e}")
            raise ValueError(f"Failed to get historical data for {ticker}: {e}") from e

    def _map_period_to_days(self, period: str) -> str:
        """
        Parse a period string into days for FMP API.

        Handles formats like:
        - Nd: N days (e.g., "1d", "5d")
        - Nmo: N months (e.g., "1mo", "3mo")
        - Ny: N years (e.g., "1y", "5y")
        - Special cases: "ytd", "max"

        Args:
            period: Period string in yfinance format

        Returns:
            Number of days as string, or special value ("ytd", "max")

        Raises:
            ValueError: If the period format cannot be parsed
        """
        # Handle special cases
        if period in {"ytd", "max"}:
            return period

        # Parse the numeric part and unit

        match = re.match(r"(\d+)([dmy].*)", period)
        if not match:
            raise ValueError(f"Unsupported period format: {period}")

        value, unit = match.groups()
        value = int(value)

        # Convert to days based on unit
        if unit.startswith("d"):
            return str(value)
        elif unit.startswith("mo"):
            return str(value * 30)  # Approximate
        elif unit.startswith("y"):
            return str(value * 365)  # Approximate
        else:
            raise ValueError(f"Unsupported period unit: {unit}")

    def _map_interval_to_fmp(self, interval: str) -> str:
        """
        Parse an interval string into FMP API format.

        Converts formats like:
        - Nm: N minutes (e.g., "1m", "5m") → "Nmin"
        - Nh: N hours (e.g., "1h", "4h") → "Nhour"
        - 1d: daily
        - 1wk: weekly
        - 1mo: monthly

        Args:
            interval: Interval string in yfinance format

        Returns:
            Interval in FMP format

        Raises:
            ValueError: If the interval format cannot be parsed
        """
        # Handle special cases first
        if interval == "1d":
            return "daily"
        elif interval == "1wk":
            return "weekly"
        elif interval == "1mo":
            return "monthly"

        # Parse the numeric part and unit

        match = re.match(r"(\d+)([mh])", interval)
        if not match:
            raise ValueError(f"Unsupported interval format: {interval}")

        value, unit = match.groups()

        # Convert unit to FMP format
        if unit == "m":
            return f"{value}min"
        elif unit == "h":
            return f"{value}hour"
        else:
            # This shouldn't happen due to the regex, but just in case
            raise ValueError(f"Unsupported interval unit: {unit}")
