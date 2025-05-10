# Plan: Persistent Caching for Market Data (v1)

**Date:** 2023-06-01
**Author:** Claude 3.7 Sonnet

## WHY

The current implementation of `MarketDataProvider` in `src/folib/data/market_data.py` only has in-session caching, which means data is lost when the application restarts. Adding persistent caching will:

1. **Reduce API Calls:** Minimize redundant calls to external financial data providers
2. **Improve Performance:** Faster data retrieval for frequently accessed tickers
3. **Support Flexible Invalidation:** Allow different cache invalidation strategies for different data types (e.g., beta vs price)
4. **Enhance User Experience:** Provide faster response times and better offline capabilities
5. **Reduce Costs:** Fewer API calls can reduce costs for paid data services

## WHAT

We need to implement a persistent caching mechanism for the `MarketDataProvider` class that:

- Stores data on disk between application sessions in a `.cache` directory
- Allows for flexible cache invalidation strategies per data type
- Provides fallback to expired cache with appropriate warnings
- Maintains the simplicity and extensibility of the current design
- Follows the project's existing patterns and conventions
- Tracks and logs cache hit rates for monitoring

## HOW

We will implement a decorator-based caching approach using the `diskcache` library:

1. **Create a Cache Module:**
   - Implement a configurable cache decorator in `src/folib/data/cache.py`
   - Support different TTLs per data type
   - Handle fallback to expired cache with warnings
   - Track and log cache statistics

2. **Apply Decorators to MarketDataProvider:**
   - Apply cache decorators to `get_price`, `get_beta`, and `_fetch_profile` methods
   - Configure appropriate TTLs for each method
   - Update initialization to set up cache

3. **Add Cache Management:**
   - Add methods to clear cache
   - Add methods to view cache statistics
   - Implement cache directory management

## Scope

This change will primarily affect:

- `src/folib/data/market_data.py`: Add caching decorators to methods
- New file `src/folib/data/cache.py`: Implement caching utilities
- `pyproject.toml`: Add `diskcache` dependency
- `tests/folib/data/test_market_data.py`: Update tests to account for persistent cache
- New file `tests/folib/data/test_cache.py`: Add tests for cache functionality

The change is moderate in complexity but focused in scope, affecting only the data layer of the application.

## Assumptions

1. The `diskcache` library will meet our needs for persistent caching
2. The decorator approach will be maintainable and extensible
3. The default TTLs (1 hour for price, 1 week for beta, 1 month for profile) are appropriate
4. Cache invalidation based on TTL is sufficient for our needs
5. The `.cache` directory is an acceptable location for cache files
6. The current `MarketDataProvider` API will remain stable

## Open Questions

1. Should we implement cache size limits or cleanup strategies?
2. Should we add configuration options for cache settings (e.g., TTLs, directory)?
3. How should we handle cache migration if the cache format changes in the future?

## Implementation Details

### 1. Cache Module (`src/folib/data/cache.py`)

```python
"""
Caching utilities for data providers.

This module provides decorators and utilities for caching data from external sources.
It supports persistent caching with configurable TTLs and fallback to expired cache.
"""

import functools
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast

from diskcache import Cache

logger = logging.getLogger(__name__)

# Type variables for better type hinting
T = TypeVar('T')
R = TypeVar('R')

# Cache statistics
_cache_stats: Dict[str, Dict[str, int]] = {}


def get_cache_dir() -> str:
    """Get the cache directory path."""
    # Use project root/.cache by default
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))), '.cache')


def cached(
    ttl: int = 3600,  # Default: 1 hour
    key_prefix: str = '',
    cache_dir: Optional[str] = None,
    use_expired_on_error: bool = True
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Decorator for caching function results to disk.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_dir: Directory to store cache files
        use_expired_on_error: Whether to use expired cache on error

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        # Initialize cache statistics for this function
        func_name = f"{key_prefix}_{func.__name__}" if key_prefix else func.__name__
        if func_name not in _cache_stats:
            _cache_stats[func_name] = {"hits": 0, "misses": 0, "fallbacks": 0}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            # Get cache directory
            cache_directory = cache_dir or get_cache_dir()
            os.makedirs(cache_directory, exist_ok=True)

            # Create cache key
            cache_key = _create_cache_key(func, key_prefix, args, kwargs)

            # Initialize cache
            with Cache(cache_directory) as cache:
                # Try to get from cache
                cache_item = cache.get(cache_key)
                current_time = time.time()

                if cache_item is not None:
                    value, timestamp = cache_item

                    # Check if cache is still valid
                    if current_time - timestamp <= ttl:
                        logger.debug(f"Cache hit for {func_name}")
                        _cache_stats[func_name]["hits"] += 1
                        return cast(R, value)

                    # Cache is expired
                    cache_age_hours = (current_time - timestamp) / 3600
                    logger.debug(f"Cache expired for {func_name} (age: {cache_age_hours:.2f} hours)")

                # Cache miss or expired
                _cache_stats[func_name]["misses"] += 1

                try:
                    # Call the original function
                    result = func(*args, **kwargs)

                    # Store in cache
                    cache.set(cache_key, (result, current_time))

                    return result
                except Exception as e:
                    # If we have expired cache and use_expired_on_error is True
                    if cache_item is not None and use_expired_on_error:
                        value, timestamp = cache_item
                        cache_age_hours = (current_time - timestamp) / 3600
                        logger.warning(
                            f"Error calling {func_name}, using expired cache as fallback. "
                            f"Cache age: {cache_age_hours:.2f} hours. Error: {e}"
                        )
                        _cache_stats[func_name]["fallbacks"] += 1
                        return cast(R, value)

                    # Re-raise the exception
                    raise

        return wrapper
    return decorator


def _create_cache_key(func: Callable, prefix: str, args: Tuple, kwargs: Dict) -> str:
    """Create a cache key from function name and arguments."""
    # Start with function name
    key_parts = [func.__module__, func.__name__]

    # Add prefix if provided
    if prefix:
        key_parts.insert(0, prefix)

    # Add positional arguments
    for arg in args:
        key_parts.append(str(arg))

    # Add keyword arguments (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    # Join with underscore and return
    return "_".join(key_parts)


def get_cache_stats() -> Dict[str, Dict[str, int]]:
    """Get cache statistics."""
    return _cache_stats


def log_cache_stats() -> None:
    """Log cache statistics at INFO level."""
    for func_name, stats in _cache_stats.items():
        total = stats["hits"] + stats["misses"]
        hit_rate = (stats["hits"] / total) * 100 if total > 0 else 0
        logger.info(
            f"Cache stats for {func_name}: "
            f"hit rate: {hit_rate:.1f}% "
            f"(hits: {stats['hits']}, misses: {stats['misses']}, fallbacks: {stats['fallbacks']})"
        )


def clear_cache(cache_dir: Optional[str] = None) -> None:
    """Clear the entire cache."""
    cache_directory = cache_dir or get_cache_dir()
    if os.path.exists(cache_directory):
        with Cache(cache_directory) as cache:
            cache.clear()
        logger.info(f"Cache cleared from {cache_directory}")

    # Reset statistics
    for func_stats in _cache_stats.values():
        for key in func_stats:
            func_stats[key] = 0
```

### 2. Updated MarketDataProvider (`src/folib/data/market_data.py`)

```python
"""
Market data provider for financial data.

This module provides a unified interface for fetching market data from FMP API.
It includes both in-session and persistent caching to minimize redundant API calls.
"""

import logging
import os
from typing import Any, Dict, Optional

import fmpsdk

from src.folib.data.cache import cached

logger = logging.getLogger(__name__)

# Cache TTLs in seconds
PRICE_TTL = 3600  # 1 hour
BETA_TTL = 604800  # 1 week (7 days)
PROFILE_TTL = 2592000  # 1 month (30 days)


class MarketDataProvider:
    """Primary interface for accessing market data.

    Uses Financial Modeling Prep (FMP) API to fetch stock price and beta data.
    Implements both in-session and persistent caching to minimize redundant API calls.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the market data provider.

        Args:
            api_key: FMP API key. If None, will attempt to read from FMP_API_KEY environment variable.

        Raises:
            ValueError: If no API key is provided and FMP_API_KEY environment variable is not set.
        """
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY is required.")
        # In-session cache: {ticker: {price: value, beta: value, profile: raw_data}}
        self._session_cache: Dict[str, Dict[str, Any]] = {}

    @cached(ttl=PROFILE_TTL, key_prefix="profile")
    def _fetch_profile(self, ticker: str) -> Dict[str, Any]:
        """Fetch company profile data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Company profile data dictionary or None if not found or error occurred.
        """
        ticker_upper = ticker.upper()
        if (
            ticker_upper not in self._session_cache
            or "profile" not in self._session_cache[ticker_upper]
        ):
            logger.debug(f"Fetching FMP profile for {ticker_upper}")
            try:
                profile_data = fmpsdk.company_profile(
                    apikey=self.api_key, symbol=ticker_upper
                )
                if profile_data:
                    profile = profile_data[0]
                    self._session_cache.setdefault(ticker_upper, {})["profile"] = (
                        profile
                    )
                    self._session_cache[ticker_upper]["price"] = profile.get("price")
                    self._session_cache[ticker_upper]["beta"] = profile.get("beta")
                    return profile
                else:
                    logger.warning(f"No profile data found for {ticker_upper}")
                    self._session_cache.setdefault(ticker_upper, {})["profile"] = None
                    return None
            except Exception as e:
                logger.error(f"Error fetching FMP profile for {ticker_upper}: {e}")
                self._session_cache.setdefault(ticker_upper, {})["profile"] = None
                raise
        return self._session_cache[ticker_upper].get("profile")

    @cached(ttl=PRICE_TTL, key_prefix="price")
    def get_price(self, ticker: str) -> float:
        """Get the current price for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Current stock price as float or None if not available.
        """
        ticker_upper = ticker.upper()
        if (
            ticker_upper in self._session_cache
            and self._session_cache[ticker_upper].get("price") is not None
        ):
            return self._session_cache[ticker_upper]["price"]
        profile = self._fetch_profile(ticker)
        price = profile.get("price") if profile else None
        if price is not None:
            try:
                return float(price)
            except (ValueError, TypeError):
                logger.error(f"Invalid price value for {ticker_upper}: {price}")
                return None
        return None

    @cached(ttl=BETA_TTL, key_prefix="beta")
    def get_beta(self, ticker: str) -> float:
        """Get the beta value for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Beta value as float or None if not available.
        """
        ticker_upper = ticker.upper()
        if (
            ticker_upper in self._session_cache
            and self._session_cache[ticker_upper].get("beta") is not None
        ):
            return self._session_cache[ticker_upper]["beta"]
        profile = self._fetch_profile(ticker)
        beta = profile.get("beta") if profile else None
        if beta is not None:
            try:
                return float(beta)
            except (ValueError, TypeError):
                logger.error(f"Invalid beta value for {ticker_upper}: {beta}")
                return None
        return None

    def clear_session_cache(self) -> None:
        """Clear the in-session cache."""
        self._session_cache.clear()
        logger.info("In-session market data cache cleared.")


# Default instance (requires FMP_API_KEY env var)
try:
    market_data_provider = MarketDataProvider()
    logger.info("Default MarketDataProvider initialized successfully")
except ValueError as e:
    logger.error(f"Failed to initialize default MarketDataProvider: {e}")
    market_data_provider = None
```

### 3. Update `pyproject.toml`

Add the `diskcache` dependency to `pyproject.toml`.

### 4. Testing

Create tests for the cache functionality and update existing tests for `MarketDataProvider`.

## Next Steps

1. Implement the cache module
2. Update the `MarketDataProvider` class
3. Add tests for the new functionality
4. Update `pyproject.toml` with the new dependency
5. Document the caching system
