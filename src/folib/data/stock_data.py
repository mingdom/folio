"""
Stock data management.

This module provides a structured way to store and access stock-related data
through the StockData and StockDataService classes. It serves as a central
point for managing stock information with efficient caching.

The StockDataService is designed to be used with dependency injection, but
also provides a default instance for convenience.

Example usage:
    # Using dependency injection
    service = StockDataService()
    stock_data = service.load_market_data("AAPL")
    beta = stock_data.beta

    # Using the default instance
    from src.folib.data.stock_data import default_stock_service
    stock_data = default_stock_service.load_market_data("MSFT")
    price = stock_data.price

Features:
- In-memory caching of stock data
- Filesystem persistence in .cache_stock_data directory
- Automatic cache invalidation based on age
- Clear separation of data fetching and storage
- Extensible design for future data types
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.folib.data.stock import StockOracle

# Set up logging
logger = logging.getLogger(__name__)


class StockData:
    """Container for stock-related information.

    This class stores various data points related to a stock, including
    market data (price, beta, volatility) and potentially fundamental data
    in the future. It serves as a cache-friendly container that can be
    expanded as our data needs grow.
    """

    def __init__(self, ticker: str):
        """Initialize a StockData object.

        Args:
            ticker: The stock ticker symbol
        """
        # Core identifier
        self.ticker = ticker

        # Market data
        self.price: float | None = None
        self.beta: float | None = None
        self.volatility: float | None = None

        # Cache management
        self.last_updated: datetime | None = None

    def __repr__(self) -> str:
        """Return a string representation of the StockData object."""
        return (
            f"StockData(ticker='{self.ticker}', "
            f"price={self.price}, "
            f"beta={self.beta}, "
            f"volatility={self.volatility}, "
            f"last_updated={self.last_updated})"
        )


class StockDataService:
    """Service for managing stock data.

    This service is responsible for fetching, caching, and providing
    access to StockData objects. It uses StockOracle as its data source
    and maintains both in-memory and filesystem caches to reduce API calls.
    """

    def __init__(self, oracle=None):
        """Initialize the StockDataService.

        Args:
            oracle: Optional StockOracle instance. If None, the default instance will be used.
        """
        self._cache = {}  # ticker -> StockData
        self._oracle = oracle or StockOracle.get_instance()

        # Load cache from disk on initialization
        self._load_cache_from_disk()

    def get_stock_data(self, ticker: str) -> StockData:
        """Get a StockData object for the given ticker.

        If the data doesn't exist in the cache, creates a new StockData object.
        Note: This doesn't load the data - use load_market_data() for that.

        Args:
            ticker: The stock ticker symbol

        Returns:
            A StockData object (may be empty if not yet loaded)
        """
        ticker = ticker.upper()  # Normalize ticker to uppercase
        if ticker not in self._cache:
            self._cache[ticker] = StockData(ticker)

        return self._cache[ticker]

    def load_market_data(self, ticker: str, force_refresh: bool = False) -> StockData:
        """Load or refresh market data for a stock.

        Fetches price, beta, and volatility data for the given ticker.
        Uses cached data unless force_refresh is True or the data is stale.

        Args:
            ticker: The stock ticker symbol
            force_refresh: Whether to force a refresh from the data source

        Returns:
            The updated StockData object

        Raises:
            ValueError: If the ticker is invalid or no data is available
        """
        ticker = ticker.upper()  # Normalize ticker to uppercase
        stock_data = self.get_stock_data(ticker)

        # Try to load from disk if not in memory and not already loaded
        if stock_data.last_updated is None:
            disk_data = self._load_from_disk(ticker)
            if disk_data:
                # Update in-memory data from disk
                stock_data.price = disk_data.price
                stock_data.beta = disk_data.beta
                stock_data.volatility = disk_data.volatility
                stock_data.last_updated = disk_data.last_updated

                logger.debug(f"Loaded {ticker} data from disk cache")

        # Check if we need to refresh the data
        needs_refresh = (
            force_refresh
            or stock_data.last_updated is None
            or self._is_data_stale(stock_data)
        )

        if needs_refresh:
            try:
                logger.debug(f"Fetching market data for {ticker}")

                # Fetch data from StockOracle
                stock_data.price = self._oracle.get_price(ticker)
                stock_data.beta = self._oracle.get_beta(ticker)
                stock_data.volatility = self._oracle.get_volatility(ticker)
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
                # Re-raise the exception to be handled by the caller
                raise
        else:
            logger.debug(
                f"Using cached market data for {ticker} (last updated: {stock_data.last_updated})"
            )

        return stock_data

    def _is_data_stale(
        self, stock_data: StockData, max_age_seconds: int = 3600
    ) -> bool:
        """Check if the stock data is stale and needs refreshing.

        Args:
            stock_data: The StockData object to check
            max_age_seconds: Maximum age in seconds (default: 1 hour)

        Returns:
            True if the data is stale, False otherwise
        """
        if stock_data.last_updated is None:
            return True

        age = datetime.now() - stock_data.last_updated
        return age.total_seconds() > max_age_seconds

    def _get_cache_dir(self) -> Path:
        """Get the cache directory path, creating it if it doesn't exist.

        Returns:
            The cache directory path
        """
        cache_dir = Path(".cache_stock_data")
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    def _get_cache_file_path(self, ticker: str) -> Path:
        """Get the cache file path for a ticker.

        Args:
            ticker: The stock ticker symbol

        Returns:
            The cache file path
        """
        return self._get_cache_dir() / f"{ticker.upper()}.json"

    def _save_to_disk(self, stock_data: StockData) -> None:
        """Save a StockData object to disk.

        Args:
            stock_data: The StockData object to save
        """
        cache_file = self._get_cache_file_path(stock_data.ticker)

        # Convert to serializable format
        data = {
            "ticker": stock_data.ticker,
            "last_updated": stock_data.last_updated.isoformat()
            if stock_data.last_updated
            else None,
            "data": {
                "price": stock_data.price,
                "beta": stock_data.beta,
                "volatility": stock_data.volatility,
            },
        }

        try:
            # Write to file
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved cache for {stock_data.ticker} to disk")
        except Exception as e:
            logger.warning(f"Error saving cache for {stock_data.ticker} to disk: {e}")

    def _load_from_disk(self, ticker: str) -> StockData | None:
        """Load a StockData object from disk.

        Args:
            ticker: The stock ticker symbol

        Returns:
            The loaded StockData object, or None if not found or error
        """
        cache_file = self._get_cache_file_path(ticker)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
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
            logger.warning(f"Error loading cache for {ticker} from disk: {e}")
            return None

    def _load_cache_from_disk(self) -> None:
        """Load all cached data from disk."""
        cache_dir = self._get_cache_dir()

        if not cache_dir.exists():
            return

        count = 0
        for cache_file in cache_dir.glob("*.json"):
            ticker = cache_file.stem.upper()
            stock_data = self._load_from_disk(ticker)

            if stock_data:
                self._cache[ticker] = stock_data
                count += 1

        if count > 0:
            logger.info(f"Loaded {count} stocks from disk cache")

    def save_cache_to_disk(self) -> None:
        """Save all cached data to disk."""
        count = 0
        for _ticker, stock_data in self._cache.items():
            if stock_data.last_updated is not None:  # Only save if we have data
                self._save_to_disk(stock_data)
                count += 1

        if count > 0:
            logger.info(f"Saved {count} stocks to disk cache")

    def is_cash_like(self, ticker: str, description: str = "") -> bool:
        """Determine if a position should be considered cash or cash-like.

        Args:
            ticker: The ticker symbol to check
            description: The description of the security (optional)

        Returns:
            True if the position is likely cash or cash-like, False otherwise
        """
        return self._oracle.is_cash_like(ticker, description)

    def is_valid_stock_symbol(self, ticker: str) -> bool:
        """Check if a ticker symbol is likely a valid stock symbol.

        Args:
            ticker: The ticker symbol to check

        Returns:
            True if the ticker appears to be a valid stock symbol, False otherwise
        """
        return self._oracle.is_valid_stock_symbol(ticker)

    def clear_cache(self) -> None:
        """Clear the entire in-memory cache."""
        self._cache.clear()
        logger.debug("Stock data in-memory cache cleared")

    def clear_disk_cache(self) -> None:
        """Clear the entire disk cache."""
        cache_dir = self._get_cache_dir()

        if not cache_dir.exists():
            return

        count = 0
        for cache_file in cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Error deleting cache file {cache_file}: {e}")

        logger.info(f"Cleared {count} files from disk cache")

    def remove_from_cache(self, ticker: str) -> None:
        """Remove a specific ticker from the in-memory cache.

        Args:
            ticker: The ticker symbol to remove
        """
        ticker = ticker.upper()  # Normalize ticker to uppercase
        if ticker in self._cache:
            del self._cache[ticker]
            logger.debug(f"Removed {ticker} from in-memory cache")

    def remove_from_disk_cache(self, ticker: str) -> None:
        """Remove a specific ticker from the disk cache.

        Args:
            ticker: The ticker symbol to remove
        """
        ticker = ticker.upper()  # Normalize ticker to uppercase
        cache_file = self._get_cache_file_path(ticker)

        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug(f"Removed {ticker} from disk cache")
            except Exception as e:
                logger.warning(f"Error removing {ticker} from disk cache: {e}")


# Create a default instance for convenience
default_stock_service = StockDataService()
