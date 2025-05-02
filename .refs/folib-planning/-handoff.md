---
description: Handoff document for portfolio implementation differences
date: "2025-05-01"
status: "IN PROGRESS"
---

# How to use this document:
1. Run `python tests/compare_portfolio_implementations.py -v -p private-data/portfolio-private.csv --use-cache` to compare the difference between the old and new implementations.
2. Read The rest of this document and pick the most important change to fix
3. Run the script again and compare
4. Iterate (steps 1-3 above) until every issue is fixed

---

# Portfolio Implementation Differences Handoff Document

This document analyzes the differences between the old and new portfolio implementations, focusing on exposure calculations and option delta calculations. It serves as a handoff document for the next engineer to understand the current state and what needs to be addressed.

## Summary of Current Status

The new implementation (`src/folib/`) has successfully matched the old implementation (`src/folio/`) for most portfolio metrics:

- **Total Value**: Matches within 0.03% (difference of $833.43)
- **Stock Value**: Matches within 0.05% (difference of $832.95)
- **Option Value**: Matches exactly (0.00% difference)
- **Cash Value**: Matches within 0.00% (difference of $0.48)
- **Pending Activity**: Matches exactly (0.00% difference)

However, there are significant differences in exposure calculations:

- **Net Market Exposure**: 57.21% lower in the new implementation
- **Long Exposure**: 6.05% lower in the new implementation
- **Short Exposure**: 18.51% higher in the new implementation

## Root Causes of Differences

### 1. Option Delta Calculation Differences

The primary cause of exposure differences is in how option delta is calculated:

#### Old Implementation (`src/folio/options.py`):
```python
def calculate_black_scholes_delta(
    option_position: OptionContract,
    underlying_price: float,
    risk_free_rate: float = 0.05,
    volatility: float | None = None,
) -> float:
    # Set up the pricing environment
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    rate_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(today, risk_free_rate, ql.Actual365Fixed())
    )
    dividend_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(today, 0.0, ql.Actual365Fixed())
    )
    calendar = ql.UnitedStates(ql.UnitedStates.NYSE)
    vol_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(today, calendar, volatility, ql.Actual365Fixed())
    )

    # Error handling with fallback values
    try:
        # Calculate delta
        delta = option.delta()
        return delta
    except Exception as e:
        logger.error(f"Error calculating delta for {option_position.description}: {e}")
        # Return a reasonable default delta based on option type and moneyness
        if option_position.option_type == "CALL":
            return 0.5 if underlying_price > strike else 0.1
        else:  # PUT
            return -0.5 if underlying_price < strike else -0.1
```

#### New Implementation (`src/folib/calculations/options.py`):
```python
def calculate_option_delta(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05,
) -> float:
    # Set up the pricing environment
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date, risk_free_rate, ql.Actual365Fixed())
    )
    dividend_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date, 0.0, ql.Actual365Fixed())
    )
    volatility_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            calculation_date,
            ql.UnitedStates(ql.UnitedStates.NYSE),  # Changed from TARGET to NYSE
            volatility,
            ql.Actual365Fixed(),
        )
    )

    # No error handling with fallback values - follows "fail fast" principle
    return option.delta()
```

### 2. Exposure Calculation Differences

#### Old Implementation (`src/folio/portfolio_value.py`):
- Uses `ExposureBreakdown` class with detailed component tracking
- Handles option exposures based on delta exposure, not market value
- Includes fallback mechanisms for error handling

#### New Implementation (`src/folib/services/portfolio_service.py`):
- Uses simpler functional approach with calculation modules
- Follows "fail fast" principle with minimal error handling
- Uses more consistent approach to exposure calculations

### 3. Option Categorization Differences

#### Old Implementation:
- Categorizes options based on delta exposure:
  - Positive delta exposure (long calls, short puts) => Long position
  - Negative delta exposure (short calls, long puts) => Short position

#### New Implementation:
- Uses the same categorization logic but with different delta values
- This leads to different categorization of some option positions

## Key Files to Examine

### Old Implementation:
1. `src/folio/options.py`: Option pricing and Greeks calculations
   - `calculate_black_scholes_delta()`: Delta calculation with fallbacks
   - `calculate_option_exposure()`: Option exposure calculation

2. `src/folio/portfolio_value.py`: Portfolio value and exposure calculations
   - `calculate_portfolio_metrics()`: Calculates net market exposure
   - `calculate_component_values()`: Extracts component values

3. `src/folio/data_model.py`: Data structures
   - `ExposureBreakdown`: Detailed breakdown of exposures
   - `PortfolioSummary`: Summary of portfolio metrics

### New Implementation:
1. `src/folib/calculations/options.py`: Pure functions for option calculations
   - `calculate_option_delta()`: Delta calculation without fallbacks
   - `calculate_option_price()`: Option price calculation

2. `src/folib/calculations/exposure.py`: Exposure calculation functions
   - `calculate_stock_exposure()`: Stock exposure calculation
   - `calculate_option_exposure()`: Option exposure calculation
   - `calculate_beta_adjusted_exposure()`: Beta adjustment

3. `src/folib/services/portfolio_service.py`: Portfolio processing
   - `create_portfolio_summary()`: Creates portfolio summary
   - `get_portfolio_exposures()`: Calculates portfolio exposures

## Recommended Approach to Fix Differences

### 1. Align Option Delta Calculation

The most significant differences are in option delta calculation. To align the implementations:

```python
# In src/folib/calculations/options.py
def calculate_option_delta(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05,
) -> float:
    # ... existing code ...

    try:
        return option.delta()
    except Exception as e:
        # Add fallback similar to old implementation
        if option_type == "CALL":
            return 0.5 if underlying_price > strike else 0.1
        else:  # PUT
            return -0.5 if underlying_price < strike else -0.1
```

### 2. Add Detailed Logging for Comparison

Add detailed logging to both implementations to identify specific differences:

```python
# In src/folib/services/portfolio_service.py
def get_portfolio_exposures(portfolio: Portfolio) -> dict:
    # ... existing code ...

    # Add detailed logging for each option position
    for position in portfolio.option_positions:
        delta = calculate_option_delta(...)
        market_exposure = calculate_option_exposure(...)
        logger.debug(f"Option {position.ticker}: delta={delta}, exposure={market_exposure}")
```

### 3. Create Test Cases for Specific Option Scenarios

Create test cases that compare delta calculations between implementations:

```python
def test_option_delta_comparison():
    # Test case 1: At-the-money call option
    old_delta = calculate_old_delta("CALL", 100, date(2023, 12, 31), 100)
    new_delta = calculate_new_delta("CALL", 100, date(2023, 12, 31), 100)
    print(f"ATM Call: Old={old_delta}, New={new_delta}, Diff={old_delta-new_delta}")

    # Test case 2: Out-of-the-money put option
    # ... more test cases ...
```

### 4. Consider Configuration Options

Add configuration options to control delta calculation behavior:

```python
def calculate_option_delta(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05,
    use_fallback: bool = True,  # New parameter
) -> float:
    # ... existing code ...

    try:
        return option.delta()
    except Exception as e:
        if use_fallback:
            # Use fallback values
            if option_type == "CALL":
                return 0.5 if underlying_price > strike else 0.1
            else:  # PUT
                return -0.5 if underlying_price < strike else -0.1
        else:
            # Follow fail-fast principle
            raise
```

## How Options Calculations Should Work

### Option Delta Calculation

Option delta represents the rate of change of the option price with respect to the underlying price. It ranges from -1.0 to 1.0:

- For call options: 0.0 to 1.0 (higher for in-the-money options)
- For put options: -1.0 to 0.0 (lower for in-the-money options)

The correct calculation should:

1. Use American-style options for US equities
2. Account for time to expiration
3. Use appropriate volatility (ideally implied volatility)
4. Handle edge cases (e.g., deep in/out of the money, near expiry)

### Option Exposure Calculation

Option exposure represents the equivalent stock exposure of an option position:

```
Option Exposure = Quantity × Contract Size × Underlying Price × Delta
```

For example, a position with 10 call option contracts (each representing 100 shares) with delta 0.6 on a stock trading at $100 has an exposure of:
```
10 × 100 × $100 × 0.6 = $60,000
```

This means the option position behaves similarly to owning $60,000 worth of the underlying stock.

### Option Categorization

Options should be categorized based on their delta exposure:

- **Long Exposure**:
  - Long call options (positive delta)
  - Short put options (positive delta)

- **Short Exposure**:
  - Short call options (negative delta)
  - Long put options (negative delta)

This categorization ensures that the exposure reflects the directional risk of the position.

## Testing Strategy

To ensure the implementations match, follow this testing strategy:

1. **Unit Tests**: Create unit tests for each calculation function
2. **Integration Tests**: Test the entire portfolio calculation pipeline
3. **Comparison Tests**: Compare results between old and new implementations
4. **Edge Case Tests**: Test extreme scenarios (e.g., deep ITM/OTM options, near expiry)

The test suite should include:

```python
# Unit tests for option delta calculation
def test_option_delta_calculation():
    # Test at-the-money call
    delta = calculate_option_delta("CALL", 100, date(2023, 12, 31), 100)
    assert 0.4 < delta < 0.6  # Approximate range for ATM call

    # Test in-the-money put
    delta = calculate_option_delta("PUT", 120, date(2023, 12, 31), 100)
    assert -0.9 < delta < -0.7  # Approximate range for ITM put

# Integration tests for portfolio exposure
def test_portfolio_exposure_calculation():
    portfolio = create_test_portfolio()
    exposures = get_portfolio_exposures(portfolio)

    # Verify exposures match expected values
    assert abs(exposures["net_market_exposure"] - expected_value) < tolerance
```

## Conclusion

The differences in exposure calculations between the old and new implementations are primarily due to differences in option delta calculation and error handling approaches. By aligning these calculations and adding appropriate fallback mechanisms, we can make the implementations match more closely.

The recommended approach is to:

1. Add fallback mechanisms to the new implementation's delta calculation
2. Add detailed logging to identify specific differences
3. Create test cases for comparison
4. Consider adding configuration options for flexibility

This will ensure that the new implementation provides the same results as the old implementation while maintaining the cleaner, more modular architecture.

## Next Steps

1. Implement the recommended changes to align delta calculations
2. Add detailed logging for comparison
3. Create test cases for specific option scenarios
4. Run comprehensive tests to verify the implementations match
5. Document any remaining differences and their impact
