# Revised Plan: Disable Price Updates by Default in Portfolio Loading

## Date
2025-05-08

## Author
AI Assistant

## WHY
The goal is to reduce unnecessary API calls when loading portfolios. Currently, price updates are enabled by default in both CLI and web UI, which consumes API quota even when we already have valid prices from the portfolio data. By making price updates opt-in rather than opt-out, we can conserve API usage while still ensuring that necessary data (like underlying prices for unpaired options) is available when needed.

## WHAT
We need to modify how price updates are handled when loading portfolios to make them opt-in rather than opt-out. Based on user feedback, we'll:

1. Use the raw values from the portfolio CSV as provided by the loader first
2. Ensure that if an option is paired with an underlying stock, the option's underlying price should match the stock's price
3. Move price updates to a separate function that's controlled by a flag, defaulting to off

## HOW

### Current Architecture Analysis
1. `src/folib/data/loader.py` parses CSV data into `PortfolioHolding` objects with raw price data
2. `src/folib/services/portfolio_service.py` processes these holdings into a structured `Portfolio`
3. Currently, `update_prices` parameter exists but is not implemented (marked as reserved for future)
4. The `MarketDataProvider` class provides price data but isn't being used selectively

### Proposed Architecture

#### 1. Core Library Changes (`src/folib/services/portfolio_service.py`)

**A. Refactor `process_portfolio` function:**
```python
def process_portfolio(
    holdings: list[PortfolioHolding],
    update_prices: bool = False,  # Change default to False
) -> Portfolio:
    """
    Process raw portfolio holdings into a structured portfolio.

    [existing docstring...]

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()
        update_prices: Whether to update prices from market data (default: False)
                      When False, only updates prices for unpaired options
                      to ensure accurate exposure calculations.
    """
    # 1. Categorize holdings (cash, unknown, non-cash)
    # 2. Create positions from holdings (stocks, options, etc.)
    # 3. Handle paired options and stocks
    # 4. Conditionally update prices
    # 5. Return portfolio
```

**B. Create helper functions for better separation of concerns:**

```python
def _categorize_holdings(holdings: list[PortfolioHolding]) -> tuple[list, list, list, float]:
    """Categorize holdings into cash, unknown, and non-cash positions."""
    # Implementation...

def _create_stock_positions(non_cash_holdings: list[PortfolioHolding]) -> list[StockPosition]:
    """Create stock positions from non-cash holdings."""
    # Implementation...

def _create_option_positions(non_cash_holdings: list[PortfolioHolding]) -> list[OptionPosition]:
    """Create option positions from non-cash holdings."""
    # Implementation...

def _identify_unpaired_options(positions: list[Position]) -> list[OptionPosition]:
    """Identify options that don't have a matching stock position."""
    # Implementation...

def _update_unpaired_option_prices(unpaired_options: list[OptionPosition]) -> None:
    """Update underlying prices for unpaired options."""
    # Implementation...

def _update_all_prices(positions: list[Position]) -> None:
    """Update prices for all positions."""
    # Implementation...
```

**C. Implement price synchronization for paired options:**

```python
def _synchronize_option_underlying_prices(positions: list[Position]) -> None:
    """
    Ensure options use the same underlying price as their paired stocks.

    For each option, if there's a matching stock position (same ticker),
    set the option's underlying_price to match the stock's price.
    """
    # Implementation...
```

#### 2. Portfolio Processing Flow

1. Parse raw CSV data using `loader.py` (keeping original prices)
2. Categorize holdings and create positions
3. Synchronize option underlying prices with paired stocks
4. Only update prices for unpaired options by default
5. Optionally update all prices if `update_prices=True`

#### 3. Interface Changes

**A. CLI Interface (`src/cli/commands/utils.py`):**
```python
def load_portfolio(file_path: str, update_prices: bool = False) -> Portfolio:
    """
    Load a portfolio from a CSV file.

    Args:
        file_path: Path to the portfolio CSV file
        update_prices: Whether to update prices from market data (default: False)
    """
    # Implementation...
```

**B. Web UI Interface (`src/folio/app.py`):**
```python
# Update portfolio loading to default to False
portfolio = process_portfolio_data(df, update_prices=False)
```

**C. Core Data Processing (`src/folio/portfolio.py`):**
```python
def process_portfolio_data(df: pd.DataFrame, update_prices: bool = False) -> Portfolio:
    """
    Process portfolio data from a DataFrame into a structured portfolio.

    Args:
        df: DataFrame with portfolio data
        update_prices: Whether to update prices from market data (default: False)
                      When False, only updates prices for unpaired options.
    """
    # Implementation...
```

### Implementation Strategy

1. **Phase 1: Core Library Refactoring**
   - Refactor `process_portfolio` in `portfolio_service.py`
   - Implement helper functions for better separation of concerns
   - Add logic to synchronize option underlying prices with paired stocks
   - Add selective price updates for unpaired options

2. **Phase 2: Interface Updates**
   - Update `process_portfolio_data` in `portfolio.py` to default to `False`
   - Update `load_portfolio` in `utils.py` to default to `False`
   - Update portfolio loading in `app.py` to default to `False`

3. **Phase 3: Testing and Validation**
   - Add unit tests for the new functionality
   - Test with real portfolios to ensure correct behavior
   - Verify that API calls are minimized

### Logging Enhancements

Add detailed logging to inform users about price update operations:

```python
# When updating all prices
logger.info("Updating all position prices from market data")

# When updating only unpaired options
logger.info("Updating prices for %d unpaired options", len(unpaired_options))

# When synchronizing option prices with stocks
logger.debug("Synchronizing option underlying prices with paired stocks")

# When skipping price updates
logger.debug("Using raw prices from portfolio data (update_prices=False)")

# When encountering missing prices
logger.warning("Position %s has missing or zero price", position.ticker)
```

## Benefits of This Approach

1. **Improved Performance**: Minimizes API calls by default
2. **Better Data Consistency**: Ensures paired options and stocks use the same underlying price
3. **Clear Separation of Concerns**: Breaks down the portfolio processing into logical steps
4. **Opt-in Flexibility**: Users can still get fresh market data when needed
5. **Transparent Operation**: Enhanced logging keeps users informed

## Answers to Open Questions

1. **Command-line flag**: Not implementing initially, but can be added later if needed
2. **Missing/zero prices**: Will log warnings but use the values as-is unless update_prices=True
3. **Logging**: Adding comprehensive logging as outlined above
4. **Smart updates**: Not implementing initially to keep the solution focused

## Next Steps After Implementation

1. Monitor API usage to confirm reduction
2. Gather user feedback on the new behavior
3. Consider adding a UI toggle for price updates in the web interface
4. Document the new behavior in the user guide
