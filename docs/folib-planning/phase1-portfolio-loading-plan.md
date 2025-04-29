# Phase 1: Portfolio Loading Implementation Plan

## Overview

This document outlines the detailed implementation plan for Phase 1 of the folib migration, focusing on portfolio loading, processing, and CLI integration. The goal is to have a complete end-to-end flow from loading a portfolio CSV file to displaying the processed portfolio in the CLI.

## Goals

- Implement the core data loading functionality in `folib/data/`
- Implement the portfolio processing service in `folib/services/`
- Integrate with the CLI for portfolio loading and display
- Ensure all components work together seamlessly
- Maintain backward compatibility with existing portfolio CSV format

## Success Criteria

- A user can load a portfolio from a CSV file using the CLI
- The loaded portfolio is correctly processed and displayed
- All core position data (stocks, options) is correctly parsed and represented
- Cash positions and pending activity are correctly identified
- The implementation follows the functional programming principles outlined in the migration plan

## Timeline

- Estimated Duration: 2 weeks
- Start Date: TBD
- End Date: TBD

## Task Breakdown

### 1. Data Access Layer (Week 1, Days 1-3)

#### 1.1 Market Data Implementation

- [x] **Create `folib/data/stock.py`**

#### 1.2 Portfolio Loading Implementation

- [ ] **Complete `folib/data/loader.py`**
  - [ ] TODO: figure out details below

### 2. Portfolio Processing Layer (Week 1, Days 4-5)

#### 2.1 Basic Calculations

- [ ] **Create `folib/calculations/exposure.py`**
  - [ ] Implement `calculate_position_exposure(position)` function
  - [ ] Implement `calculate_beta_adjusted_exposure(position, beta)` function
  - [ ] Write unit tests

#### 2.2 Portfolio Service Implementation

- [ ] **Complete `folib/services/portfolio_service.py`**
  - [ ] Implement `process_portfolio(holdings, market_oracle)` function
  - [ ] Implement `create_portfolio_groups(holdings, market_oracle)` function
  - [ ] Implement `create_portfolio_summary(portfolio)` function (basic version)
  - [ ] Write unit tests

### 3. CLI Integration (Week 2, Days 1-3)

#### 3.1 CLI Command Updates

- [ ] **Update `focli/commands/portfolio.py`**
  - [ ] Refactor `load_portfolio` command to use folib
  - [ ] Update error handling and user feedback
  - [ ] Ensure backward compatibility with existing command syntax

#### 3.2 CLI Display Updates

- [ ] **Update `focli/formatters/portfolio.py`**
  - [ ] Create adapter functions to convert folib domain models to display format
  - [ ] Update portfolio display formatting
  - [ ] Ensure consistent styling with existing CLI

### 4. Testing & Refinement (Week 2, Days 4-5)

#### 4.1 Integration Testing

- [ ] **Create test portfolios**
  - [ ] Simple portfolio with stocks only
  - [ ] Complex portfolio with stocks and options
  - [ ] Edge cases (empty portfolio, invalid entries, etc.)

#### 4.2 End-to-End Testing

- [ ] **Test complete workflow**
  - [ ] Test loading portfolio from CSV
  - [ ] Test processing and grouping
  - [ ] Test summary calculation
  - [ ] Test CLI display

#### 4.3 Performance Optimization

- [ ] **Optimize critical paths**
  - [ ] Profile and identify bottlenecks
  - [ ] Implement caching for expensive operations
  - [ ] Optimize data structures for common operations

## Implementation Details

### Data Flow

The data flow for Phase 1 will be:

1. **Input**: CSV file (`portfolio-private.csv`)
2. **Loading**: `load_portfolio_from_csv()` → DataFrame
3. **Parsing**: `parse_portfolio_holdings()` → List of `PortfolioHolding` objects
4. **Processing**: `process_portfolio()` → `Portfolio` object with `PortfolioGroup` objects
5. **Summary**: `create_portfolio_summary()` → `PortfolioSummary` object
6. **Display**: CLI formatting and display

### Key Design Decisions

1. **Separation of Concerns**:
   - Data loading is separate from business logic
   - Domain models are separate from calculation functions
   - CLI formatting is separate from core functionality

2. **Error Handling Strategy**:
   - Follow "fail fast" approach for critical errors
   - Provide clear error messages for user-facing issues
   - Log detailed information for debugging

3. **Testing Strategy**:
   - Unit tests for individual functions
   - Integration tests for component interactions
   - End-to-end tests for complete workflow

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CSV format variations | High | Medium | Implement flexible parsing with fallbacks |
| Missing market data | Medium | Low | Add robust error handling and default values |
| Performance issues with large portfolios | Medium | Low | Implement caching and optimize critical paths |
| CLI integration issues | High | Medium | Maintain backward compatibility and thorough testing |

## Dependencies

- Python 3.10+
- pandas for CSV parsing
- yfinance for market data
- rich for CLI formatting

## Conclusion

This Phase 1 implementation plan provides a clear roadmap for implementing the portfolio loading functionality in the new folib architecture. By following this plan, we will establish a solid foundation for the remaining phases of the migration while delivering immediate value through CLI integration.

The focus on the "smallest chunk" approach ensures that we can complete and test each component before moving on, reducing risk and providing early feedback on the design decisions.
