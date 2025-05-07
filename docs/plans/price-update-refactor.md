# Price Update Refactor Plan

## Overview

This document outlines the plan to refactor the price update mechanism in the Folio application to add a flag that can turn off price updates. The goal is to:

1. Use the price from the portfolio CSV file for positions that have a price
2. Only fetch prices for option positions where we don't have the underlying price (even when price updates are generally disabled)
3. Make "no price updates" the default behavior for both CLI and web app (folio)
4. Fail fast when required prices cannot be fetched (especially for option underlying prices)

## Current Implementation Analysis

### Price Update Flow

The current price update flow involves several components:

1. **Portfolio Loading and Processing**:
   - In `src/folio/portfolio.py`, the `process_portfolio_data()` function has an `update_prices` parameter (default: `True`)
   - When `update_prices=True`, it calls `update_all_prices()` to fetch current market prices for all positions
   - In `src/folib/services/portfolio_service.py`, there's a similar `process_portfolio()` function with an `update_prices` parameter, but it's currently not used (marked with `# noqa: ARG001`)
   - In `src/folio/app.py`, the web app calls `process_portfolio_data()` with `update_prices=True` hardcoded

2. **Price Update Functions**:
   - `update_portfolio_prices()`: Updates prices for all positions in portfolio groups
   - `update_zero_price_positions()`: Updates only positions with zero prices
   - `update_all_prices()`: Updates prices for all positions by fetching current market prices

3. **CSV Processing**:
   - During CSV processing in `process_portfolio_data()`, prices are read from the "Last Price" column
   - If the price is missing or zero, the code attempts to fetch the current price using `stockdata.get_price()`

4. **Option Position Handling**:
   - Option positions require the underlying stock price for calculations
   - In `_get_option_market_data()` and other functions, the code fetches the underlying price using `stockdata.get_price()`

### CLI Integration

- The CLI commands in `src/cli/commands/portfolio.py` and `src/cli/commands/position.py` don't currently expose the `update_prices` parameter
- The `load_portfolio()` utility function in `src/cli/commands/utils.py` doesn't pass any price update configuration to the underlying functions

## Refactoring Plan

### 1. Modify Core Library (`src/folio/`)

#### 1.1. Update `process_portfolio_data()` in `src/folio/portfolio.py`

- Enhance the existing `update_prices` parameter to control price update behavior
- Modify the price processing logic to:
  - Always use the price from the CSV if available and non-zero
  - Only fetch prices for positions with missing or zero prices when `update_prices=True`
  - For option positions, always fetch the underlying price if needed for calculations (even when `update_prices=False`)

#### 1.2. Refactor Price Update Functions

- Modify `update_all_prices()` to respect the `update_prices` flag
- Update `update_portfolio_prices()` to only update prices for positions that need it
- Ensure `update_zero_price_positions()` still works correctly with the new behavior

### 2. Update Service Layer (`src/folib/`)

#### 2.1. Implement `update_prices` in `process_portfolio()` in `src/folib/services/portfolio_service.py`

- Make the `update_prices` parameter functional (remove the `# noqa: ARG001` comment)
- Pass the parameter to the underlying portfolio processing functions

#### 2.2. Update Option Position Handling

- Modify `_get_option_market_data()` and related functions to:
  - Use the existing price from the portfolio if available
  - Always fetch the underlying price if it's not available, regardless of `update_prices` setting
  - This ensures option exposure calculations are always accurate

### 3. Update CLI Interface (`src/cli/`)

#### 3.1. Add Command-Line Option

- Add a `--update-prices` flag to relevant CLI commands in `src/cli/commands/portfolio.py` (default: `False`)
- Update the `load_portfolio()` utility function in `src/cli/commands/utils.py` to accept and pass the price update preference
- Make "no price updates" the default behavior for all CLI commands

#### 3.2. Update Interactive Shell

- Add support for the price update preference in the interactive shell
- Update the state management to store the user's preference

## Implementation Details

### Core Changes

1. **`src/folio/portfolio.py`**:
   ```python
   def process_portfolio_data(
       df: pd.DataFrame,
       update_prices: bool = True,
   ) -> tuple[list[PortfolioGroup], PortfolioSummary, list[dict]]:
       # ...

       # Process price
       if pd.isna(row["Last Price"]) or row["Last Price"] in ("--", ""):
           # Missing price
           if is_known_cash:
               # Use default values for cash-like positions with missing price
               price = 0.0
               beta = 0.0
               is_cash_like = True
           elif update_prices or is_option_symbol(symbol):
               # Fetch price if update_prices is True OR this is an option (we always need option underlying prices)
               try:
                   price = stockdata.get_price(symbol)
                   logger.info(f"Row {index}: Updated price for {symbol}: {price}")
               except Exception as e:
                   error_msg = f"Row {index}: Error fetching price for {symbol}: {e}"
                   logger.error(error_msg)
                   # Fail fast - especially important for options
                   raise ValueError(error_msg)
           else:
               # Skip positions with missing prices when update_prices is False and not an option
               logger.warning(f"Row {index}: Missing price for {symbol} and price updates disabled. Skipping.")
               continue
       else:
           price = clean_currency_value(row["Last Price"])
           if price < 0:
               logger.debug(f"Row {index}: {symbol} has negative price ({price}). Skipping.")
               continue
           elif price == 0 and (update_prices or is_option_symbol(symbol)):
               # Fetch price if it's zero AND (update_prices is True OR this is an option)
               try:
                   logger.debug(f"Row {index}: {symbol} has zero price. Attempting to fetch current price.")
                   price = stockdata.get_price(symbol)
                   logger.info(f"Row {index}: Updated price for {symbol}: {price}")
               except Exception as e:
                   error_msg = f"Row {index}: Error fetching price for {symbol}: {e}"
                   logger.error(error_msg)
                   # Fail fast - especially important for options
                   raise ValueError(error_msg)

       # ...

       # Update prices if requested
       if update_prices:
           logger.debug("Updating prices in portfolio groups...")
           groups = update_all_prices(groups)
   ```

2. **`src/folib/services/portfolio_service.py`**:
   ```python
   def process_portfolio(
       holdings: list[PortfolioHolding],
       update_prices: bool = True,
   ) -> Portfolio:
       # Implement the update_prices parameter
       # ...

   def _get_option_market_data(position: Position, update_prices: bool = True) -> tuple[float, float]:
       """
       Get market data (underlying price and beta) for an option position.

       Args:
           position: The option position
           update_prices: Whether to fetch current prices from market data

       Returns:
           Tuple of (underlying_price, beta)
       """
       # Always try to get the underlying price for options
       # This is necessary for accurate exposure calculations
       try:
           # First try to get the price from the market data
           underlying_price = stockdata.get_price(position.ticker)
           # Only get beta if we're doing full price updates
           beta = stockdata.get_beta(position.ticker) if update_prices else 1.0
           if update_prices is False and beta == 1.0:
               logger.warning(f"Using default beta of 1.0 for {position.ticker} as price updates are disabled")
       except Exception as e:
           # Fail fast - we need the underlying price for option calculations
           error_msg = f"Could not get underlying price for option {position.ticker}: {e}"
           logger.error(error_msg)
           raise ValueError(error_msg)

       return underlying_price, beta
   ```

3. **`src/cli/commands/utils.py`**:
   ```python
   def load_portfolio(file_path: str | None = None, update_prices: bool = False) -> dict:
       """
       Load portfolio data from a CSV file.

       Args:
           file_path: Path to the portfolio CSV file (optional)
           update_prices: Whether to update prices from market data

       Returns:
           Dictionary with loaded portfolio data

       Raises:
           FileNotFoundError: If the file doesn't exist
           ValueError: If the file is invalid
       """
       # ...

       # Process the portfolio
       console.print("Processing portfolio...")
       portfolio = process_portfolio(holdings, update_prices=update_prices)
       console.print(f"Processed portfolio with [bold]{len(portfolio.positions)}[/bold] positions")

       # ...
   ```

4. **`src/cli/commands/portfolio.py`**:
   ```python
   @portfolio_app.command("summary")
   def portfolio_summary_cmd(
       file_path: str | None = typer.Option(
           None, "--file", "-f", help="Path to the portfolio CSV file"
       ),
       update_prices: bool = typer.Option(
           False, "--update-prices", help="Update prices from market data"
       ),
   ):
       """Display high-level portfolio metrics."""
       try:
           # Load the portfolio
           result = load_portfolio(file_path, update_prices=update_prices)
           portfolio = result["portfolio"]

           # ...
   ```

## Testing Plan

1. **Unit Tests**:
   - Update existing tests to verify the behavior with `update_prices=False`
   - Add new tests for the modified price update functions
   - Test option position handling with and without price updates

2. **Integration Tests**:
   - Test the CLI commands with the new `--no-price-update` flag
   - Verify that the interactive shell correctly handles the price update preference

3. **Manual Testing**:
   - Test with a real portfolio CSV file with various price scenarios
   - Verify that option calculations work correctly with and without price updates

## Risks and Mitigations

1. **Risk**: Option calculations might be inaccurate without current market prices
   - **Mitigation**: Always fetch underlying prices for options, even when general price updates are disabled

2. **Risk**: Existing code might rely on prices being updated
   - **Mitigation**: Carefully review all code paths that use position prices
   - **Mitigation**: Ensure that the default behavior for CLI is consistent and well-documented

3. **Risk**: CLI interface changes might break existing scripts
   - **Mitigation**: Make the new flag optional with a sensible default
   - **Mitigation**: Document the change in behavior in the CLI help text

4. **Risk**: Performance might degrade if we fetch prices unnecessarily
   - **Mitigation**: Only fetch prices when absolutely necessary (e.g., for option underlying prices)
   - **Mitigation**: Consider implementing batch fetching for multiple tickers

## Files Affected

The following files will need to be modified:

1. **Core Library**:
   - `src/folio/portfolio.py`: Update price update logic in `process_portfolio_data()`, `update_portfolio_prices()`, `update_zero_price_positions()`, and `update_all_prices()`
   - `src/folio/app.py`: Update to use `update_prices=False` as the default when processing portfolio data

2. **Service Layer**:
   - `src/folib/services/portfolio_service.py`: Update `process_portfolio()` and `_get_option_market_data()`
   - `src/folib/services/position_service.py`: Update any functions that fetch prices for option calculations

3. **CLI Interface**:
   - `src/cli/commands/utils.py`: Update `load_portfolio()` to accept and use the `update_prices` parameter with default `False`
   - `src/cli/commands/portfolio.py`: Add `--update-prices` flag to relevant commands
   - `src/cli/commands/position.py`: Add `--update-prices` flag to relevant commands
   - `src/cli/shell.py`: Update to support the price update preference in interactive mode
   - `src/cli/state.py`: Update to store the price update preference

## Implementation Decisions

Based on the project's philosophy of failing fast and prioritizing correctness:

1. **Option Pricing Strategy**:
   - No fallbacks for option underlying prices - if we can't get the price, throw an error
   - This ensures we don't make calculations based on incorrect data

2. **Beta Calculation**:
   - Use a default beta value of 1.0 when price updates are disabled
   - Log a warning when using the default beta value
   - This provides a reasonable approximation while making it clear we're using a default

3. **Error Handling**:
   - Fail fast when required prices cannot be fetched
   - Especially critical for option underlying prices which are needed for exposure calculations
   - Clear error messages should indicate what failed and why

4. **Performance Considerations**:
   - Selectively fetching only option underlying prices should provide performance benefits
   - Consider implementing batch fetching for multiple tickers in a future enhancement

## Next Steps

1. Implement the changes in the core library (`src/folio/`)
2. Update the service layer (`src/folib/`)
3. Add the CLI interface changes
4. Update tests
5. Manual testing and validation
