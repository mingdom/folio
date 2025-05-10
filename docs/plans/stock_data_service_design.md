# Stock Data Service Design

## WHY

### Problem Statement
Currently, our application fetches stock data (price, beta, volatility) directly from the StockOracle when needed, but doesn't store this information in a structured way within our domain model. This leads to several issues:

1. **Repeated API Calls**: We may fetch the same data multiple times for the same ticker
2. **No Clear Ownership**: Stock data is separate from position data, but there's no clear home for it
3. **Limited Extensibility**: As we add more sophisticated financial data and calculations (DCF, financial statements), we need a structured way to store and access this data

### Goals
1. Create a simple but extensible design for storing and accessing stock data
2. Maintain separation between position data (quantity, cost basis) and stock data (price, beta, fundamentals)
3. Reduce API calls by implementing effective caching
4. Establish a foundation that can grow to support more complex financial data in the future

### Non-Goals
1. Implementing a complex provider abstraction layer (we'll focus on FMP for now)
2. Building a comprehensive financial data system (we'll start simple and expand as needed)
3. Integrating with FinanceToolkit at this stage (YAGNI principle)

## WHAT

We will implement two new components:

1. **StockData**: A simple data container class that holds all information related to a specific stock
2. **StockDataService**: A service that manages StockData objects, handles caching, and coordinates with StockOracle

### StockData Class
A lightweight container for stock-related information:
- Basic market data (price, beta, volatility)
- Metadata for cache management (last updated timestamp)
- Extensible design to add more properties in the future

### StockDataService
A service that:
- Maintains a cache of StockData objects
- Provides methods to fetch and update stock data
- Uses the existing StockOracle as its data source
- Handles cache invalidation and refreshing

## HOW

### StockData Class Design

```python
class StockData:
    """Container for stock-related information.

    This class stores various data points related to a stock, including
    market data (price, beta, volatility) and potentially fundamental data
    in the future. It serves as a cache-friendly container that can be
    expanded as our data needs grow.
    """

    def __init__(self, ticker: str):
        # Core identifier
        self.ticker = ticker

        # Market data
        self.price = None
        self.beta = None
        self.volatility = None

        # Cache management
        self.last_updated = None

        # Future expansion fields
        # self.income_statement = None
        # self.balance_sheet = None
        # self.cash_flow = None
        # self.dcf_valuation = None
```

### StockDataService Design

```python
class StockDataService:
    """Service for managing stock data.

    This service is responsible for fetching, caching, and providing
    access to StockData objects. It uses StockOracle as its data source
    and maintains an in-memory cache to reduce API calls.
    """

    def __init__(self):
        self._cache = {}  # ticker -> StockData
        self._oracle = StockOracle.get_instance()

    def get_stock_data(self, ticker: str) -> StockData:
        """Get a StockData object for the given ticker.

        If the data doesn't exist in the cache, creates a new StockData object.
        Note: This doesn't load the data - use load_market_data() for that.

        Args:
            ticker: The stock ticker symbol

        Returns:
            A StockData object (may be empty if not yet loaded)
        """
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
        """
        stock_data = self.get_stock_data(ticker)

        # Check if we need to refresh the data
        needs_refresh = (
            force_refresh or
            stock_data.last_updated is None or
            self._is_data_stale(stock_data)
        )

        if needs_refresh:
            # Fetch data from StockOracle
            stock_data.price = self._oracle.get_price(ticker)
            stock_data.beta = self._oracle.get_beta(ticker)
            stock_data.volatility = self._oracle.get_volatility(ticker)
            stock_data.last_updated = datetime.now()

        return stock_data

    def _is_data_stale(self, stock_data: StockData, max_age_seconds: int = 3600) -> bool:
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

    def is_cash_like(self, ticker: str, description: str = "") -> bool:
        """Determine if a position should be considered cash or cash-like.

        This is a pass-through to StockOracle's is_cash_like method to maintain
        compatibility with existing code.

        Args:
            ticker: The ticker symbol to check
            description: The description of the security (optional)

        Returns:
            True if the position is likely cash or cash-like, False otherwise
        """
        return self._oracle.is_cash_like(ticker, description)

    def is_valid_stock_symbol(self, ticker: str) -> bool:
        """Check if a ticker symbol is likely a valid stock symbol.

        This is a pass-through to StockOracle's is_valid_stock_symbol method to maintain
        compatibility with existing code.

        Args:
            ticker: The ticker symbol to check

        Returns:
            True if the ticker appears to be a valid stock symbol, False otherwise
        """
        return self._oracle.is_valid_stock_symbol(ticker)
```

## Integration Analysis

After analyzing the codebase, I've identified all integration points where the new StockDataService will need to be incorporated. This section outlines these integration points and potential challenges.

### Key Integration Points

1. **Direct StockOracle Usage in Portfolio Service**
   - File: `src/folib/services/portfolio_service.py`
   - Lines: 126-127, 147-148, 406-408, 504-505, 525-526, 650-653, 669-670
   - Functions: `process_portfolio()`, `_process_stock_position()`, `_get_option_market_data()`, `_get_position_beta()`, `get_portfolio_exposures()`
   - Integration: Replace direct `stockdata` calls with `stock_service` calls

2. **Exposure Calculations**
   - File: `src/folib/calculations/exposure.py`
   - Lines: 106-121, 138-147, 168-169
   - Functions: `calculate_beta_adjusted_exposure()`, `calculate_position_exposure()`
   - Integration: These functions need beta values that will now come from StockDataService

3. **Option Calculations**
   - File: `src/folib/calculations/options.py`
   - Integration: Option calculations need underlying stock prices and volatility

4. **Singleton Access Pattern**
   - Current: `from src.folib.data.stock import stockdata`
   - New: Need to decide how to make StockDataService accessible globally

5. **Cash Detection**
   - File: `src/folib/services/portfolio_service.py`
   - Lines: 126-127, 406-408
   - Functions: `process_portfolio()`, `_process_stock_position()`
   - Integration: Need to maintain the `is_cash_like()` functionality

### Integration Challenges and Solutions

1. **Singleton Pattern vs. Service Injection**

   **Challenge**: The current code uses a global `stockdata` singleton, but modern practice favors dependency injection.

   **Options**:
   - Create a global `stock_service` similar to `stockdata`
   - Use dependency injection by passing the service to functions that need it
   - Use a hybrid approach with a global default but allow injection

   **Recommendation**: Create a global instance for backward compatibility but design the class to support dependency injection.

   ```python
   # In src/folib/data/stock_data.py
   stock_service = StockDataService()

   # In code that needs customization
   custom_service = StockDataService(custom_oracle)
   ```

2. **API Compatibility**

   **Challenge**: Existing code expects certain methods from StockOracle.

   **Solution**: Implement pass-through methods in StockDataService for full API compatibility:

   ```python
   def get_price(self, ticker: str) -> float:
       """Get the current price for a ticker."""
       stock_data = self.load_market_data(ticker)
       return stock_data.price

   def get_beta(self, ticker: str) -> float:
       """Get the beta for a ticker."""
       stock_data = self.load_market_data(ticker)
       return stock_data.beta

   def get_volatility(self, ticker: str) -> float:
       """Get the volatility for a ticker."""
       stock_data = self.load_market_data(ticker)
       return stock_data.volatility
   ```

3. **Error Handling Consistency**

   **Challenge**: Existing code has specific error handling patterns.

   **Solution**: Maintain the same error handling patterns in StockDataService:

   ```python
   def get_beta(self, ticker: str) -> float:
       try:
           stock_data = self.load_market_data(ticker)
           if stock_data.beta is None:
               return 1.0  # Same fallback as current code
           return stock_data.beta
       except Exception as e:
           logger.warning(f"Could not calculate beta for {ticker}: {e}")
           return 1.0  # Same fallback as current code
   ```

4. **Testing Considerations**

   **Challenge**: The current code has tests that mock StockOracle.

   **Solution**: Design StockDataService to be easily mockable:

   ```python
   # Make the oracle injectable for testing
   def __init__(self, oracle=None):
       self._oracle = oracle or StockOracle.get_instance()
   ```

5. **Caching Behavior Differences**

   **Challenge**: StockOracle has its own caching, and StockDataService adds another layer.

   **Solution**: Consider these options:

   - Disable StockOracle's internal caching when used by StockDataService
   - Use StockOracle's cache as the source of truth and only add memory caching in StockDataService
   - Implement a coordinated caching strategy

   **Recommendation**: Keep StockOracle's disk caching for API calls and add memory caching in StockDataService for faster access.

### Implementation Strategy

To minimize disruption, we'll implement the integration in phases:

1. **Phase 1: Create the New Components**
   - Implement StockData and StockDataService classes
   - Create a global instance similar to stockdata
   - Implement full API compatibility with StockOracle
   - Add comprehensive unit tests

2. **Phase 2: Gradual Integration**
   - Start with one module (e.g., portfolio_service.py)
   - Replace direct stockdata calls with stock_service calls
   - Run tests to ensure behavior is identical
   - Proceed to the next module

3. **Phase 3: Refine and Optimize**
   - Analyze performance and caching behavior
   - Adjust caching parameters based on real-world usage
   - Consider adding persistence for the cache

### Code Changes Required

Here's a summary of the specific changes needed:

1. **New Files**:
   - `src/folib/data/stock_data.py`: Contains StockData and StockDataService classes

2. **Modified Files**:
   - `src/folib/services/portfolio_service.py`: Replace stockdata with stock_service
   - `src/folib/calculations/exposure.py`: Update to work with StockDataService
   - `src/folib/data/__init__.py`: Export stock_service

3. **Test Files**:
   - `tests/folib/data/test_stock_data.py`: Unit tests for the new components

### Future Extensions

This design can be extended in several ways:

1. **Add Fundamental Data**:
   - Expand StockData with financial statement fields
   - Add methods to StockDataService to load this data

2. **Persistence**:
   - Add methods to save/load the cache to/from disk
   - Implement more sophisticated caching strategies

3. **Advanced Calculations**:
   - Add methods to calculate derived metrics
   - Potentially integrate with FinanceToolkit for complex calculations

By following this plan, we'll create a simple but extensible foundation for managing stock data that can grow with our application's needs.
