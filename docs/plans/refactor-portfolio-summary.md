# Refactoring Portfolio Summary Calculation

## WHY

The current implementation of portfolio summary calculation is spread across multiple files and modules, making it difficult to maintain and understand. Specifically:

1. The `src/folib/calculations/portfolio.py` module contains only two small functions that are only used in `portfolio_service.py`
2. The portfolio beta calculation is hardcoded to 1.0, which is inaccurate
3. The `PortfolioSummary` class has been updated with new fields (`net_exposure_pct` and `beta_adjusted_exposure`) that need proper calculation
4. Having calculation logic spread across multiple files creates unnecessary complexity

By consolidating all portfolio summary calculation logic into a single function in `src/folib/services/portfolio_service.py`, we can:
- Simplify the codebase by reducing the number of files and imports
- Ensure consistent calculation of portfolio metrics
- Properly implement the new fields in the `PortfolioSummary` class
- Make the code easier to understand and maintain

## WHAT: Scope of the Change

### Files to Modify:

1. **src/folib/services/portfolio_service.py**
   - Update `create_portfolio_summary` function to include all calculation logic
   - Implement proper calculation for `net_exposure_pct` and `beta_adjusted_exposure`
   - Remove imports from `calculations/portfolio.py`

2. **tests/folib/services/test_portfolio_service.py**
   - Update tests for `create_portfolio_summary` to verify new calculations
   - Add tests for the new fields in `PortfolioSummary`

### Files to Remove:

1. **src/folib/calculations/portfolio.py**
   - Remove this file entirely as its functions will be moved to `portfolio_service.py`

2. **tests/folib/calculations/test_portfolio.py**
   - Remove this file as its tests will be moved to `test_portfolio_service.py`

### Files to Update:

1. **src/folib/calculations/__init__.py**
   - Remove imports and exports of functions from `portfolio.py`

## HOW: Implementation Plan

### Phase 1: Prepare Tests

1. Move tests from `tests/folib/calculations/test_portfolio.py` to `tests/folib/services/test_portfolio_service.py`
2. Update the tests to reflect the new structure and expectations
3. Add tests for the new fields in `PortfolioSummary` (`net_exposure_pct` and `beta_adjusted_exposure`)

### Phase 2: Consolidate Calculation Logic

1. Move the functionality of `create_value_breakdowns` and `calculate_portfolio_metrics` into the `create_portfolio_summary` function in `portfolio_service.py`
2. Implement proper calculation for `net_exposure_pct` as `net_market_exposure / total_value` (handling zero division)
3. Implement proper calculation for `beta_adjusted_exposure` as the sum of beta-adjusted exposures of all positions
4. Remove imports from `calculations/portfolio.py`

### Phase 3: Update Portfolio Summary Creation

1. Update the `create_portfolio_summary` function to return a `PortfolioSummary` object with all required fields
2. Ensure all calculations are done within this function
3. Verify that the function handles edge cases (zero values, missing data, etc.)

### Phase 4: Clean Up

1. Remove the `src/folib/calculations/portfolio.py` file
2. Update `src/folib/calculations/__init__.py` to remove references to the removed functions
3. Run all tests to ensure everything works correctly

### Phase 5: Documentation

1. Update docstrings in `create_portfolio_summary` to reflect the new implementation
2. Add comments explaining the calculation of `net_exposure_pct` and `beta_adjusted_exposure`

## Implementation Details

### New `create_portfolio_summary` Function Structure

The refactored `create_portfolio_summary` function will:

1. Process all positions in the portfolio to calculate:
   - Long stock value and exposure
   - Short stock value and exposure
   - Long option value and exposure
   - Short option value and exposure
   - Cash value
   - Unknown value
   - Beta-adjusted exposure for each position

2. Calculate summary metrics:
   - Total value (sum of all position values plus pending activity)
   - Stock value (long + short)
   - Option value (long + short)
   - Net market exposure (sum of all exposures)
   - Net exposure percentage (net_market_exposure / total_value)
   - Beta-adjusted exposure (sum of all beta-adjusted exposures)

3. Return a `PortfolioSummary` object with all calculated values

### Calculation of Beta-Adjusted Exposure

The beta-adjusted exposure will be calculated as:

```python
beta_adjusted_exposure = 0.0

# For stock positions
for position in portfolio.stock_positions:
    # Skip cash-like positions
    if not is_cash_like(position):
        beta = get_beta(position.ticker) or 1.0  # Default to 1.0 if beta not available
        market_exposure = position.quantity * position.price
        beta_adjusted = market_exposure * beta
        beta_adjusted_exposure += beta_adjusted

# For option positions
for position in portfolio.option_positions:
    beta = get_beta(position.ticker) or 1.0  # Default to 1.0 if beta not available
    delta = calculate_option_delta(...)
    market_exposure = calculate_option_exposure(...)
    beta_adjusted = market_exposure * beta
    beta_adjusted_exposure += beta_adjusted
```

### Calculation of Net Exposure Percentage

The net exposure percentage will be calculated as:

```python
net_exposure_pct = (net_market_exposure / total_value) if total_value > 0 else 0.0
```

This represents the percentage of the portfolio that is exposed to market movements.

## Testing Strategy

1. Test with various portfolio compositions:
   - All long positions
   - Mix of long and short positions
   - With and without options
   - With and without cash positions
   - With and without pending activity

2. Test edge cases:
   - Empty portfolio
   - Portfolio with only cash
   - Portfolio with zero total value
   - Portfolio with missing betas

3. Verify calculations:
   - Ensure net_exposure_pct is correctly calculated
   - Ensure beta_adjusted_exposure is the sum of all position beta-adjusted exposures
   - Compare results with the old implementation to ensure consistency

## Risks and Mitigations

1. **Risk**: Breaking existing functionality
   **Mitigation**: Comprehensive test coverage before and after changes

2. **Risk**: Incorrect calculation of new fields
   **Mitigation**: Add specific tests for these calculations and verify with manual calculations

3. **Risk**: Performance impact of consolidating logic
   **Mitigation**: Profile the function before and after changes to ensure no significant performance degradation
