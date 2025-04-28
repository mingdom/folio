# Fix Simulation Display Issues

## WHY
The `make sim` command is not reflecting changes to the calculation logic in the displayed results. This suggests there may be issues with error handling, fallback logic, or caching that are preventing the updated calculations from being properly displayed.

## WHAT
This document outlines the findings from analyzing the `make sim` code path and identifies potential issues that could be causing the simulation results to remain unchanged despite logic updates.

## HOW

### Identified Issues

#### 1. SPY Price Fallback Logic in Display Function
In `src/focli/commands/sim.py`, the `display_simulation_results` function contains problematic error handling:

```python
# Get current SPY price
try:
    import yfinance as yf

    spy_data = yf.Ticker("SPY")
    current_spy_price = spy_data.history(period="1d")["Close"].iloc[-1]
except Exception:
    # If there's an error getting the price, use a default value
    current_spy_price = 500.0  # Default SPY price
    console.print(
        "[yellow]Warning: Could not get current SPY price. Using default value.[/yellow]"
    )
```

This is a classic example of bad fallback logic. If there's an error fetching the SPY price, it silently falls back to a hardcoded value of 500.0 without failing. This means that if there are network issues or API problems, you'll still see results but they'll be based on incorrect data.

#### 2. Extensive Caching in YFinance Wrapper
The project has a custom `YFinanceDataFetcher` class in `src/yfinance.py` that implements aggressive caching:

```python
# Check cache first
cache_path = self._get_cache_path(ticker, period, interval)

# Use the centralized cache validation logic
from src.stockdata import should_use_cache

should_use, reason = should_use_cache(cache_path, self.cache_ttl)

if should_use:
    logger.info(f"Loading {ticker} data from cache: {reason}")
    try:
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)
    except Exception as e:
        logger.warning(f"Error reading cache for {ticker}: {e}")
        # Continue to fetch from API
```

Even more concerning, there's a fallback to expired cache on network errors:

```python
# Only use expired cache for expected data errors, not for programming errors
if os.path.exists(cache_path):
    logger.warning(f"Using expired cache for {ticker} as fallback")
    try:
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as cache_e:
        logger.error(f"Error reading cache for {ticker}: {cache_e}")
        # Re-raise the original error since cache fallback failed
        raise e from cache_e
```

This means that even if the network is down or the API is unavailable, the system will still use potentially stale data from the cache.

#### 3. Zero Index Calculation Issue
In `simulator_v2.py`, there's a potential issue with how the zero index is calculated:

```python
# Find the index of 0% SPY change to use as baseline
# If 0% is not in the list, we'll calculate baseline values separately
zero_index = None
for i, change in enumerate(spy_changes):
    if abs(change) < 0.001:  # Close to 0%
        zero_index = i
        break

# Simulate for each SPY change
for spy_change in spy_changes:
    # ...simulation code...

baseline_value = portfolio_values[zero_index]
```

If there's no SPY change close to 0% in the list, `zero_index` will remain `None`, which would cause an error when used later. However, the code doesn't check if `zero_index` is still `None` before using it.

#### 4. Limited SPY Change Range in Makefile
The Makefile's `sim` target uses a very limited range of SPY changes:

```makefile
$(POETRY) run python -m src.focli.commands.sim @private-data/private-portfolio.csv --min-spy-change -0.1 --max-spy-change 0.1 --steps 5 $(if $(ticker),--ticker $(ticker),) $(if $(detailed),--detailed,);
```

With only 5 steps between -10% and +10%, it's possible that none of the steps are exactly 0%, which could trigger the zero_index issue mentioned above.

#### 5. Potential Caching in `marketdata.py`
While `marketdata.py` itself doesn't implement caching, it uses the `yfinance` library which might be caching results internally:

```python
def get_stock_price(ticker: str) -> float:
    """
    Get the current stock price for a ticker using YFinance.
    """
    try:
        # Fetch the latest data for the ticker
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period="1d")
```

If `yfinance` is caching data internally, you might still get stale prices even if your calculation logic changes.

### Recommended Fixes

1. **Remove SPY Price Fallback Logic**: Modify the `display_simulation_results` function to fail fast when it can't get the current SPY price, rather than silently using a default value.

2. **Disable or Clear Cache**: Add a flag to force fresh data retrieval from yfinance, bypassing any potential caching. This could be a `--no-cache` option for the `sim` command.

3. **Fix Zero Index Handling**: Ensure that the zero index calculation handles the case where no SPY change is close to 0%.

4. **Increase SPY Change Range and Steps**: Update the Makefile to use a wider range of SPY changes and more steps to ensure a 0% point is included.

5. **Add Debug Logging**: Add more logging to trace the execution path and values at key points in the simulation.

### Testing Plan

1. **Direct CLI Invocation**: Try running the simulation directly via the CLI rather than through the Makefile to see if the issue persists.

2. **Test with Simple Portfolio**: Create a simple test portfolio with known values to verify the simulation logic.

3. **Check for Cached Files**: Look for any cached files in the project directory that might be affecting the results.

4. **Add Temporary Debug Prints**: Add temporary print statements at key points in the code to see what values are being used:
   - Print the SPY changes being used
   - Print the portfolio values after simulation
   - Print the zero_index value to ensure it's not None

### Implementation Strategy

1. First, add debug logging to understand what's happening without changing behavior.
2. Fix the zero index calculation issue to ensure it handles the case where no SPY change is close to 0%.
3. Remove the SPY price fallback logic to ensure we're using accurate data.
4. Add a `--no-cache` option to force fresh data retrieval.
5. Update the Makefile to use a wider range of SPY changes and more steps.
