# Caching in Folio

This document explains how caching works in the Folio application, focusing on the cachetools-based caching system.

## Overview

Folio implements a sophisticated caching system to improve performance and reduce API calls to external data providers. The caching system is primarily used for market data, which can be expensive to fetch repeatedly.

The implementation uses a combination of:
- In-memory caching with cachetools
- Disk persistence with diskcache
- Intelligent key generation for method caching

## Cache Architecture

### Core Components

The caching system is built on two main libraries:

1. **cachetools**: A Python library providing various memoizing collections and decorators
2. **diskcache**: A disk-based cache implementation for persistent storage

### Cache Location

Cache data is stored in the `.cache` directory at the root of the project. This location is determined by the `get_cache_dir()` function in `src/folib/data/cache.py`.

### Cache Layers

The caching system uses a two-level approach:

1. **Memory Cache (Primary)**:
   - Implemented using cachetools' TTLCache
   - Provides fast access to frequently used data
   - Limited by the `maxsize` parameter (default: 128 items)
   - Entries expire based on TTL (Time-To-Live)

2. **Disk Cache (Secondary)**:
   - Implemented using diskcache
   - Provides persistence between application runs
   - Larger capacity than memory cache
   - Also uses TTL for expiration

## The @cached Decorator

The primary interface to the caching system is the `@cached` decorator, which can be applied to any function or method:

```python
@cached(ttl=900, key_prefix="ticker_data")  # 15 minutes TTL
def get_ticker_data(self, ticker: str) -> TickerData:
    # Function implementation...
```

### Decorator Parameters

- **ttl**: Time-to-live in seconds (default: 3600 - 1 hour)
- **key_prefix**: Prefix for cache keys to avoid collisions
- **cache_dir**: Custom directory for disk cache (optional)
- **use_expired_on_error**: Whether to use expired cache on error (default: True)
- **maxsize**: Maximum size of the in-memory cache (default: 128)

## Key Generation

One of the most important aspects of the caching system is how cache keys are generated. The system uses a smart key generation approach that:

1. **Handles method calls properly**: Automatically skips the `self` parameter
2. **Normalizes ticker symbols**: Converts ticker symbols to uppercase
3. **Creates consistent keys**: Ensures keys are consistent between application runs

### Key Function

The key generation is handled by the `_make_key` function, which:

```python
def _make_key(prefix: str) -> Callable:
    """Create a key function that properly handles method calls."""
    def key_func(*args, **kwargs) -> str:
        # Skip the first argument if it's a method call (self)
        if args and hasattr(args[0], "__class__") and not isinstance(
            args[0], (str, int, float, bool, tuple, list, dict)
        ):
            key_args = args[1:]  # Skip self
        else:
            key_args = args

        # Create key parts
        key_parts = [prefix] if prefix else []

        # Add arguments (with special handling for ticker symbols)
        for arg in key_args:
            if isinstance(arg, str) and len(arg) < 10:  # Likely a ticker symbol
                key_parts.append(arg.upper())
            else:
                key_parts.append(str(arg))

        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")

        # Join with underscore and return
        return "_".join(key_parts)

    return key_func
```

## Cache Flow

When a cached function is called:

1. **Key Generation**:
   - A cache key is generated based on the function name, prefix, and arguments
   - For methods, the `self` parameter is automatically skipped

2. **Memory Cache Check**:
   - The system first checks if the data exists in the in-memory cache
   - If found and not expired, it's returned immediately

3. **Disk Cache Check**:
   - If not found in memory, it checks the disk cache
   - If found and not expired, it's loaded into memory and returned

4. **Function Execution**:
   - If not found in either cache or expired, the original function is executed
   - The result is stored in both memory and disk caches

5. **Error Handling**:
   - If the function raises an exception and `use_expired_on_error` is True
   - The system will return expired cache data as a fallback (if available)

## Using the Cache

### Basic Usage

To cache a function or method:

```python
from src.folib.data.cache import cached

@cached(ttl=3600)  # 1 hour TTL
def expensive_calculation(input_data):
    # Expensive operation...
    return result
```

### Caching Methods

For class methods, the decorator handles the `self` parameter automatically:

```python
class DataService:
    @cached(ttl=900, key_prefix="service_data")  # 15 minutes TTL
    def get_data(self, identifier: str):
        # Fetch data...
        return data
```

### Cache Management

The cache module provides several functions for managing the cache programmatically:

```python
from src.folib.data.cache import clear_cache, log_cache_stats

# Clear the entire cache
clear_cache()

# Clear with backup
clear_cache(backup=True)

# Log cache statistics
log_cache_stats()

# Log detailed statistics
log_cache_stats(aggregate=False)
```

You can also clear the cache when loading a portfolio by using the `--no-cache` option:

```bash
# CLI command
python -m src.cli portfolio load path/to/portfolio.csv --no-cache

# Interactive shell
folio> portfolio load path/to/portfolio.csv --no-cache
```

## Cache Statistics

The caching system maintains statistics for each cached function:

- **Hits**: Number of successful cache retrievals
- **Misses**: Number of cache misses (function had to be executed)
- **Fallbacks**: Number of times expired cache was used due to errors

These statistics can be accessed and logged:

```python
from src.folib.data.cache import get_cache_stats, log_cache_stats

# Get raw statistics
stats = get_cache_stats()

# Log statistics in a readable format
log_cache_stats()
```

## Real-World Example: Ticker Service

The `TickerService` class in `src/folib/services/ticker_service.py` demonstrates effective use of the caching system:

```python
class TickerService:
    # ...

    @cached(ttl=900, key_prefix="ticker_data")  # 15 minutes TTL
    def get_ticker_data(self, ticker: str) -> TickerData:
        # Implementation...

    @cached(ttl=900, key_prefix="ticker_price")  # 15 minutes TTL
    def get_price(self, ticker: str) -> float:
        ticker_data = self.get_ticker_data(ticker)
        return ticker_data.effective_price

    @cached(ttl=86400, key_prefix="ticker_beta")  # 24 hours TTL
    def get_beta(self, ticker: str) -> float:
        ticker_data = self.get_ticker_data(ticker)
        return ticker_data.effective_beta
```

Note how different TTLs are used based on how frequently the data changes:
- Prices: 15 minutes (more volatile)
- Beta values: 24 hours (less volatile)

## Best Practices

1. **Choose appropriate TTLs** based on data volatility and importance

2. **Use meaningful key prefixes** to avoid collisions between different functions

3. **Consider cache implications** when refactoring cached functions:
   - Changing parameter names or types may invalidate existing cache entries
   - Changing return types may cause type errors when retrieving cached values

4. **Be careful with mutable arguments** as they can lead to inconsistent cache behavior

5. **Use debug logging** to understand cache behavior:
   ```python
   import logging
   logging.getLogger("src.folib.data.cache").setLevel(logging.DEBUG)
   ```

## Troubleshooting

### Common Issues

1. **Unexpected cache misses**:
   - Check if the key generation is consistent
   - Enable debug logging to see the generated cache keys
   - Verify that the cache directory exists and is writable

2. **Memory usage concerns**:
   - Adjust the `maxsize` parameter to limit memory cache size
   - Consider using smaller TTLs for large objects

3. **Stale data**:
   - Adjust TTL values based on data freshness requirements
   - Use `clear_cache()` to reset the cache if necessary

### Debugging

To debug caching issues:

1. Enable debug logging to see cache operations:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Examine cache statistics to understand hit/miss patterns:
   ```python
   from src.folib.data.cache import log_cache_stats
   log_cache_stats(aggregate=False)
   ```

3. Check the contents of the `.cache` directory to verify disk persistence

## Advanced Usage

### Custom Key Functions

While the default key generation works for most cases, you can create custom key functions for special needs:

```python
def custom_key_func(*args, **kwargs):
    # Custom key generation logic
    return key

@cached(ttl=3600)
def my_function(*args, **kwargs):
    # Implementation...

# Use with the custom key function
result = my_function(*args, **kwargs)
```

### Cache Preloading

For frequently accessed data, consider preloading the cache:

```python
# Prefetch data for common tickers
ticker_service.prefetch_tickers(["AAPL", "MSFT", "GOOGL", "AMZN"])
```

## Conclusion

The cachetools-based caching system in Folio provides an efficient, flexible way to cache data at multiple levels. By understanding how the cache works, you can optimize your code for better performance and reduced external API calls.

The combination of in-memory caching for speed and disk persistence for durability makes this system suitable for a wide range of caching needs, from short-lived data like stock prices to more stable information like company profiles.
