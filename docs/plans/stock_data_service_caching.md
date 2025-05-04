# StockData Service Caching Design

## WHY

### Problem Statement
Our current StockData service implementation has a caching gap. While we've implemented in-memory caching in the StockDataService, we're still indirectly using StockOracle's filesystem caching in `.cache_fmp` or `.cache_yf` directories. This creates redundant caching layers and doesn't align with our design decision to have a single, unified caching strategy.

### Goals
1. Implement a single, consistent caching strategy for StockDataService
2. Move from the old cache directories (`.cache_fmp`, `.cache_yf`) to a new dedicated directory (`.cache_stock_data`)
3. Maintain filesystem persistence for cache data between application restarts
4. Ensure the implementation is simple yet extensible for future needs

### Non-Goals
1. Implementing a complex distributed caching system
2. Supporting multiple cache backends (e.g., Redis, Memcached)
3. Backward compatibility with the old cache directories

## WHAT

We will enhance the StockDataService with filesystem caching capabilities:

1. **Direct Provider Access**:
   - Modify StockDataService to access data providers directly, bypassing StockOracle's caching layer
   - This ensures we have a single point of caching control

2. **Filesystem Cache**:
   - Implement filesystem caching in a new `.cache_stock_data` directory
   - Store cache data in a structured format (JSON) for easy reading and debugging

3. **Cache Management**:
   - Add methods to load/save the cache from/to disk
   - Implement automatic cache loading on service initialization
   - Add periodic cache saving to ensure persistence

4. **Cache Invalidation**:
   - Maintain the existing time-based invalidation strategy
   - Add support for invalidating specific data types

## HOW

### Direct Provider Access

Instead of using StockOracle's methods that include caching, we'll access the underlying data providers directly:

```python
class StockDataService:
    def __init__(self, oracle=None):
        self._cache = {}
        self._oracle = oracle or StockOracle.get_instance()
        # Get direct access to the provider
        self._provider = self._oracle.get_provider()

        # Load cache from disk on initialization
        self._load_cache_from_disk()
```

### Filesystem Cache Structure

We'll use a simple JSON-based cache structure:

```
.cache_stock_data/
  ├── AAPL.json
  ├── MSFT.json
  └── ...
```

Each JSON file will contain:
- Ticker symbol
- Market data (price, beta, volatility)
- Timestamp of last update
- Any additional data we might add in the future

Example JSON structure:
```json
{
  "ticker": "AAPL",
  "last_updated": "2023-10-15T14:30:00",
  "data": {
    "price": 150.0,
    "beta": 1.2,
    "volatility": 0.25
  }
}
```

### Cache Management Implementation

```python
import json
import os
from datetime import datetime
from pathlib import Path

class StockDataService:
    # ... existing code ...

    def _get_cache_dir(self) -> Path:
        """Get the cache directory path, creating it if it doesn't exist."""
        cache_dir = Path(".cache_stock_data")
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    def _get_cache_file_path(self, ticker: str) -> Path:
        """Get the cache file path for a ticker."""
        return self._get_cache_dir() / f"{ticker.upper()}.json"

    def _save_to_disk(self, stock_data: StockData) -> None:
        """Save a StockData object to disk."""
        cache_file = self._get_cache_file_path(stock_data.ticker)

        # Convert to serializable format
        data = {
            "ticker": stock_data.ticker,
            "last_updated": stock_data.last_updated.isoformat() if stock_data.last_updated else None,
            "data": {
                "price": stock_data.price,
                "beta": stock_data.beta,
                "volatility": stock_data.volatility
            }
        }

        # Write to file
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved cache for {stock_data.ticker} to disk")

    def _load_from_disk(self, ticker: str) -> StockData:
        """Load a StockData object from disk."""
        cache_file = self._get_cache_file_path(ticker)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)

            stock_data = StockData(ticker)
            stock_data.price = data["data"]["price"]
            stock_data.beta = data["data"]["beta"]
            stock_data.volatility = data["data"]["volatility"]

            # Parse the timestamp
            if data["last_updated"]:
                stock_data.last_updated = datetime.fromisoformat(data["last_updated"])

            logger.debug(f"Loaded cache for {ticker} from disk")
            return stock_data
        except Exception as e:
            logger.warning(f"Error loading cache for {ticker}: {e}")
            return None

    def _load_cache_from_disk(self) -> None:
        """Load all cached data from disk."""
        cache_dir = self._get_cache_dir()

        if not cache_dir.exists():
            return

        for cache_file in cache_dir.glob("*.json"):
            ticker = cache_file.stem.upper()
            stock_data = self._load_from_disk(ticker)

            if stock_data:
                self._cache[ticker] = stock_data

        logger.info(f"Loaded {len(self._cache)} stocks from disk cache")

    def save_cache_to_disk(self) -> None:
        """Save all cached data to disk."""
        for ticker, stock_data in self._cache.items():
            self._save_to_disk(stock_data)

        logger.info(f"Saved {len(self._cache)} stocks to disk cache")
```

### Updated Data Loading Logic

We'll modify the `load_market_data` method to use our direct provider access and update the filesystem cache:

```python
def load_market_data(self, ticker: str, force_refresh: bool = False) -> StockData:
    """Load or refresh market data for a stock."""
    ticker = ticker.upper()
    stock_data = self.get_stock_data(ticker)

    # Try to load from disk if not in memory
    if stock_data.last_updated is None:
        disk_data = self._load_from_disk(ticker)
        if disk_data:
            # Update in-memory data from disk
            stock_data.price = disk_data.price
            stock_data.beta = disk_data.beta
            stock_data.volatility = disk_data.volatility
            stock_data.last_updated = disk_data.last_updated

    # Check if we need to refresh the data
    needs_refresh = (
        force_refresh or
        stock_data.last_updated is None or
        self._is_data_stale(stock_data)
    )

    if needs_refresh:
        try:
            logger.debug(f"Fetching market data for {ticker}")

            # Fetch data directly from the provider
            stock_data.price = self._provider.get_price(ticker)
            stock_data.beta = self._calculate_beta(ticker)
            stock_data.volatility = self._provider.get_volatility(ticker)
            stock_data.last_updated = datetime.now()

            # Save to disk
            self._save_to_disk(stock_data)

            logger.debug(
                f"Updated market data for {ticker}: "
                f"price=${stock_data.price:.2f}, beta={stock_data.beta:.2f}, "
                f"volatility={stock_data.volatility:.2f}"
            )
        except Exception as e:
            logger.error(f"Error fetching market data for {ticker}: {e}")
            raise

    return stock_data

def _calculate_beta(self, ticker: str) -> float:
    """Calculate beta for a ticker using the provider directly."""
    try:
        # This bypasses StockOracle's caching
        return self._provider.calculate_beta(ticker)
    except Exception as e:
        logger.warning(f"Could not calculate beta for {ticker}: {e}")
        return 1.0  # Use beta of 1.0 as fallback
```

### Cache Invalidation

We'll maintain our existing time-based invalidation strategy:

```python
def _is_data_stale(self, stock_data: StockData, max_age_seconds: int = 3600) -> bool:
    """Check if the stock data is stale and needs refreshing."""
    if stock_data.last_updated is None:
        return True

    age = datetime.now() - stock_data.last_updated
    return age.total_seconds() > max_age_seconds
```

### Implementation Strategy

1. **Phase 1: Direct Provider Access**
   - Modify StockDataService to access providers directly
   - Update the data loading logic to bypass StockOracle's caching

2. **Phase 2: Filesystem Caching**
   - Implement the filesystem caching methods
   - Add automatic cache loading on initialization
   - Update the data loading logic to check disk cache

3. **Phase 3: Testing and Refinement**
   - Add unit tests for the new caching functionality
   - Verify cache persistence between application restarts
   - Optimize cache loading/saving for performance

### Extensibility Considerations

This design is extensible in several ways:

1. **Additional Data Types**:
   - The JSON structure can easily accommodate new data fields
   - The cache loading/saving methods can be extended for new data types

2. **Cache Configuration**:
   - We can add configuration options for cache directory, TTL, etc.
   - These could be loaded from environment variables or a config file

3. **Future Enhancements**:
   - The design could be extended to support different cache backends
   - We could add cache statistics and monitoring
   - We could implement more sophisticated invalidation strategies

By implementing this design, we'll have a single, consistent caching strategy that persists data between application restarts while maintaining the simplicity and extensibility of our StockData service.
