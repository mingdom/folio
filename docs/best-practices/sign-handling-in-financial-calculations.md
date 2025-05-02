# Best Practices: Sign Handling in Financial Calculations

## Introduction

This document outlines best practices for handling signs (positive/negative values) in financial calculations, particularly for portfolio exposure calculations. It is based on lessons learned from debugging issues in the portfolio exposure calculation implementation.

## The Problem

We encountered a significant issue in our portfolio exposure calculations where the new implementation produced very different results from the old implementation. The root cause was inconsistent handling of signs for short positions and negative exposures.

Specifically:
- The old implementation stored short exposures with negative signs
- The new implementation initially stored short exposures as positive values and applied signs during aggregation
- This led to double-counting of signs and incorrect exposure calculations

## Best Practices

### 1. Store Values with Their Natural Signs

**DO:**
```python
# Store short exposures with negative signs
if market_exposure < 0:
    exposures["short_option_exposure"] += market_exposure  # Already negative
```

**DON'T:**
```python
# Don't use abs() and then apply signs later
if option_category == "short":
    exposures["short_option_exposure"] += abs(market_exposure)  # Wrong!
```

### 2. Use Simple Addition for Aggregation

**DO:**
```python
# Simply add all exposures (signs are already correct)
net_exposure = (
    long_stock_exposure
    + short_stock_exposure  # Already negative
    + long_option_exposure
    + short_option_exposure  # Already negative
)
```

**DON'T:**
```python
# Don't use subtraction for aggregation
net_exposure = (
    long_stock_exposure
    - short_stock_exposure  # Wrong! Double-counting the sign
    + long_option_exposure
    - short_option_exposure  # Wrong! Double-counting the sign
)
```

### 3. Avoid Categorization Based on Signs When Possible

**DO:**
```python
# Use the natural sign of the exposure
if market_exposure > 0:
    exposures["long_option_exposure"] += market_exposure
else:
    exposures["short_option_exposure"] += market_exposure  # Already negative
```

**DON'T:**
```python
# Don't categorize based on delta and then apply different logic
option_category = categorize_option_by_delta(delta)
if option_category == "long":
    exposures["long_option_exposure"] += abs(market_exposure)
else:
    exposures["short_option_exposure"] += abs(market_exposure)
```

### 4. Be Consistent with Sign Conventions

**DO:**
- Document your sign conventions clearly
- Use the same sign conventions throughout the codebase
- For financial calculations:
  - Long positions: Positive values
  - Short positions: Negative values

**DON'T:**
- Mix different sign conventions in different parts of the code
- Use abs() to strip signs and then reapply them inconsistently

### 5. Use Clear Variable Names

**DO:**
```python
long_stock_exposure = 1000.0  # Positive value
short_stock_exposure = -500.0  # Negative value
net_exposure = long_stock_exposure + short_stock_exposure  # 500.0
```

**DON'T:**
```python
long_exposure = 1000.0
short_exposure = 500.0  # Ambiguous: is this positive or negative?
net_exposure = long_exposure - short_exposure  # Ambiguous calculation
```

## Real-World Example

Here's a real-world example from our codebase that demonstrates the issue and the fix:

### Problem Code:

```python
# Categorize options based on delta sign
option_category = categorize_option_by_delta(delta)

# Store exposures as absolute values
if option_category == "long":
    exposures["long_option_exposure"] += abs(market_exposure)
else:
    exposures["short_option_exposure"] += abs(market_exposure)

# Calculate net exposure using subtraction
exposures["net_market_exposure"] = (
    exposures["long_stock_exposure"]
    - exposures["short_stock_exposure"]
    + exposures["long_option_exposure"]
    - exposures["short_option_exposure"]
)
```

### Fixed Code:

```python
# Store exposures with their natural signs
if market_exposure > 0:
    exposures["long_option_exposure"] += market_exposure
else:
    exposures["short_option_exposure"] += market_exposure  # Already negative

# Calculate net exposure using addition
exposures["net_market_exposure"] = (
    exposures["long_stock_exposure"]
    + exposures["short_stock_exposure"]  # Already negative
    + exposures["long_option_exposure"]
    + exposures["short_option_exposure"]  # Already negative
)
```

## Conclusion

Consistent sign handling is critical for financial calculations. By following these best practices, we can avoid common pitfalls and ensure that our calculations are correct and maintainable.

Remember:
1. Store values with their natural signs
2. Use simple addition for aggregation
3. Avoid categorization based on signs when possible
4. Be consistent with sign conventions
5. Use clear variable names

These principles will help ensure that our financial calculations are correct, maintainable, and easy to understand.
