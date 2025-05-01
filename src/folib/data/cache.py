"""
Cache utilities for market data providers.

This module provides file-based caching functionality for market data providers,
with support for TTL-based expiration and methods for caching DataFrames and values.
"""

import logging
import os
import time

import pandas as pd

# Set up logging
logger = logging.getLogger(__name__)


class DataCache:
    """
    Cache manager for market data.

    This class provides methods for caching and retrieving market data,
    with support for TTL-based expiration.
    """

    def __init__(self, cache_dir: str, cache_ttl: int = 86400):
        """
        Initialize the DataCache.

        Args:
            cache_dir: Directory to store cached data
            cache_ttl: Cache TTL in seconds (default: 86400 - 1 day)
        """
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_path(
        self, ticker: str, period: str | None = None, interval: str | None = None
    ) -> str:
        """
        Get the path to the cache file for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Time period (optional)
            interval: Data interval (optional)

        Returns:
            Path to cache file
        """
        if period and interval:
            return os.path.join(self.cache_dir, f"{ticker}_{period}_{interval}.csv")
        else:
            return os.path.join(self.cache_dir, f"{ticker}.csv")

    def get_beta_cache_path(self, ticker: str) -> str:
        """
        Get the path to the beta cache file for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Path to beta cache file
        """
        return os.path.join(self.cache_dir, f"{ticker}_beta.txt")

    def is_cache_expired(self, cache_timestamp: float) -> bool:
        """
        Determine if cache should be considered expired based on TTL.

        Args:
            cache_timestamp: The timestamp of when the cache was created/modified

        Returns:
            True if cache should be considered expired, False otherwise
        """
        cache_age = time.time() - cache_timestamp
        return cache_age >= self.cache_ttl

    def read_dataframe_from_cache(self, cache_path: str) -> pd.DataFrame | None:
        """
        Read a DataFrame from cache if it exists and is not expired.

        Args:
            cache_path: Path to the cache file

        Returns:
            DataFrame from cache, or None if cache doesn't exist, is expired, or can't be read
        """
        if not os.path.exists(cache_path):
            logger.debug(f"Cache file does not exist: {cache_path}")
            return None

        # Get cache age in seconds
        cache_age = time.time() - os.path.getmtime(cache_path)
        cache_age_hours = cache_age / 3600  # Convert to hours for more readable logging

        if self.is_cache_expired(os.path.getmtime(cache_path)):
            logger.debug(
                f"Cache expired: {cache_path} (age: {cache_age_hours:.1f} hours)"
            )
            return None
        else:
            logger.debug(
                f"Cache valid: {cache_path} (age: {cache_age_hours:.1f} hours)"
            )

        try:
            logger.debug(f"Loading data from cache: {cache_path}")
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            logger.debug(f"Loaded {len(df)} rows from cache")
            return df
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def write_dataframe_to_cache(self, df: pd.DataFrame, cache_path: str) -> bool:
        """
        Write a DataFrame to cache.

        Args:
            df: DataFrame to cache
            cache_path: Path to the cache file

        Returns:
            True if successful, False otherwise
        """
        try:
            df.to_csv(cache_path)
            logger.debug(f"Cached {len(df)} rows of data to: {cache_path}")
            return True
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")
            return False

    def read_value_from_cache(self, cache_path: str) -> float | None:
        """
        Read a numeric value from cache if it exists and is not expired.

        Args:
            cache_path: Path to the cache file

        Returns:
            Value from cache, or None if cache doesn't exist, is expired, or can't be read
        """
        if not os.path.exists(cache_path):
            logger.debug(f"Cache file does not exist: {cache_path}")
            return None

        # Get cache age in seconds
        cache_age = time.time() - os.path.getmtime(cache_path)
        cache_age_hours = cache_age / 3600  # Convert to hours for more readable logging

        if self.is_cache_expired(os.path.getmtime(cache_path)):
            logger.debug(
                f"Cache expired: {cache_path} (age: {cache_age_hours:.1f} hours)"
            )
            return None
        else:
            logger.debug(
                f"Cache valid: {cache_path} (age: {cache_age_hours:.1f} hours)"
            )

        try:
            with open(cache_path) as f:
                value = float(f.read().strip())
            logger.debug(f"Loaded value from cache: {value:.3f}")
            return value
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def write_value_to_cache(self, value: float, cache_path: str) -> bool:
        """
        Write a numeric value to cache.

        Args:
            value: Value to cache
            cache_path: Path to the cache file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(cache_path, "w") as f:
                f.write(f"{value:.6f}")
            logger.debug(f"Cached value: {value:.3f} to {cache_path}")
            return True
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")
            return False
