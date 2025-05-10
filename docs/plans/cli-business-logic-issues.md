---
date: 2025-05-03
title: CLI Business Logic Issues Analysis
author: Augment Agent
---

# CLI Business Logic Issues Analysis

## WHY: User's Goal

The user wants to maintain a clean separation of concerns between the CLI layer (`src/cli/`) and the business logic layer (`src/folib/`). The CLI should be a thin display interface that does not contain business logic. The specific issue that triggered this analysis was an incorrect approach to handling beta values for cash positions in the CLI layer rather than in the core library.

## WHAT: Problem Statement

The CLI code currently contains business logic that should be in the `src/folib/` library. This violates the separation of concerns principle and makes the codebase harder to maintain. We need to identify all instances where business logic is incorrectly placed in the CLI layer and document them for future refactoring.

## HOW: Solution

This document identifies and analyzes instances where business logic is incorrectly placed in the CLI layer, providing recommendations for moving this logic to the appropriate location in the `src/folib/` library.

## Scope

This analysis focuses on the `src/cli/` directory, particularly examining:
- Business logic in command implementations
- Data transformations in the CLI layer
- Conditional logic that should be in the core library
- Calculations performed in the CLI layer

## Assumptions

- The CLI should be a thin display interface that only handles user input, calls appropriate `folib` functions, and formats output.
- All business logic, data transformations, and calculations should be in the `src/folib/` library.
- The CLI-SPEC.md document represents the intended architecture and separation of concerns.

## Issues Identified

### 1. Beta Value Handling for Cash Positions

**Location:** `src/cli/formatters.py` (lines 269-273)

**Issue:** The CLI code contains conditional logic to display beta as "0.00" for cash positions:

```python
"0.00"
if position_type == "cash"
else (
    f"{beta:.2f}" if isinstance(beta, (int, float)) else "1.00"
),  # Format beta
```

**Analysis:** This is business logic that should be in the `folib` library. The beta value for cash positions should be set to 0.0 in the core library, and the CLI should simply display whatever value is provided by the library.

**Recommendation:** Move this logic to the `src/folib/domain.py` file by adding a `beta` property to the `CashPosition` class that always returns 0.0.

### 2. Beta-Adjusted Exposure Calculation in Portfolio List Command

**Location:** `src/cli/commands/portfolio.py` (lines 163-232 and 380-449)

**Issue:** The `portfolio_list_cmd` and `portfolio_list` functions contain extensive business logic for calculating beta-adjusted exposure for different position types:

```python
# Calculate exposure based on position type
if position.position_type == "stock":
    from src.folib.calculations.exposure import (
        calculate_beta_adjusted_exposure,
        calculate_stock_exposure,
    )
    from src.folib.data.market_data import market_data_provider

    # Calculate stock exposure
    market_exposure = calculate_stock_exposure(
        position.quantity, position.price
    )
    # Get beta for the stock
    beta = market_data_provider.get_beta(position.ticker) or 1.0
    # Calculate beta-adjusted exposure
    beta_adjusted_exposure = calculate_beta_adjusted_exposure(
        market_exposure, beta
    )
# ... similar code for option positions
```

**Analysis:** This calculation logic should be in the `folib` library. The CLI should simply call a function that returns the beta-adjusted exposure for a position.

**Recommendation:** Create a new function in `src/folib/services/position_service.py` that calculates beta-adjusted exposure for any position type, and have the CLI call this function.

### 3. Custom Sorting for Beta-Adjusted Exposure

**Location:** `src/cli/commands/portfolio.py` (lines 234-239 and 451-456)

**Issue:** The CLI implements custom sorting logic for beta-adjusted exposure:

```python
# Sort position data by beta-adjusted exposure if that's the sort criteria
if sort_by.lower() == "beta_adjusted_exposure":
    position_data.sort(
        key=lambda x: x["beta_adjusted_exposure"],
        reverse=(sort_direction.lower() == "desc"),
    )
```

**Analysis:** This sorting logic should be in the `folib` library. The `sort_positions` function in `src/folib/services/portfolio_service.py` should handle all sorting criteria, including beta-adjusted exposure.

**Recommendation:** Enhance the `sort_positions` function in `src/folib/services/portfolio_service.py` to handle beta-adjusted exposure sorting.

### 4. Default Beta Values in CLI

**Location:** `src/cli/commands/portfolio.py` (lines 225-226 and 442-443)

**Issue:** The CLI sets default beta values for cash and unknown positions:

```python
# For cash or unknown positions, exposure is zero
market_exposure = 0.0
beta_adjusted_exposure = 0.0
beta = 0.0  # Set beta to 0 for cash and unknown positions
```

**Analysis:** Default values for business properties should be set in the `folib` library, not in the CLI.

**Recommendation:** Add properties to the `CashPosition` and `UnknownPosition` classes in `src/folib/domain.py` that return appropriate default values for beta and beta-adjusted exposure.

### 5. Fallback Logic for Option Underlying Price

**Location:** `src/cli/commands/portfolio.py` (lines 195-205 and 412-422)

**Issue:** The CLI contains fallback logic for option underlying prices:

```python
try:
    underlying_price = market_data_provider.get_price(
        position.ticker
    )
    beta = market_data_provider.get_beta(position.ticker) or 1.0
except Exception:
    # Fallback to using strike as proxy for underlying price
    underlying_price = position.strike
    beta = 1.0
```

**Analysis:** This fallback logic is business logic that should be in the `folib` library.

**Recommendation:** Move this fallback logic to a function in `src/folib/services/position_service.py` that handles getting underlying prices for options with appropriate fallbacks.

## Open Questions

1. Should the `Position` class in `src/folib/domain.py` have `beta` and `beta_adjusted_exposure` properties?
2. Should there be a separate service function for calculating beta-adjusted exposure for all position types?
3. How should the CLI handle sorting by custom criteria that aren't directly available as position properties?

## Conclusion

The CLI layer currently contains significant business logic that should be moved to the `folib` library. This violates the separation of concerns principle and makes the codebase harder to maintain. By addressing the issues identified in this document, we can improve the architecture of the application and make it more maintainable.

The most critical issue is the handling of beta values for cash positions, which should be moved to the `folib` library. Other issues, such as beta-adjusted exposure calculation and sorting, should also be addressed to ensure a clean separation between the CLI and business logic layers.
