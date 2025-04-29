# Code Review Guidelines

This document captures key principles and examples of good code design from our codebase reviews.

## Core Principles

1. **Code Reuse Above All Else**
2. **DRY (Don't Repeat Yourself)**
3. **Single Responsibility Principle**
4. **Fail Fast**
5. **Simplicity Over Complexity**
6. **Avoid Special Case Logic**
7. **Predictable Behavior**
8. **No Silent Fallbacks**

## Examples of Good Design

### Example 1: Method Reuse in StockOracle

In `src/folib/data/stock.py`, we have a perfect example of effective code reuse:

```python
def get_price(self, ticker: str) -> float:
    """
    Get the current price for a ticker.

    This method fetches the latest closing price for the given ticker
    using the Yahoo Finance API.

    Args:
        ticker: The ticker symbol

    Returns:
        The current price
    """
    return self.get_historical_data(ticker, period="1d")["Close"].iloc[-1]
```

This implementation demonstrates several key principles:

1. **Maximum Code Reuse**: Instead of duplicating validation and data fetching logic, it reuses the existing `get_historical_data` method.

2. **Centralized Validation**: All validation logic is concentrated in `get_historical_data`, so when that method is improved, `get_price` automatically benefits.

3. **Single Responsibility**: Each method has a clear purpose:
   - `get_historical_data`: Handles data fetching, validation, and error handling
   - `get_price`: Simply extracts the specific piece of information needed

4. **Maintainability**: Changes to data fetching or validation logic only need to be made in one place.

5. **Simplicity**: The implementation is just one line of actual code, making it easy to understand and maintain.

### Example 2: Clean Validation Without Special Cases

When adding validation to methods, keep it simple and generic:

```python
# GOOD: Simple, generic validation
def get_historical_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Get historical price data for a ticker.

    [docstring...]
    """
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    # Simple, generic validation that applies to all tickers
    if not self.is_valid_stock_symbol(ticker):
        raise ValueError(f"Invalid stock symbol format: {ticker}")

    # Direct call to the external API without special cases
    ticker_data = yf.Ticker(ticker)
    df = ticker_data.history(period=period)

    if df.empty:
        raise ValueError(f"No historical data available for {ticker}")

    return df
```

This approach:
- Applies validation consistently to all inputs
- Has predictable behavior without special cases
- Maintains a clear, direct relationship with the external API
- Follows the "fail fast" principle with early validation

## Anti-Patterns to Avoid

### Anti-Pattern 1: Duplicated Logic

```python
# DON'T DO THIS: Duplicated logic
def get_price(self, ticker: str) -> float:
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    # Duplicate validation logic
    if not self.is_valid_stock_symbol(ticker):
        raise ValueError(f"Invalid stock symbol format: {ticker}")

    # Duplicate special case handling
    if self.is_cash_like(ticker):
        return 1.0

    # Duplicate data fetching logic
    ticker_data = yf.Ticker(ticker)
    df = ticker_data.history(period="1d")

    if df.empty:
        raise ValueError(f"No price data available for {ticker}")

    price = df.iloc[-1]["Close"]

    if price <= 0:
        raise ValueError(f"Invalid stock price ({price}) for {ticker}")

    return price
```

### Anti-Pattern 2: Excessive Special Case Logic

```python
# DON'T DO THIS: Special case logic and synthetic data
def get_historical_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    # Special case for market index
    if ticker == self.market_index:
        # Always allow the market index (SPY) to pass through
        pass
    # Special case for cash-like positions
    elif self.is_cash_like(ticker):
        # Creating synthetic data that doesn't come from the API
        logger.debug(f"Creating synthetic historical data for cash-like position: {ticker}")
        dates = pd.date_range(end=pd.Timestamp.now(), periods=10)
        df = pd.DataFrame(
            {
                "Open": [1.0] * 10,
                "High": [1.0] * 10,
                "Low": [1.0] * 10,
                "Close": [1.0] * 10,
                "Volume": [0] * 10,
            },
            index=dates,
        )
        return df
    # Another special case
    elif not self.is_valid_stock_symbol(ticker):
        logger.warning(f"Invalid stock symbol format: {ticker}")
        raise ValueError(f"Invalid stock symbol format: {ticker}")

    # Finally, the actual API call
    ticker_data = yf.Ticker(ticker)
    df = ticker_data.history(period=period)

    if df.empty:
        raise ValueError(f"No historical data available for {ticker}")

    return df
```

### Anti-Pattern 3: Silent Fallbacks and Error Hiding

```python
# DON'T DO THIS: Silent fallbacks and error hiding
def get_historical_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    # Check cache first
    cache_path = self._get_cache_path(ticker, period)
    try:
        # Try to use cache
        if os.path.exists(cache_path):
            logger.info(f"Loading {ticker} data from cache")
            return pd.read_csv(cache_path, index_col=0, parse_dates=True)
    except Exception as e:
        # Silently ignore cache errors
        logger.warning(f"Error reading cache for {ticker}: {e}")

    # Fetch from API
    try:
        logger.info(f"Fetching data for {ticker} from API")
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period=period)

        # Save to cache
        try:
            df.to_csv(cache_path)
        except Exception as e:
            # Silently ignore cache write errors
            logger.warning(f"Error writing cache for {ticker}: {e}")

        return df
    except Exception as e:
        # Try to use expired cache as fallback
        if os.path.exists(cache_path):
            logger.warning(f"API error, using expired cache as fallback: {e}")
            try:
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)
            except Exception:
                pass  # Silently ignore fallback errors

        # If all else fails, return empty DataFrame instead of raising the error
        logger.error(f"Failed to get data for {ticker}: {e}")
        return pd.DataFrame()  # Silent fallback to empty DataFrame
```

Problems with this approach:
- Hides errors from the caller, making debugging difficult
- Returns potentially invalid data (empty DataFrame) instead of failing
- Creates complex, unpredictable control flow with multiple fallback paths
- Makes it hard to understand when and why failures occur
- Violates the "fail fast" principle by attempting to recover silently
- Increases code complexity with multiple nested try/except blocks
- Makes the code harder to understand and maintain
- Complicates testing by introducing multiple branches and special cases
- Violates the principle of least surprise - users expect a wrapper to the API, not synthetic data

## Key Takeaways

1. **Identify Reuse Opportunities**: Always look for opportunities to reuse existing methods rather than duplicating logic.

2. **Centralize Validation**: Concentrate validation and error handling in one place, typically at the lowest level of abstraction.

3. **Avoid Special Cases**: Keep code generic and consistent. Special case logic makes code harder to understand and maintain.

4. **Respect Method Contracts**: Methods should do what their name and documentation suggest, without surprising behavior.

5. **Keep It Simple**: Simple, straightforward code is easier to understand, test, and maintain.

6. **Be Predictable**: Code should behave predictably for all valid inputs.

7. **Consider Future Maintenance**: Code that follows these principles is easier to maintain, extend, and debug.

Remember: The best code is often the code you don't have to write because you've effectively reused what already exists.
