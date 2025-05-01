---
description: Handoff document for portfolio implementation differences - Update 2
date: "2025-05-01"
status: "IN PROGRESS"
---

# Portfolio Implementation Differences - Progress Update

This document summarizes the progress made in aligning the old and new portfolio implementations, focusing on option exposure calculations. It serves as a handoff document for the next engineer to understand the current state and what still needs to be addressed.

## Progress Summary

We've made significant progress in aligning the option exposure calculations between the old implementation (`src/folio/`) and the new implementation (`src/folib/`):

1. **Option Exposure Calculation**: Fixed the calculation in `src/folib/calculations/exposure.py` to match the old implementation's approach.
2. **Option Delta Calculation**: Updated the delta calculation in `src/folib/calculations/options.py` to handle position direction (short vs. long) correctly.
3. **Option Categorization**: Implemented a `categorize_option_by_delta` function to ensure consistent categorization of options.

Despite these improvements, there are still significant differences in the portfolio-level exposure calculations:

- **Net Market Exposure**: 57.21% lower in the new implementation
- **Long Exposure**: 6.05% lower in the new implementation
- **Short Exposure**: 18.51% higher in the new implementation

## Key Changes Made

### 1. Fixed Option Exposure Calculation

Updated `calculate_option_exposure` in `src/folib/calculations/exposure.py` to match the old implementation's approach:

```python
def calculate_option_exposure(
    quantity: float, underlying_price: float, delta: float, include_sign: bool = True
) -> float:
    # Standard contract multiplier for equity options
    CONTRACT_SIZE = 100

    # Calculate notional value (always positive)
    notional_value = CONTRACT_SIZE * abs(quantity) * underlying_price

    # Calculate exposure (sign determined by delta)
    # For short positions, the old implementation inverts the delta
    # This is critical for matching the old implementation's behavior
    if quantity < 0:  # Short position
        # For short positions, invert the sign of delta
        exposure = -delta * notional_value
    else:  # Long position
        exposure = delta * notional_value

    # If include_sign is False, return the absolute value
    if not include_sign:
        exposure = abs(exposure)

    return exposure
```

### 2. Updated Option Delta Calculation

Updated `calculate_option_delta` in `src/folib/calculations/options.py` to handle position direction:

```python
def calculate_option_delta(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05,
    use_fallback: bool = True,
    quantity: float = 1.0,  # New parameter to adjust delta based on position direction
) -> float:
    # ... existing code ...

    # Calculate raw delta
    raw_delta = option.delta()

    # Adjust for position direction (short positions have inverted delta)
    # This matches the behavior in the old implementation (src/folio/options.py)
    adjusted_delta = raw_delta if quantity >= 0 else -raw_delta

    return adjusted_delta
```

### 3. Implemented Option Categorization Function

Created a new function `categorize_option_by_delta` in `src/folib/calculations/options.py`:

```python
def categorize_option_by_delta(delta: float) -> str:
    """
    Categorize an option as 'long' or 'short' based on its delta.

    In the old implementation (src/folio/portfolio_value.py), options are categorized
    based on delta exposure, not quantity:
    - Positive delta exposure (long calls, short puts) => Long position
    - Negative delta exposure (short calls, long puts) => Short position

    Args:
        delta: Option delta (-1.0 to 1.0)

    Returns:
        'long' for positive delta exposure, 'short' for negative delta exposure
    """
    return "long" if delta >= 0 else "short"
```

## Testing Progress

We've created and updated two test scripts to verify our changes:

### 1. Option Exposure Comparison Test

The `tests/compare_option_exposures.py` script compares option exposure calculations between the old and new implementations for various option scenarios. After our changes, this test now shows 0% difference for all test cases.

**How to run:**
```bash
python tests/compare_option_exposures.py -v
```

### 2. Portfolio Implementation Comparison Test

The `tests/compare_portfolio_implementations.py` script compares the full portfolio calculations between the old and new implementations. Despite our changes to the option exposure calculations, this test still shows significant differences in the exposure metrics.

**How to run:**
```bash
python tests/compare_portfolio_implementations.py -v -p private-data/portfolio-private.csv --use-cache
```

## Current Hypothesis

The fact that the option exposure calculations match perfectly in the dedicated test script but still show significant differences in the portfolio-level comparison suggests:

1. **Duplicate Calculation Logic**: There may be duplicate or inconsistent calculation logic in the portfolio service that is not using our fixed exposure calculation functions.

2. **Different Aggregation Methods**: The way exposures are aggregated at the portfolio level might differ between implementations.

3. **Categorization Inconsistencies**: Despite fixing the categorization function, there might be places where options are categorized differently.

4. **Data Differences**: The underlying data (prices, betas, etc.) might be different between the implementations.

## Key Files to Examine Next

1. **Portfolio Service Implementation**:
   - `src/folib/services/portfolio_service.py`: Check how exposures are calculated and aggregated
   - `src/folio/portfolio_value.py`: Compare with the old implementation's approach

2. **Exposure Calculation Logic**:
   - `src/folib/calculations/exposure.py`: Ensure all exposure calculations are consistent
   - `src/folio/options.py`: Compare with the old implementation's approach

3. **Data Fetching and Processing**:
   - `src/folib/data/stock.py`: Check how underlying data is fetched and processed
   - `src/folio/stockdata.py`: Compare with the old implementation's approach

## Recommended Next Steps

1. **Add Detailed Logging**:
   - Add detailed logging to both implementations to track the calculation of each position's exposure
   - Compare the logs to identify specific positions where exposures differ

2. **Check for Duplicate Logic**:
   - Review the portfolio service implementation to ensure it's using the fixed exposure calculation functions
   - Look for any hardcoded calculations that might bypass the fixed functions

3. **Verify Data Consistency**:
   - Ensure both implementations are using the same underlying data (prices, betas, etc.)
   - Add logging to verify data consistency

4. **Test Individual Components**:
   - Create targeted tests for specific components (e.g., option categorization, exposure aggregation)
   - Isolate the source of the differences

5. **Consider a Step-by-Step Approach**:
   - Start with a minimal portfolio (e.g., just one option position)
   - Gradually add positions and verify each step

## Conclusion

We've made significant progress in aligning the option exposure calculations at the individual position level, but there are still differences at the portfolio level. The next steps should focus on identifying where these differences occur in the portfolio aggregation process.

The most likely cause is that there are multiple places where option exposures are calculated or categorized, and not all of them are using our fixed functions. A thorough review of the portfolio service implementation should help identify these inconsistencies.

## Independent Investigation Notes (Second Opinion)

After analyzing both codebases and comparing implementations, I've identified some additional insights that may help explain the exposure differences:

1. **Delta Calculation vs Exposure Calculation Sign Convention**:
   - A critical issue appears to be double-inversion of position signs between delta and exposure calculations
   - Old implementation: Only inverts delta once (in delta calculation)
   - New implementation: Inverts twice:
     1. In `calculate_option_delta` when adjusting for position direction
     2. Again in `calculate_option_exposure` when handling short positions
   - This double-inversion explains the significant shift in short option exposure (+18.51%)

2. **Cascading Effects of Sign Convention Issue**:
   - The sign issues affect option categorization:
     - Some long positions are being miscategorized as short
     - This explains both the lower long exposure (-6.05%) and higher short exposure (+18.51%)
   - The total impact compounds through the portfolio aggregation

3. **Portfolio Service Layer Potential Issues**:
   - `get_portfolio_exposures` in portfolio service has potential data flow issues:
     - Position direction is handled in both delta calculation and exposure calculation layers
     - Unnecessary use of `abs()` in exposure aggregation
     - Sign conventions are not consistently applied through the aggregation chain

4. **Specific Areas to Fix**:
   - Primary fix needed in `src/folib/calculations/exposure.py`:
     ```python
     # Current problematic logic:
     if quantity < 0:  # Short position
         exposure = -delta * notional_value  # This is the double-inversion
     else:
         exposure = delta * notional_value
     ```
   - The delta calculation already accounts for position direction, so this second inversion should be removed

5. **Fix Verification Strategy**:
   - Once the exposure calculation is fixed:
     1. Individual option exposures should match between implementations
     2. This should automatically fix the categorization issues
     3. The portfolio-level exposure differences should significantly reduce

This analysis suggests that fixing the core exposure calculation would address both the direct exposure differences and the categorization issues that are causing the portfolio-level discrepancies. The fix should be relatively straightforward, but careful testing will be needed to verify the changes don't introduce new issues.
