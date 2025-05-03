# DCF Calculator Feature Design

**Version:** 1.0
**Date:** 2025-05-03
**Status:** Draft
**Author:** Augment Agent

## 1. Overview

This document outlines the design for adding a Discounted Cash Flow (DCF) calculator feature to the Folio suite. The feature will allow users to estimate the intrinsic value of a stock based on projected future cash flows, providing a fundamental valuation tool alongside existing portfolio analysis features.

The initial implementation will focus on the core library (`folib`) and CLI interface, with the web interface implementation deferred to a future phase.

## 2. Why We Need This Feature

### 2.1 Problem Statement

Currently, Folio provides portfolio analysis tools that focus on existing positions and their metrics (exposure, beta, etc.). However, it lacks tools for fundamental valuation that would help users make informed investment decisions based on a company's financial data and future prospects.

### 2.2 User Needs

Our users need to:
1. Estimate the intrinsic value of stocks they're considering for investment
2. Compare current market prices with calculated intrinsic values to identify potential opportunities
3. Understand the key drivers of a stock's value (growth rates, discount rates, etc.)
4. Perform sensitivity analysis by adjusting key parameters

### 2.3 Business Value

Adding DCF valuation capabilities will:
1. Enhance Folio's value proposition as a comprehensive investment analysis tool
2. Differentiate our product from competitors that focus solely on technical analysis or portfolio tracking
3. Appeal to value investors and fundamental analysts who rely on DCF models
4. Create opportunities for future premium features (e.g., automated DCF analysis for entire portfolios)

### 2.4 Strategic Alignment

This feature aligns with our strategy to:
1. Expand from portfolio tracking to investment decision support
2. Provide tools for both technical and fundamental analysis
3. Appeal to a broader range of investment styles and methodologies

## 3. What We're Building

### 3.1 Feature Scope

The DCF calculator will:
1. Fetch historical financial data from Financial Modeling Prep (FMP) API
2. Calculate historical growth rates for key metrics
3. Project future cash flows based on user-provided or calculated growth rates
4. Calculate terminal value using perpetuity growth or exit multiple methods
5. Discount projected cash flows to present value
6. Calculate intrinsic value per share
7. Provide a CLI interface for performing DCF calculations

Out of scope for this phase:
1. Web interface integration
2. Automated sensitivity analysis
3. Batch processing for multiple stocks
4. Integration with portfolio analysis

### 3.2 User Experience

#### CLI Interface

Users will interact with the DCF calculator through the CLI using commands like:

```
# Basic usage
folio> dcf calculate AAPL

# With custom parameters
folio> dcf calculate AAPL --metric FCF --years 5 --growth 0.15 --terminal-growth 0.03 --discount 0.1

# Show detailed calculation steps
folio> dcf calculate AAPL --show-calculation
```

The output will include:
1. Stock information (ticker, name, current price)
2. DCF calculation results (intrinsic value, upside/downside percentage)
3. Key inputs used (growth rates, discount rate, etc.)
4. Optional detailed calculation steps

### 3.3 Core Functionality

The DCF calculator will provide the following core functionality:

1. **Data Retrieval**:
   - Fetch historical financial data (cash flows, earnings, etc.) from FMP API
   - Retrieve shares outstanding and dividend history
   - Get current stock price and historical price/metric ratios

2. **Growth Rate Calculation**:
   - Calculate historical compound annual growth rates (CAGR) for key metrics
   - Provide default growth rates based on historical data
   - Allow user overrides for all growth parameters

3. **Cash Flow Projection**:
   - Project future values for the selected metric (FCF, Operating Cash Flow, Net Income)
   - Project future shares outstanding and dividends
   - Calculate terminal value using perpetuity growth or exit multiple methods

4. **Valuation Calculation**:
   - Discount projected cash flows to present value
   - Calculate intrinsic value per share
   - Compare with current market price
   - Calculate implied CAGR based on current price and future value

### 3.4 Data Model

The DCF calculator will use the following data structures:

1. **Input Parameters**:
   ```python
   @dataclass(frozen=True)
   class DCFParameters:
       ticker: str
       metric: str  # FCF, OCF, NetIncome
       projection_years: int
       growth_rate: float | None  # None means calculate from historical data
       terminal_growth_rate: float | None
       discount_rate: float
       shares_growth_rate: float | None
       dividend_growth_rate: float | None
   ```

2. **Historical Data**:
   ```python
   @dataclass(frozen=True)
   class HistoricalFinancials:
       years: list[int]
       metric_values: list[float]  # Values for the selected metric
       shares_outstanding: list[float]
       dividends_per_share: list[float]
       price_metric_ratios: list[float]
   ```

3. **Projection Data**:
   ```python
   @dataclass(frozen=True)
   class DCFProjection:
       years: list[int]
       projected_metric_values: list[float]
       projected_shares_outstanding: list[float]
       projected_dividends_per_share: list[float]
       terminal_value: float
       present_values: list[float]
   ```

4. **DCF Result**:
   ```python
   @dataclass(frozen=True)
   class DCFResult:
       parameters: DCFParameters
       historical_data: HistoricalFinancials
       projection: DCFProjection
       intrinsic_value: float
       current_price: float
       upside_downside_pct: float
       implied_cagr: float
   ```

### 3.5 Integration Points

The DCF calculator will integrate with the following existing components:

1. **Data Layer**:
   - Extend the FMP provider to fetch financial data
   - Use the existing caching mechanism to optimize API calls

2. **CLI Interface**:
   - Add a new command group for DCF calculations
   - Integrate with the existing CLI framework

## 4. How We'll Build It

### 4.1 Architecture

The DCF calculator will follow the existing layered architecture of the Folio application:

1. **Domain Layer** (`src/folib/domain.py`):
   - Add data classes for DCF parameters and results

2. **Data Layer** (`src/folib/data/`):
   - Extend the FMP provider to fetch financial data
   - Implement caching for financial data

3. **Calculation Layer** (`src/folib/calculations/`):
   - Create a new module for DCF calculations
   - Implement pure functions for each calculation step

4. **Service Layer** (`src/folib/services/`):
   - Create a new service module to orchestrate the DCF process
   - Handle parameter validation and default values

5. **CLI Layer** (`src/cli/commands/`):
   - Create a new command module for DCF calculations
   - Implement both direct execution and interactive mode

### 4.2 Implementation Plan

The implementation will be divided into the following phases:

1. **Phase 1: Core Library Implementation**
   - Extend FMP provider for financial data
   - Implement DCF calculation functions
   - Create DCF service layer

2. **Phase 2: CLI Interface Implementation**
   - Create DCF command module
   - Implement formatting utilities for DCF results
   - Add interactive mode support

3. **Phase 3: Testing and Documentation**
   - Write unit tests for calculation functions
   - Write integration tests for the service layer
   - Update documentation

### 4.3 Technical Considerations

#### Data Fetching

The DCF calculator will rely on the Financial Modeling Prep (FMP) API for historical financial data. Key considerations:

1. **API Rate Limits**: FMP has rate limits that need to be respected
2. **Data Availability**: Not all stocks may have complete financial data
3. **Caching**: Financial data should be cached to minimize API calls

#### Calculation Accuracy

DCF calculations involve several assumptions and approximations. Key considerations:

1. **Growth Rate Estimation**: Historical growth rates may not be indicative of future performance
2. **Terminal Value**: Different methods (perpetuity growth, exit multiple) can yield different results
3. **Discount Rate**: The appropriate discount rate depends on various factors (risk-free rate, equity risk premium, etc.)

#### User Experience

The CLI interface should provide a good balance of simplicity and flexibility:

1. **Default Values**: Provide sensible defaults for all parameters
2. **Parameter Validation**: Validate user inputs to prevent unrealistic scenarios
3. **Output Formatting**: Present results in a clear and understandable format

### 4.4 Code Structure

```
src/
├── folib/
│   ├── calculations/
│   │   └── dcf.py              # Pure functions for DCF calculations
│   ├── data/
│   │   └── provider_fmp.py     # Extended FMP provider for financial data
│   ├── services/
│   │   └── dcf_service.py      # DCF service orchestration
│   └── domain.py               # Add DCF data classes
├── cli/
    ├── commands/
    │   └── dcf.py              # DCF command implementation
    └── formatters.py           # Add DCF formatting utilities
```

## 5. Acceptance Criteria

The DCF calculator feature will be considered complete when:

1. Users can fetch historical financial data for a stock using the FMP API
2. Users can calculate intrinsic value using DCF methodology with default parameters
3. Users can customize all calculation parameters (growth rates, discount rate, etc.)
4. The CLI interface provides both basic and detailed output options
5. All calculations are properly tested and validated
6. Documentation is updated to include the new feature

## 6. Open Questions

1. Should we support multiple terminal value calculation methods (perpetuity growth, exit multiple)?
2. How should we handle stocks with negative cash flows or earnings?
3. Should we provide industry-specific default parameters?
4. How detailed should the calculation output be in the default view?

## 7. Future Enhancements

Potential future enhancements for the DCF calculator include:

1. Web interface integration with interactive charts
2. Sensitivity analysis to show how changes in parameters affect the result
3. Batch processing for multiple stocks
4. Integration with portfolio analysis to identify undervalued positions
5. Support for additional valuation methods (e.g., dividend discount model)
