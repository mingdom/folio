# Retrospective: Sign Handling in Financial Calculations

## Issue Summary

We encountered a significant issue in our portfolio exposure calculations where the new implementation produced very different results from the old implementation. The root cause was inconsistent handling of signs for short positions and negative exposures.

## What Happened

1. The old implementation stored short exposures with negative signs
2. The new implementation initially stored short exposures as positive values and applied signs during aggregation
3. This led to double-counting of signs and incorrect exposure calculations

## Root Cause Analysis

The issue stemmed from a fundamental design flaw in how we handled signs in our financial calculations:

```python
# Problematic code in get_portfolio_exposures
if option_category == "long":
    exposures["long_option_exposure"] += abs(market_exposure)
else:  # option_category == "short"
    exposures["short_option_exposure"] += abs(market_exposure)

# Later, when calculating net exposure
exposures["net_market_exposure"] = (
    exposures["long_stock_exposure"]
    - exposures["short_stock_exposure"]
    + exposures["long_option_exposure"]
    - exposures["short_option_exposure"]
)
```

This approach had several problems:
1. It stripped away the natural sign of the exposure using `abs()`
2. It categorized positions as "long" or "short" and then applied signs based on the category
3. It used subtraction for aggregation, which assumes all values are positive

This created a complex, error-prone system where the sign of a value could be applied multiple times or in inconsistent ways.

## The Fix

We fixed the issue by embracing the natural signs of financial values:

```python
# Fixed code in get_portfolio_exposures
if market_exposure > 0:
    exposures["long_option_exposure"] += market_exposure
else:
    exposures["short_option_exposure"] += market_exposure  # Already negative

# Later, when calculating net exposure
exposures["net_market_exposure"] = (
    exposures["long_stock_exposure"]
    + exposures["short_stock_exposure"]  # Already negative
    + exposures["long_option_exposure"]
    + exposures["short_option_exposure"]  # Already negative
)
```

This approach:
1. Preserves the natural sign of the exposure
2. Uses the sign to determine the category (positive = long, negative = short)
3. Uses simple addition for aggregation, which works correctly with signed values

## Lessons Learned

### 1. Embrace Natural Signs

In financial calculations, values often have natural signs that convey important information:
- Long positions: Positive values
- Short positions: Negative values
- Credits: Positive values
- Debits: Negative values

By preserving these natural signs throughout our calculations, we make our code more intuitive and less error-prone.

### 2. Avoid Using `abs()` Unnecessarily

The `abs()` function strips away valuable information. Only use it when you genuinely need the absolute value, not as a way to handle signs separately.

### 3. Use Addition, Not Subtraction, for Aggregation

When values already have their natural signs, you can simply add them together to get the correct result:

```python
# Good
net_value = positive_value + negative_value  # negative_value is already negative

# Bad
net_value = positive_value - abs(negative_value)  # Error-prone
```

### 4. Design for Clarity and Consistency

Our exposure calculation had two different approaches to handling signs:
1. In some places, it used the natural sign of the value
2. In other places, it used categorization and then applied signs

This inconsistency made the code hard to understand and maintain. By using a consistent approach throughout, we made the code more reliable.

## Best Practices for Sign Handling

1. **Store values with their natural signs**
   - Long positions: Positive
   - Short positions: Negative

2. **Use the sign to determine the category, not vice versa**
   - If value > 0, it's a long position
   - If value < 0, it's a short position

3. **Use addition for aggregation**
   - Net value = sum of all values (with their signs)

4. **Be explicit about sign conventions in documentation**
   - Document your sign conventions clearly
   - Use consistent terminology

5. **Use clear variable names**
   - `long_exposure` (positive value)
   - `short_exposure` (negative value)

## Conclusion

This issue highlighted the importance of careful sign handling in financial calculations. By embracing natural signs and using consistent approaches throughout our codebase, we can make our code more intuitive, maintainable, and correct.

Remember: In financial calculations, signs matter!
