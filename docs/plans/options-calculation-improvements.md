---
date: 2023-06-21
title: Options Calculation Improvements
author: Augment Agent
---

# Options Calculation Improvements

## WHY
We need to ensure our options calculations are accurate and follow the fail-fast principle. Currently, we're using default volatility values (0.3) in several places instead of calculating implied volatility from market prices, which could lead to inaccurate delta and exposure calculations. This affects the accuracy of our portfolio analysis and could potentially lead to incorrect investment decisions, causing our clients to lose millions.

## WHAT
We need to update our options calculation module to:
1. Properly use implied volatility calculated from market prices
2. Follow the fail-fast principle by raising exceptions instead of silently falling back to default values
3. Handle edge cases like options near or past expiry correctly
4. Ensure all consumers of these functions use the correct approach

## HOW
We will update the `calculate_option_delta` function to require volatility explicitly, update the `analyze_option_position` function to calculate implied volatility from the option's market price, and ensure all error cases fail fast with appropriate exceptions.

## Scope
This is a moderate change affecting several files in the codebase:

1. `src/folib/calculations/options.py`:
   - Update `calculate_option_delta` to require volatility explicitly
   - Update `calculate_implied_volatility` to handle expiry edge cases
   - Ensure all functions follow the fail-fast principle

2. `src/folib/services/position_service.py`:
   - Update `analyze_option_position` to calculate implied volatility from the option's market price
   - Update `get_position_market_exposure` to use the proper volatility calculation

3. Any other files that call these functions directly or indirectly

## Decisions

1. **Handling Options Near Expiry**:
   - For options near expiry, we'll continue to use the standard implied volatility calculation
   - For options past expiry, we'll treat them as if they're at expiry for calculation purposes
   - We'll log a warning when processing options past expiry as this is an error case

2. **Input Validation**:
   - We won't add additional validation for option prices beyond checking if they're positive
   - We'll rely on the existing validation in the `validate_option_inputs` function

3. **Error Handling**:
   - We'll fail completely and quickly when errors occur
   - No silent fallbacks to default values
   - Exceptions will be propagated to the caller

## Assumptions
1. The option's market price in the `OptionPosition` object is accurate and up-to-date
2. The QuantLib library can handle the implied volatility calculation for all valid inputs
3. All consumers of these functions can handle exceptions appropriately

## Open Questions
1. Are there any other consumers of these functions that we haven't identified?
2. Should we add unit tests specifically for the edge cases (near expiry, past expiry)?
3. Do we need to update any documentation to reflect these changes?

## Implementation Plan

### 1. Update `calculate_option_delta` in `src/folib/calculations/options.py`
- Remove the default `None` value for volatility
- Remove the code that sets volatility to DEFAULT_VOLATILITY when it's None
- Update the function signature and docstring

### 2. Update `calculate_implied_volatility` in `src/folib/calculations/options.py`
- Add handling for options past expiry
- Remove the fallback to DEFAULT_VOLATILITY on error
- Propagate exceptions to the caller

### 3. Update `analyze_option_position` in `src/folib/services/position_service.py`
- Calculate implied volatility using the option's market price
- Pass the calculated volatility to `calculate_option_delta`
- Handle exceptions from the implied volatility calculation

### 4. Update `get_position_market_exposure` in `src/folib/services/position_service.py`
- Calculate implied volatility using the option's market price
- Pass the calculated volatility to `calculate_option_delta`
- Handle exceptions from the implied volatility calculation

### 5. Run Tests
- Run the existing test suite to ensure we haven't broken anything
- Add new tests for the edge cases if needed

### 6. Update Documentation
- Update docstrings to reflect the new behavior
- Add warnings about the fail-fast approach
