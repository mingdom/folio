# Caching in Folio

This document explains how caching works in the Folio application, focusing on the stock data caching system.

## Overview

Folio implements a caching system to improve performance and reduce API calls to external data providers. The caching system is primarily used for stock market data, which can be expensive to fetch repeatedly.

The current implementation uses a combination of in-memory caching and filesystem persistence to provide efficient access to frequently used data.

## Cache Architecture

### StockDataService

The primary caching mechanism is implemented in the `StockDataService` class located in `src/folib/data/stock_data.py`. This service provides:

1. **In-memory caching**: Keeps recently accessed stock data in memory for immediate access
2. **Filesystem persistence**: Stores data on disk for persistence between application restarts
3. **Automatic cache invalidation**: Refreshes stale data based on configurable time thresholds

### Cache Location

Stock data is cached in the `.cache_stock_data` directory at the root of the project. Each stock's data is stored in a separate JSON file named after its ticker symbol (e.g., `AAPL.json`).

### Cache Structure

Each cached stock data file contains:

- **Ticker**: The stock symbol
- **Last Updated**: Timestamp of when the data was last fetched
- **Data**: The actual stock data including:
  - Price
  - Beta
  - Volatility

## How Caching Works

### Data Flow

1. When stock data is requested via `StockDataService.load_market_data()`:
   - First, the service checks if the data exists in the in-memory cache
   - If not found in memory, it checks the filesystem cache
   - If found in either cache and not stale, the cached data is returned
   - If not found or stale, fresh data is fetched from the data provider

2. When fresh data is fetched:
   - It is stored in the in-memory cache for immediate future access
   - It is also persisted to the filesystem for long-term storage

### Cache Invalidation

Data staleness is determined by the `_is_data_stale()` method, which compares the data's last update timestamp with the current time. By default, data is considered stale after 1 hour (3600 seconds).

This threshold can be adjusted based on the application's needs and the volatility of the data being cached.

## Using the Cache

### Accessing Cached Data

To access stock data with caching:

```python
from src.folib.data.stock_data import default_stock_service

# Get stock data (will use cache if available)
stock_data = default_stock_service.load_market_data("AAPL")

# Access the data
price = stock_data.price
beta = stock_data.beta
volatility = stock_data.volatility
```

### Forcing a Refresh

To bypass the cache and force a fresh data fetch:

```python
# Force refresh regardless of cache status
stock_data = default_stock_service.load_market_data("AAPL", force_refresh=True)
```

### Cache Management

The `StockDataService` provides several methods for managing the cache:

```python
# Clear the in-memory cache
default_stock_service.clear_cache()

# Clear the disk cache
default_stock_service.clear_disk_cache()

# Remove a specific ticker from the in-memory cache
default_stock_service.remove_from_cache("AAPL")

# Remove a specific ticker from the disk cache
default_stock_service.remove_from_disk_cache("AAPL")

# Save all in-memory cache to disk
default_stock_service.save_cache_to_disk()
```

## Implementation Details

### StockData Class

The `StockData` class serves as a container for stock-related information:

```python
class StockData:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.price: float | None = None
        self.beta: float | None = None
        self.volatility: float | None = None
        self.last_updated: datetime | None = None
```

### Cache Serialization

When saving to disk, the `StockData` object is serialized to JSON with the following structure:

```json
{
  "ticker": "AAPL",
  "last_updated": "2023-05-03T15:30:00",
  "data": {
    "price": 150.0,
    "beta": 1.2,
    "volatility": 0.25
  }
}
```

## Best Practices

1. **Use the default service instance** when possible to benefit from shared caching:
   ```python
   from src.folib.data.stock_data import default_stock_service
   ```

2. **Avoid unnecessary refreshes** to reduce API calls and improve performance.

3. **Consider cache implications** when making changes to the `StockData` class structure.

4. **Use appropriate cache invalidation** strategies based on the data's volatility and importance.

## Future Improvements

Potential enhancements to the caching system:

1. **Configurable cache TTL** per data type or ticker
2. **Memory usage limits** to prevent excessive memory consumption
3. **Cache preloading** for frequently accessed tickers
4. **Cache statistics** for monitoring and optimization
5. **Distributed caching** for multi-instance deployments

## Troubleshooting

### Common Issues

1. **Stale data**: If you're seeing outdated information, try forcing a refresh with `force_refresh=True`.

2. **Missing cache directory**: The `.cache_stock_data` directory is created automatically when needed. If it's missing, the service will recreate it.

3. **Corrupted cache files**: If you encounter errors related to cache loading, try clearing the disk cache with `clear_disk_cache()`.

### Debugging

To debug caching issues, you can:

1. Check the contents of the `.cache_stock_data` directory
2. Examine the timestamps in the cache files
3. Enable debug logging to see cache-related log messages

## Conclusion

The caching system in Folio provides an efficient way to store and retrieve stock data, reducing API calls and improving application performance. By understanding how the cache works, you can make better use of it and contribute to its improvement.
