# Stock Data Service Design (Final)

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
4. Maintaining backward compatibility with the existing StockOracle API (we'll make a clean break)

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

    def __init__(self, oracle=None):
        """Initialize the StockDataService.

        Args:
            oracle: Optional StockOracle instance. If None, the default instance will be used.
        """
        self._cache = {}  # ticker -> StockData
        self._oracle = oracle or StockOracle.get_instance()

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

### Integration Decisions

1. **Service Injection Approach**

   **Decision**: Use dependency injection rather than a global singleton.

   **Implementation**:
   - Design all functions that need stock data to accept a StockDataService parameter
   - Provide a default service at the module level for convenience
   - Encourage explicit service injection in new code

   ```python
   # In src/folib/data/stock_data.py
   default_stock_service = StockDataService()

   # In functions that use the service
   def calculate_portfolio_metrics(portfolio, stock_service=None):
       stock_service = stock_service or default_stock_service
       # Use stock_service...
   ```

2. **Breaking Changes Approach**

   **Decision**: Make a clean break from the old API rather than maintaining compatibility.

   **Implementation**:
   - Update all call sites to use the new API directly
   - Don't implement pass-through methods for backward compatibility
   - Document the migration path for any external code

3. **Caching Strategy**

   **Decision**: Only StockDataService will implement caching, removing redundant caching in StockOracle.

   **Implementation**:
   - Disable StockOracle's internal caching when used by StockDataService
   - StockDataService will handle all caching responsibilities
   - This simplifies the caching architecture and avoids potential inconsistencies

### Implementation Strategy

To minimize disruption, we'll implement the integration in phases:

1. **Phase 1: Create the New Components**
   - Implement StockData and StockDataService classes
   - Create unit tests for the new components
   - Document the new API

2. **Phase 2: Complete Integration**
   - Update all code that currently uses StockOracle to use StockDataService
   - Inject the service where needed rather than using a global singleton
   - Run tests to ensure behavior is identical

3. **Phase 3: Refine and Optimize**
   - Analyze performance and caching behavior
   - Adjust caching parameters based on real-world usage
   - Consider adding persistence for the cache

### Code Changes Required

Here's a summary of the specific changes needed:

1. **New Files**:
   - `src/folib/data/stock_data.py`: Contains StockData and StockDataService classes

2. **Modified Files**:
   - `src/folib/services/portfolio_service.py`: Update to use StockDataService
   - `src/folib/calculations/exposure.py`: Update to use StockDataService
   - `src/folib/data/__init__.py`: Export StockDataService and default instance

3. **Test Files**:
   - `tests/folib/data/test_stock_data.py`: Unit tests for the new components

### Final Decisions on Implementation Considerations

1. **Caching Strategy**
   - **Decision**: Only StockDataService will implement caching
   - **Implementation**: Disable or remove caching in StockOracle when used by StockDataService to avoid redundant caching
   - **Rationale**: Simplifies the caching architecture and avoids potential inconsistencies between cache layers

2. **Error Handling Strategy**
   - **Decision**: Follow existing error handling patterns as defined in `.refs/folib-planning/error-handling.md`
   - **Implementation**: Implement consistent error handling in StockDataService following established project patterns
   - **Rationale**: Maintains consistency across the codebase and leverages existing error handling best practices

3. **Testing Strategy**
   - **Decision**: Implement unit tests only for the initial launch
   - **Implementation**: Create comprehensive unit tests for StockData and StockDataService classes
   - **Follow-up**: Manual testing will be performed after initial implementation, with regression tests added for any bugs found

4. **Migration Approach**
   - **Decision**: Make a clean break with no backward compatibility
   - **Implementation**: Update all code to use the new API directly without transition period
   - **Rationale**: Project hasn't launched yet, so there are no external dependencies to consider

5. **Performance Considerations**
   - **Decision**: Performance is not a concern for V0
   - **Implementation**: Focus on correct functionality rather than optimization
   - **Follow-up**: Performance optimizations can be added in future versions if needed

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
