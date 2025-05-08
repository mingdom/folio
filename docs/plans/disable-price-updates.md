# Plan: Disable Price Updates by Default in Portfolio Loading

## Date
2025-05-08

## Author
AI Assistant

## WHY
The goal is to reduce unnecessary API calls when loading portfolios. Currently, price updates are enabled by default in both CLI and web UI, which consumes API quota even when we already have valid prices from the portfolio data. By making price updates opt-in rather than opt-out, we can conserve API usage while still ensuring that necessary data (like underlying prices for unpaired options) is available when needed.

## WHAT
We need to modify how price updates are handled when loading portfolios in both `src/cli` and `src/folio` modules to make them opt-in rather than opt-out. The only exception should be for fetching underlying prices for unpaired options where we don't already have the data.

## HOW

### Scope
This change will affect:
1. `src/folib/services/portfolio_service.py` - The `process_portfolio` function
2. `src/cli/commands/utils.py` - The `load_portfolio` function
3. `src/folio/portfolio.py` - The `process_portfolio_data` function
4. `src/folio/app.py` - The portfolio loading in the web UI
5. Any other code that relies on price updates during portfolio loading

### Current Implementation
1. In `src/folib/services/portfolio_service.py`, there's an `update_prices` parameter that's currently set to `True` by default but not actually used (marked as reserved for future implementation)
2. In `src/folio/portfolio.py`, the `process_portfolio_data` function has an `update_prices` parameter defaulting to `True`, which triggers `update_all_prices(groups)` when enabled
3. In `src/folio/app.py`, portfolio loading explicitly sets `update_prices=True`
4. The `MarketDataProvider` class provides price data but doesn't have a specific method for selective updates

### Proposed Changes
1. Modify `process_portfolio` in `src/folib/services/portfolio_service.py` to:
   - Implement the `update_prices` parameter functionality
   - Default it to `False`
   - Add logic to selectively update only unpaired option underlying prices

2. Update `process_portfolio_data` in `src/folio/portfolio.py` to:
   - Change default `update_prices` to `False`
   - Modify the update logic to be selective for unpaired options

3. Update `load_portfolio` in `src/cli/commands/utils.py` to:
   - Add an `update_prices` parameter defaulting to `False`
   - Pass this parameter to the portfolio service

4. Modify `src/folio/app.py` to:
   - Make price updates optional with a default of `False`
   - Add a UI toggle for users to explicitly request price updates

### Implementation Strategy
1. First, implement the changes in the core library (`src/folib`)
2. Then update the CLI interface (`src/cli`)
3. Finally, update the web UI (`src/folio`)
4. Add tests to verify the behavior works as expected

### Specific Approach for Unpaired Options
1. Detect unpaired options during portfolio processing
2. Only for these options, fetch the underlying price data
3. Implement a helper function to determine if an option is unpaired
4. Use the `MarketDataProvider` selectively for just these cases

## Assumptions
1. The current portfolio data loaded from CSV contains accurate price information
2. API calls are expensive and should be minimized
3. Users will explicitly opt-in to price updates when needed
4. Unpaired options are relatively rare in portfolios

## Open Questions
1. Should we add a command-line flag to enable price updates for CLI users?
2. How should we handle cases where the portfolio data has missing or zero prices?
3. Do we need to add logging to inform users when prices are being updated?
4. Should we implement a "smart" update that only updates prices older than a certain threshold?
