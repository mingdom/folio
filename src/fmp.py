"""
Data fetcher for stock data using Financial Modeling Prep API
"""

import logging
import os
from datetime import datetime, timedelta

import pandas as pd
import requests

from src.stockdata import DataFetcherInterface

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
HTTP_SUCCESS = 200


class DataFetcher(DataFetcherInterface):
    """Class to fetch stock data from Financial Modeling Prep API"""

    # Default period for beta calculations
    beta_period = "3m"

    def __init__(self, cache_dir=".cache_fmp"):
        """Initialize with cache directory"""
        self.cache_dir = cache_dir
        self.api_key = os.environ.get("FMP_API_KEY")

        # If not in environment, try to get from config
        if not self.api_key:
            try:
                from src.v2.config import config

                self.api_key = config.get("data.fmp.api_key")
            except ImportError:
                logger.warning(
                    "Could not import config from src.v2.config, will rely on environment variable"
                )

        self.cache_ttl = 86400  # Default to 1 day

        # Try to get cache TTL from config if available
        try:
            from src.v2.config import config

            self.cache_ttl = config.get("app.cache.ttl", 86400)
        except ImportError:
            logger.warning(
                "Could not import config from src.v2.config, using default cache TTL"
            )

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Check for API key
        if not self.api_key:
            raise ValueError(
                "No API key found. Please set the FMP_API_KEY environment variable or "
                "configure it in the config file."
            )

    def fetch_data(self, ticker, period="3m", interval="1d"):
        """
        Fetch stock data for a ticker

        Args:
            ticker (str): Stock ticker symbol
            period (str): Time period ('3m', '6m', '1y', etc.)
            interval (str): Data interval ('1d', '1wk', etc.)

        Returns:
            pandas.DataFrame: DataFrame with stock data

        Raises:
            ValueError: If no data is returned from API
        """
        # Check cache first
        cache_file = os.path.join(self.cache_dir, f"{ticker}_{period}_{interval}.csv")

        # Use the centralized cache validation logic
        from src.stockdata import should_use_cache

        should_use, reason = should_use_cache(cache_file, self.cache_ttl)

        if should_use:
            logger.debug(f"Loading cached data for {ticker}: {reason}")
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        else:
            logger.debug(f"Cache for {ticker} is not valid: {reason}")

        # Try to fetch from API
        try:
            logger.info(f"Fetching data for {ticker} from API")
            df = self._fetch_from_api(ticker, period)

            if df is not None and not df.empty:
                # Save to cache
                df.to_csv(cache_file)
                return df
            else:
                # This is a valid case - API returned no data for a valid ticker
                logger.warning(f"No data returned from API for {ticker}")
                # Raise a specific error instead of returning an empty DataFrame
                raise ValueError(f"No historical data found for {ticker}")
        except (ValueError, requests.exceptions.RequestException) as e:
            # These are expected errors that can happen with valid inputs
            # For example, a valid ticker that has no data available or network issues
            logger.warning(f"Data fetch error for {ticker}: {e}")

            # Only use expired cache for expected data errors, not for programming errors
            if os.path.exists(cache_file):
                logger.warning(f"Using expired cache for {ticker} as fallback")
                try:
                    return pd.read_csv(cache_file, index_col=0, parse_dates=True)
                except (pd.errors.ParserError, pd.errors.EmptyDataError) as cache_e:
                    logger.error(f"Error reading cache for {ticker}: {cache_e}")
                    # If we can't read the cache, re-raise the original error
                    raise e from cache_e

            # If this is a "No historical data" error and we have no cache,
            # it's reasonable to return an empty DataFrame with the expected structure
            if "No historical data found" in str(e):
                logger.warning(
                    f"No historical data found for {ticker} and no cache available"
                )
                return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

            # For other data errors with no cache, re-raise
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
            period (str, optional): Time period. If None, uses beta_period.
            interval (str): Data interval ('1d', '1wk', etc.)

        Returns:
            pandas.DataFrame: DataFrame with market index data
        """
        # Use the class beta_period if period is None
        if period is None:
            period = self.beta_period
            logger.info(f"Using default beta period: {period}")

        logger.debug(f"Fetching market data for {market_index}")
        return self.fetch_data(market_index, period, interval)

    def _fetch_from_api(self, ticker, period="5y"):
        """Fetch data from Financial Modeling Prep API"""
        # Determine date range based on period
        end_date = datetime.now()

        if period.endswith("y"):
            years = int(period[:-1])
            start_date = end_date - timedelta(days=365 * years)
        elif period.endswith("m"):
            months = int(period[:-1])
            start_date = end_date - timedelta(days=30 * months)
        else:
            # Default to 1 year
            start_date = end_date - timedelta(days=365)

        # Format dates for API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Construct API URL
        base_url = "https://financialmodelingprep.com/api/v3/historical-price-full"
        url = f"{base_url}/{ticker}?from={start_str}&to={end_str}&apikey={self.api_key}"

        # Make request
        response = requests.get(url)

        if response.status_code != HTTP_SUCCESS:
            raise ValueError(
                f"API request failed with status code {response.status_code}: {response.text}"
            )

        # Parse response
        data = response.json()

        if "historical" not in data:
            # This is not a critical error - just log a warning and return empty DataFrame
            logger.warning(f"No historical data found for {ticker}")
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        # Convert to DataFrame
        df = pd.DataFrame(data["historical"])

        # Convert date to datetime and set as index
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        # Sort by date (ascending)
        df = df.sort_index()

        # Rename columns to match expected format
        df = df.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )

        return df

    def _fetch_data(self, url, params=None):
        try:
            response = requests.get(url, params=params)
            if response.status_code == HTTP_SUCCESS:
                return response.json()
            else:
                logger.error(f"Failed to fetch data: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None


if __name__ == "__main__":
    # Simple test
    fetcher = DataFetcher()
    data = fetcher.fetch_data("AAPL", period="1y")
