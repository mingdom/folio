# Exposure Calculation Handoff

## Background

We are in the process of migrating the portfolio exposure calculation logic from the old implementation in `src/folio/portfolio_value.py` to the new implementation in `src/folib/services/portfolio_service.py`. The goal is to ensure that both implementations produce the same results for the same input data.

This document summarizes the current state of the migration, identifies remaining discrepancies, and outlines the next steps to complete the alignment.

## Current Status

We've made significant progress in aligning the exposure calculations between the old and new implementations, but there are still some discrepancies that need to be addressed. The analysis below is based on running the comparison script with the following command:

```bash
# Make sure you're in the project root directory
python tests/compare_portfolio_implementations.py --use-cache
```

This script loads a portfolio from `private-data/portfolio-private.csv`, processes it using both the old and new implementations, and compares the results.

### What's Working

1. **Sign Handling**: We've fixed the sign handling for short positions in the new implementation. Short exposures are now correctly stored with negative signs, which aligns with the old implementation.

2. **Portfolio Values**: The portfolio values (total, stock, option, cash) match closely between the old and new implementations, with differences less than 0.05%.

3. **Stock Exposures**: The stock exposures match closely between the old and new implementations.

### Remaining Discrepancies

1. **Net Exposure**: There's still a significant difference (-26.42%) in the net exposure calculation.

2. **Long Option Exposure**: The long option exposure in the new implementation is now very close to the old implementation (0.19% difference).

3. **Short Option Exposure**: The short option exposure in the new implementation is about 12.96% more negative than in the old implementation.

## Detailed Exposure Breakdown

```
                    Exposure Breakdown
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Component             ┃      Old Value ┃      New Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Long Stock Exposure   │  $2,298,326.67 │  $2,383,088.52 │
│ Long Option Exposure  │  $1,576,592.65 │  $1,499,187.57 │
│ Short Stock Exposure  │   $-512,935.27 │   $-528,532.24 │
│ Short Option Exposure │ $-2,105,109.37 │ $-2,428,887.62 │
└───────────────────────┴────────────────┴────────────────┘
```

## Root Cause Analysis

The remaining discrepancies are likely due to differences in how option exposures are calculated. After examining the code in both implementations, we've identified several potential sources of the differences:

1. **Delta Calculation**:
   - Old implementation (`src/folio/options.py`, line ~600): Uses `calculate_black_scholes_delta` and adjusts for position direction
   - New implementation (`src/folib/calculations/options.py`): Uses a similar Black-Scholes model but may have different parameter handling

2. **Volatility Assumptions**:
   - Old implementation (`src/folio/options.py`, line ~678): Uses a volatility skew model with `estimate_volatility_with_skew`
   - New implementation: May be using a constant volatility or a different skew model

3. **Categorization Logic**:
   - Old implementation (`src/folio/portfolio_value.py`, line ~150): Categorizes options based on delta exposure sign
   - New implementation (`src/folib/services/portfolio_service.py`): May be using different criteria for categorization

4. **Notional Value Calculation**:
   - Old implementation (`src/folio/options.py`, line ~660): Uses `calculate_notional_value`
   - New implementation: May be calculating notional value differently

## Next Steps

1. **Create a Detailed Option Comparison Tool**: Develop a tool that compares option calculations at a granular level, showing:
   - Delta values for each option
   - Exposure values for each option
   - How options are categorized (long vs. short)
   - The volatility values used

2. **Investigate Option Delta Calculation**: Compare the delta calculation methods in both implementations to identify any differences.

3. **Review Option Categorization Logic**: Ensure that options are being categorized consistently in both implementations.

4. **Align Volatility Models**: Make sure both implementations are using the same volatility assumptions.

## Implementation Plan

### 1. Enhance Option Comparison Tool

We've already created a basic option comparison tool in `tests/compare_options_fixed.py`. The next step is to enhance it to work with real portfolio data:

```python
# Pseudocode for the enhanced comparison tool
def compare_portfolio_options(portfolio_file):
    # Load portfolio using old method
    old_groups = load_portfolio_old_method(portfolio_file)

    # Load portfolio using new method
    new_portfolio = load_portfolio_new_method(portfolio_file)

    # Extract all options from both implementations
    old_options = extract_options_from_old_groups(old_groups)
    new_options = extract_options_from_new_portfolio(new_portfolio)

    # Match options between implementations
    matched_options = match_options(old_options, new_options)

    # Compare calculations for each matched option
    comparison_results = []
    for old_opt, new_opt in matched_options:
        # Compare delta, exposure, etc.
        comparison_results.append(compare_option_calculations(old_opt, new_opt))

    # Analyze and report results
    return analyze_comparison_results(comparison_results)
```

### 2. Fix Delta Calculation

The delta calculation needs to be aligned between the old and new implementations:

1. **Review Old Implementation**:
   ```python
   # In src/folio/options.py
   def calculate_option_delta(option, underlying_price, risk_free_rate=0.05, implied_volatility=None):
       # ...
       raw_delta = calculate_black_scholes_delta(option, underlying_price, risk_free_rate, implied_volatility)
       adjusted_delta = raw_delta if option.quantity >= 0 else -raw_delta
       return adjusted_delta
   ```

2. **Review New Implementation**:
   ```python
   # In src/folib/calculations/options.py
   def calculate_option_delta(option_type, strike, expiry, underlying_price, volatility=None):
       # ...
       # Make sure this matches the old implementation's logic
   ```

3. **Align Parameters**:
   - Ensure both use the same risk-free rate
   - Ensure both use the same volatility model
   - Ensure both handle option direction (long/short) consistently

### 3. Align Categorization Logic

The way options are categorized as long or short needs to be consistent:

1. **Review Old Implementation**:
   ```python
   # In src/folio/portfolio_value.py
   if opt.delta_exposure >= 0:  # Positive delta exposure = Long position
       long_options["value"] += opt.market_value
       # ...
   else:  # Negative delta exposure = Short position
       short_options["value"] += opt.market_value
       # ...
   ```

2. **Review New Implementation**:
   ```python
   # In src/folib/services/portfolio_service.py
   # Ensure this uses the same logic for categorization
   ```

3. **Make Necessary Changes**:
   - Update the new implementation to match the old one's categorization logic
   - Ensure both implementations handle edge cases (zero delta, etc.) consistently

### 4. Test with Real Data

Once the changes are implemented, test with real portfolio data:

1. **Run Comparison Script**:
   ```bash
   python tests/compare_portfolio_implementations.py --use-cache
   ```

2. **Verify Results**:
   - Check that the exposure differences are significantly reduced
   - Pay special attention to the option exposures

3. **Run Enhanced Option Comparison Tool**:
   ```bash
   python tests/compare_portfolio_options.py --portfolio private-data/portfolio-private.csv
   ```

4. **Document Remaining Differences**:
   - If there are still differences, document them in detail
   - Determine if the differences are acceptable or need further investigation

## Testing Instructions

### Portfolio Comparison Test

The main comparison script compares the entire portfolio processing between old and new implementations:

```bash
# Run the comparison with default portfolio file
python tests/compare_portfolio_implementations.py --use-cache

# To use a different portfolio file
python tests/compare_portfolio_implementations.py --portfolio path/to/portfolio.csv

# To force recalculation (don't use cache)
python tests/compare_portfolio_implementations.py

# To save results to cache for faster future runs
python tests/compare_portfolio_implementations.py --save-cache

# For verbose output with more details
python tests/compare_portfolio_implementations.py -v
```

The script will output:
1. Summary comparison (portfolio values)
2. Position comparison (individual positions)
3. Exposure analysis (exposure metrics)
4. Recommendations based on the differences found

### Option Calculation Test

We've also created a separate script specifically for testing option calculations:

```bash
# Run the option comparison test
python tests/compare_options_fixed.py --use-cache

# For verbose output
python tests/compare_options_fixed.py -v

# To force recalculation
python tests/compare_options_fixed.py --force-cache

# To compare only delta calculations
python tests/compare_options_fixed.py --compare delta

# To compare only exposure calculations
python tests/compare_options_fixed.py --compare exposure
```

This script creates a set of test cases with different option parameters and compares:
1. Delta values between old and new implementations
2. Exposure values between old and new implementations

### Interpreting the Results

When running these tests, look for:
1. **Significant differences**: Highlighted in red in the output tables
2. **Patterns in differences**: Are short positions consistently different? Are puts different from calls?
3. **Recommendations**: The scripts will suggest areas to investigate based on the differences found

### Debugging Tips

If you find significant differences:
1. Add logging statements to both implementations to trace the calculation steps
2. Compare the intermediate values (delta, notional value, etc.)
3. Check how options are categorized as long or short in both implementations

## Conclusion

We've made significant progress in aligning the exposure calculations between the old and new implementations:

1. **Fixed Sign Handling**: We've fixed the sign handling for short positions, ensuring that short exposures are stored with negative signs in both implementations.

2. **Created Documentation**: We've documented best practices for sign handling in financial calculations in `docs/best-practices/sign-handling-in-financial-calculations.md`.

3. **Created Test Scripts**: We've created two test scripts:
   - `tests/compare_portfolio_implementations.py`: Compares the entire portfolio processing
   - `tests/compare_options_fixed.py`: Specifically compares option calculations

However, there's still work to be done to fully match the old implementation. The current output from running `python tests/compare_portfolio_implementations.py --use-cache` shows:

```
Exposure Analysis
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Metric         ┃      Old Value ┃      New Value ┃   Difference ┃  % Diff ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Net Exposure   │  $1,256,874.68 │    $924,856.23 │ $-332,018.44 │ -26.42% │
│ Long Exposure  │  $3,874,919.31 │  $3,882,276.10 │    $7,356.78 │   0.19% │
│ Short Exposure │ $-2,618,044.64 │ $-2,957,419.86 │ $-339,375.23 │ -12.96% │
└────────────────┴────────────────┴────────────────┴──────────────┴─────────┘
```

The most significant issue is the difference in option exposures, which is affecting the net exposure calculation. By addressing the option delta calculation and categorization logic as outlined in the implementation plan, we should be able to bring the implementations into closer alignment.

### Next Steps Summary

1. **Enhance the option comparison tool** to work with real portfolio data
2. **Align the delta calculation** between old and new implementations
3. **Ensure consistent categorization logic** for options
4. **Test with real data** and document any remaining differences

By following this plan, we should be able to reduce the exposure differences to an acceptable level and complete the migration to the new implementation.
