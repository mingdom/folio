---
description: Concise coding conventions for the Folio project
alwaysApply: true
---

# Folio Project Conventions

This document outlines the key coding conventions for the Folio project. These conventions are designed to help maintain code quality, readability, and consistency across the codebase.

## Project Tech Stack

- **Web Framework**: Dash (Python)
- **Data Processing**: Pandas, NumPy
- **Financial Data**: Yahoo Finance API (default), FMP API (optional)
- **Testing**: Pytest
- **Linting**: Flake8, Black, isort

## Core Conventions

### 1. Fail Fast and Transparently

Never hide errors with default values. Financial data must be accurate or explicitly marked as unavailable.

```python
# ❌ Bad: Hiding errors with defaults
def get_beta(ticker):
    try:
        return data_fetcher.get_beta(ticker)
    except Exception:
        return 1.0  # Dangerous default!

# ✅ Good: Transparent failure
def get_beta(ticker):
    try:
        return data_fetcher.get_beta(ticker)
    except Exception as e:
        logger.error(f"Failed to get beta for {ticker}: {e}", exc_info=True)
        raise  # Let the caller handle the error
```

### 2. Use Intention-Revealing Names

Names should clearly communicate what a variable, function, or class is for.

```python
# ❌ Bad: Unclear names
def calc(p, q):
    return p * q * 1.1

# ✅ Good: Clear names
def calculate_total_with_tax(price, quantity):
    return price * quantity * 1.1
```

### 3. Write Small, Focused Functions

Each function should do one thing well and be reasonably small.

```python
# ❌ Bad: Function doing too much
def process_portfolio(portfolio_data):
    # Validate data
    if not portfolio_data:
        raise ValueError("Empty portfolio")

    # Calculate metrics
    total_value = 0
    total_beta_adjusted = 0
    for position in portfolio_data:
        price = position["price"]
        quantity = position["quantity"]
        beta = get_beta(position["ticker"])
        value = price * quantity
        total_value += value
        total_beta_adjusted += value * beta

    # Generate report
    report = {
        "total_value": total_value,
        "portfolio_beta": total_beta_adjusted / total_value if total_value else 0,
        "positions": len(portfolio_data)
    }

    # Save to database
    db.save_portfolio_report(report)

    return report

# ✅ Good: Functions with single responsibilities
def validate_portfolio(portfolio_data):
    if not portfolio_data:
        raise ValueError("Empty portfolio")
    return portfolio_data

def calculate_position_metrics(position):
    price = position["price"]
    quantity = position["quantity"]
    beta = get_beta(position["ticker"])
    value = price * quantity
    beta_adjusted = value * beta
    return {"value": value, "beta_adjusted": value * beta}

def calculate_portfolio_metrics(portfolio_data):
    validated_data = validate_portfolio(portfolio_data)

    position_metrics = [calculate_position_metrics(pos) for pos in validated_data]

    total_value = sum(pos["value"] for pos in position_metrics)
    total_beta_adjusted = sum(pos["beta_adjusted"] for pos in position_metrics)

    return {
        "total_value": total_value,
        "portfolio_beta": total_beta_adjusted / total_value if total_value else 0,
        "positions": len(portfolio_data)
    }

def save_portfolio_report(report):
    db.save_portfolio_report(report)
    return report

def process_portfolio(portfolio_data):
    metrics = calculate_portfolio_metrics(portfolio_data)
    return save_portfolio_report(metrics)
```

### 4. Validate Early, Return Fast

Check inputs at the beginning of functions to avoid deep nesting and keep the happy path clean.

```python
# ❌ Bad: Deeply nested conditionals
def process_data(data):
    if data is not None:
        if "ticker" in data:
            if data["ticker"] != "":
                # Process the data...
                return result
            else:
                return None
        else:
            return None
    else:
        return None

# ✅ Good: Early validation
def process_data(data):
    if data is None:
        raise ValueError("Data cannot be None")
    if "ticker" not in data:
        raise ValueError("Missing required 'ticker' field")
    if data["ticker"] == "":
        raise ValueError("Ticker cannot be empty")

    # Process the data...
    return result
```

### 5. Comment the "Why," Not the "What"

Explain reasoning behind complex code, not obvious operations.

```python
# ❌ Bad: Commenting the obvious
# Calculate the sum of prices
total = sum(item.price for item in items)

# ❌ Bad: Commented-out code
# Old calculation method
# for item in items:
#     total += item.price

# ✅ Good: Explaining the why
# Apply 15% discount for bulk orders (>10 items) per company policy
if len(items) > 10:
    total *= 0.85
```

### 6. Write Minimal, Effective Tests

Focus on testing critical business logic, not framework functionality.

```python
# ❌ Bad: Testing framework functionality
def test_dataframe_creation():
    # This just tests pandas functionality, not our code
    data = {"ticker": ["AAPL"], "price": [150]}
    df = pd.DataFrame(data)
    assert len(df) == 1
    assert "ticker" in df.columns

# ✅ Good: Testing critical business logic
def test_portfolio_beta_calculation():
    # Arrange: Set up test data
    portfolio = Portfolio()
    portfolio.add_position(
        StockPosition(ticker="AAPL", quantity=10, price=150)
    )

    # Mock external dependencies
    data_fetcher = MagicMock()
    data_fetcher.get_beta.return_value = 1.2

    # Act: Call the method under test
    beta = portfolio.calculate_beta(data_fetcher=data_fetcher)

    # Assert: Verify the result
    assert beta == 1.2
    data_fetcher.get_beta.assert_called_once_with("AAPL")
```

### 7. Embrace Pythonic Idioms

Use Python's built-in features to write cleaner, more readable code.

```python
# ❌ Bad: Non-Pythonic code
result = []
for i in range(len(items)):
    if items[i].price > 100:
        result.append(items[i].name)

# ✅ Good: Pythonic code
result = [item.name for item in items if item.price > 100]

# ❌ Bad: Manual resource management
f = open("data.csv", "r")
try:
    data = f.read()
finally:
    f.close()

# ✅ Good: Context manager
with open("data.csv", "r") as f:
    data = f.read()
```

### 8. Use Type Hints

Add type hints to improve readability and enable static analysis.

```python
# ❌ Bad: No type hints
def calculate_position_value(quantity, price):
    return quantity * price

# ✅ Good: With type hints
def calculate_position_value(quantity: float, price: float) -> float:
    return quantity * price

# Even better: With more specific types and docstring
from typing import Dict, List, Optional

def get_positions_by_sector(
    positions: List[Dict[str, any]],
    sector: Optional[str] = None
) -> Dict[str, List[Dict[str, any]]]:
    """
    Group positions by sector.

    Args:
        positions: List of position dictionaries
        sector: Optional sector to filter by

    Returns:
        Dictionary mapping sectors to lists of positions
    """
    result = {}
    for position in positions:
        pos_sector = position.get("sector", "Unknown")
        if sector and pos_sector != sector:
            continue
        if pos_sector not in result:
            result[pos_sector] = []
        result[pos_sector].append(position)
    return result
```

### 9. Handle Errors Gracefully

Use exceptions with context and handle them appropriately.

```python
# ❌ Bad: Using error codes
def divide_stocks(total_value, num_stocks):
    if num_stocks == 0:
        return -1  # Error code
    return total_value / num_stocks

# Usage
result = divide_stocks(1000, 0)
if result == -1:
    print("Error: Cannot divide by zero")

# ✅ Good: Using exceptions
def divide_stocks(total_value: float, num_stocks: int) -> float:
    if num_stocks == 0:
        raise ValueError("Cannot divide by zero stocks")
    return total_value / num_stocks

# Usage
try:
    result = divide_stocks(1000, 0)
except ValueError as e:
    logger.error(f"Portfolio calculation error: {e}")
    # Handle the error appropriately
```

### 10. Keep It Simple (KISS)

Prefer simple, straightforward solutions over complex ones.

```python
# ❌ Bad: Overly complex
def is_valid_ticker(ticker):
    if ticker is not None:
        if isinstance(ticker, str):
            if len(ticker) > 0:
                if len(ticker) <= 5:
                    if ticker.isalpha():
                        return True
    return False

# ✅ Good: Simple and clear
def is_valid_ticker(ticker: str) -> bool:
    return (
        isinstance(ticker, str) and
        1 <= len(ticker) <= 5 and
        ticker.isalpha()
    )
```

## Additional Guidelines

1. **Strict Separation of Concerns**: Business logic MUST reside in the core library (`src/folio/`), not in interface layers (`src/focli/`).
   ```python
   # ❌ Bad: Business logic in CLI layer
   # src/focli/utils.py
   def calculate_position_value_with_price_change(position_group, price_change):
       # Business logic for calculating position value
       return new_value

   # ✅ Good: Business logic in core library
   # src/folio/portfolio_value.py
   def calculate_position_value_with_price_change(position_group, price_change):
       # Business logic for calculating position value
       return new_value

   # src/focli/commands/position.py
   def handle_position_command(args):
       # Only handle user interaction and call core library
       result = portfolio_value.calculate_position_value_with_price_change(
           position_group, price_change
       )
       # Format and display result
   ```

2. **Follow the Boy Scout Rule**: Leave the code cleaner than you found it.

3. **Don't Repeat Yourself (DRY)**: Extract repeated code into reusable functions.

4. **You Aren't Gonna Need It (YAGNI)**: Don't add functionality until it's necessary.

5. **Optimize After Measuring**: Profile code to identify actual bottlenecks before optimizing.

6. **Use Consistent Formatting**: Use Black, Flake8, and isort to maintain consistent code style.

7. **Imports at Top**: Always place all imports at the top of the file.

8. **No Unused Code**: Remove commented-out code and unused imports/variables.

9. **Configuration Over Hardcoding**: Use configuration files for values that might change.

10. **Log with Context**: Include relevant information in log messages.

11. **Make Small, Focused Changes**: Don't modify unrelated code when implementing a feature or fixing a bug.

## Benefits of Following These Conventions

- **Readability**: Code is easier to understand at a glance
- **Maintainability**: Simpler structure makes changes easier and safer
- **Testability**: Clear paths make testing more straightforward
- **Reliability**: Proper error handling prevents unexpected behavior
- **Performance**: Well-structured code leads to better performance
