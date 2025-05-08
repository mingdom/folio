# Simplifying Conditional Logic

This document demonstrates a real-world example of simplifying conditional logic in our codebase, following our core principles of maximizing simplicity and readability.

## Case Study: Portfolio Price Updates

We identified an issue where option positions paired with stocks were missing from portfolio listings. The root cause was in the `process_portfolio` function, which had complex conditional logic for updating position prices.

### Before: Complex Conditional Logic

```python
# Handle price updates based on the update_prices flag
if update_prices:
    logger.info("Updating prices for all positions from market data")
    positions = _update_all_prices(positions)
else:
    logger.info("Using raw CSV prices first, updating only unpaired option prices")
    # Only update prices for unpaired options
    unpaired_options = _identify_unpaired_options(positions)
    if unpaired_options:
        logger.info(f"Found {len(unpaired_options)} unpaired options to update")
        updated_options = _update_unpaired_option_prices(unpaired_options)

        # Keep track of which options are unpaired by ticker
        unpaired_tickers = {option.ticker for option in unpaired_options}

        # Remove only the unpaired options, keeping the paired ones
        positions = [
            pos
            for pos in positions
            if not (
                isinstance(pos, OptionPosition) and pos.ticker in unpaired_tickers
            )
        ]

        # Add back the updated unpaired options
        positions.extend(updated_options)
    else:
        logger.info(
            "No unpaired options found - using raw CSV prices for all positions"
        )
```

### Issues with the Original Code

1. **Excessive branching**: Multiple nested conditions make the code harder to follow
2. **Unclear responsibility**: The main function is handling too many details of the update process
3. **Poor separation of concerns**: Logic for identifying, updating, and replacing positions is mixed together
4. **Maintenance risk**: Complex conditional logic increases the chance of introducing bugs during future changes

### After: Simplified Logic with Better Abstraction

```python
# By default, update only unpaired options
logger.info("Using raw CSV prices first, updating only unpaired option prices")
positions = _update_unpaired_options_in_portfolio(positions)

# If update_prices flag is set, update all positions
if update_prices:
    logger.info("Updating prices for all positions from market data")
    positions = _update_all_prices(positions)
```

With a new helper function:

```python
def _update_unpaired_options_in_portfolio(positions: list[Position]) -> list[Position]:
    """
    Update prices for unpaired options in the portfolio.

    This function:
    1. Identifies options without matching stock positions
    2. Updates their prices from market data
    3. Returns a new positions list with updated unpaired options

    Args:
        positions: List of all positions

    Returns:
        Updated list of positions with new prices for unpaired options
    """
    # Identify options that don't have matching stock positions
    unpaired_options = _identify_unpaired_options(positions)

    if not unpaired_options:
        logger.info("No unpaired options found - using raw CSV prices for all positions")
        return positions

    logger.info(f"Found {len(unpaired_options)} unpaired options to update")
    updated_options = _update_unpaired_option_prices(unpaired_options)

    # Keep track of which options are unpaired by ticker
    unpaired_tickers = {option.ticker for option in unpaired_options}

    # Remove only the unpaired options, keeping the paired ones
    filtered_positions = [
        pos for pos in positions
        if not (isinstance(pos, OptionPosition) and pos.ticker in unpaired_tickers)
    ]

    # Add back the updated unpaired options
    filtered_positions.extend(updated_options)
    return filtered_positions
```

## Benefits of the Improved Approach

1. **Reduced complexity**: The main function is now much simpler with minimal branching
2. **Better abstraction**: Details of updating unpaired options are encapsulated in a dedicated function
3. **Clearer intent**: The code shows that updating unpaired options is the default behavior
4. **Improved maintainability**: Each function has a single responsibility
5. **Bug prevention**: The encapsulated logic is less likely to introduce subtle bugs

## Key Principles Applied

1. **Minimize branching**: Reduce conditional logic to improve readability
2. **Single responsibility**: Each function should do one thing well
3. **Appropriate abstraction**: Hide implementation details behind well-named functions
4. **Default path first**: Handle the common case as the default path
5. **Clear intent**: Code should clearly express what it's trying to accomplish

## Conclusion

This refactoring demonstrates our commitment to writing simple, maintainable code. By reducing conditional complexity and improving abstraction, we've made the code more robust and easier to understand.

Remember:
- Simplicity and readability are our highest priorities
- Minimize branching whenever possible
- Create focused helper functions for complex operations
- Make the common case the default path
