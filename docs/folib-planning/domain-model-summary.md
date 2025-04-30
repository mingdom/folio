# Domain Model Simplification Summary

## Overview

This document summarizes the proposed changes to simplify the domain model in `src/folib/domain.py` and provides a high-level implementation plan.

## Current Issues

1. **Complex Grouping**: `PortfolioGroup` adds an unnecessary layer of abstraction
2. **Redundant Classes**: Multiple position classes with overlapping fields
3. **Rigid Structure**: Hard to work with positions directly

## Proposed Solution

1. **Eliminate `PortfolioGroup`**: Replace with a flat list of positions in the Portfolio class
2. **Consolidate Position Classes**: Create a clearer hierarchy with a base `Position` class
3. **Add Helper Functions**: Implement functions in `portfolio_service.py` for grouping and lookups

## Key Changes

1. **Updated Position Hierarchy**:
   - Base `Position` class with common fields
   - Concrete implementations: `StockPosition`, `OptionPosition`, `CashPosition`, `UnknownPosition`
   - Each position knows its type via the `position_type` field

2. **Simplified Portfolio Class**:
   - Contains a flat list of positions
   - Properties for accessing positions by type
   - No more nested groups

3. **Helper Functions**:
   - `group_positions_by_ticker`: Group positions by ticker symbol
   - `get_positions_by_ticker`: Get all positions for a specific ticker
   - `get_stock_position_by_ticker`: Get the stock position for a specific ticker
   - `get_option_positions_by_ticker`: Get all option positions for a specific ticker
   - `get_positions_by_type`: Get all positions of a specific type

## Benefits

1. **Simpler Data Model**: Fewer classes and clearer relationships
2. **More Flexible**: Easier to work with positions directly
3. **Better Performance**: Dictionary-based lookups for faster access
4. **More Maintainable**: Less code to understand and modify
5. **More Extensible**: Easier to add new position types or attributes

## Implementation Plan

### Phase 1: Update Domain Models (1-2 days)
- [ ] Update `Position`, `StockPosition`, and `OptionPosition` classes
- [ ] Add `CashPosition` and `UnknownPosition` classes
- [ ] Create new `Portfolio` class without `PortfolioGroup`
- [ ] Keep `PortfolioHolding` for backward compatibility

### Phase 2: Update Portfolio Service (1-2 days)
- [ ] Add helper functions for grouping and filtering positions
- [ ] Update `process_portfolio` to work with the new model
- [ ] Remove `create_portfolio_groups` function
- [ ] Update `create_portfolio_summary` to work with flat position list

### Phase 3: Update Consumers (2-3 days)
- [ ] Identify all code that depends on `PortfolioGroup`
- [ ] Update to use the new helper functions instead
- [ ] Run tests to ensure everything works correctly

### Phase 4: Cleanup (1 day)
- [ ] Remove `PortfolioGroup` class once all consumers are updated
- [ ] Update documentation
- [ ] Final testing

## Timeline

Estimated total time: 5-8 days

## Conclusion

This simplification will make the codebase easier to understand, maintain, and extend. The helper functions in `portfolio_service.py` will provide the same functionality as `PortfolioGroup` but with more flexibility and less complexity.
