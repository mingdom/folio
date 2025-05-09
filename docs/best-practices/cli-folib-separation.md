---
date: 2025-05-03
title: Best Practices for CLI and Folib Separation
author: Augment Agent
---

# Best Practices for CLI and Folib Separation

## Core Principle

The CLI should be a thin display interface that does not contain business logic. All business logic, data transformations, and calculations should be in the `src/folib/` library.

## Methodology for Fixing Business Logic Issues

When fixing issues where business logic is incorrectly placed in the CLI layer, follow this methodical approach:

### 1. Identify the Proper Location in Folib

- Determine where in the folib library the logic should live
- Check if related logic already exists
- Identify the appropriate module, class, or function to contain this logic
- Consider the domain model and existing service functions

### 2. Evaluate Existing Folib Logic

- If related logic exists, evaluate if it's correct
- Check for bugs or incorrect fallback logic in folib
- Determine if the issue in the CLI is compensating for a problem in folib
- Look for inconsistencies in how similar logic is handled elsewhere

### 3. Write Tests First (TDD Approach)

- Create tests that verify the expected behavior
- These tests should initially fail, confirming the issue
- Tests should be specific to the business logic, not the CLI display
- Consider edge cases and boundary conditions
- Tests should pass once the folib implementation is fixed

### 4. Implement the Fix in Folib

- Add or modify the appropriate code in folib
- Ensure the implementation follows folib's design principles
- Make the implementation consistent with similar functionality
- Verify that the tests now pass

### 5. Simplify the CLI Code

- Rewrite the CLI code assuming folib works perfectly
- Remove any business logic, calculations, or transformations
- CLI should only:
  - Parse user input
  - Call appropriate folib functions
  - Format and display the results
- Verify that the CLI still works correctly with the updated folib

## Example Pattern

### Before (Incorrect):

```python
# In CLI code
if position.position_type == "cash":
    beta = 0.0
    beta_adjusted_exposure = 0.0
else:
    beta = market_data_provider.get_beta(position.ticker) or 1.0
    market_exposure = calculate_exposure(position)
    beta_adjusted_exposure = market_exposure * beta
```

### After (Correct):

```python
# In folib domain.py or service
class CashPosition(Position):
    @property
    def beta(self) -> float:
        return 0.0

    @property
    def beta_adjusted_exposure(self) -> float:
        return 0.0

# In position_service.py
def get_position_beta(position: Position) -> float:
    if position.position_type == "cash":
        return 0.0
    return market_data_provider.get_beta(position.ticker) or 1.0

def calculate_position_beta_adjusted_exposure(position: Position) -> float:
    if position.position_type == "cash":
        return 0.0
    market_exposure = calculate_exposure(position)
    beta = get_position_beta(position)
    return market_exposure * beta

# In CLI code (simplified)
beta = position.beta  # Or position_service.get_position_beta(position)
beta_adjusted_exposure = position_service.calculate_position_beta_adjusted_exposure(position)
```

## Common Patterns to Watch For

1. **Conditional Logic Based on Position Type**: This almost always belongs in folib, not the CLI.

2. **Default Values**: Default values for business properties should be set in folib, not the CLI.

3. **Calculations**: Any calculations (exposure, beta-adjusted values, etc.) should be in folib.

4. **Fallback Logic**: Fallback logic for missing or invalid data should be in folib.

5. **Type-Specific Behavior**: Different behavior based on the type of a business object should be in folib.

## Benefits of Proper Separation

- **Maintainability**: Changes to business logic only need to be made in one place
- **Testability**: Business logic can be tested independently of the UI
- **Reusability**: The same business logic can be used by multiple interfaces (CLI, web, API)
- **Consistency**: Business logic is applied consistently across all interfaces
- **Clarity**: The responsibilities of each layer are clear and well-defined

## Conclusion

By maintaining a strict separation between the CLI display layer and the folib business logic layer, we create a more maintainable, testable, and extensible codebase. When fixing issues, always start by identifying where the logic should live in folib, write tests to verify the expected behavior, implement the fix in folib, and then simplify the CLI code to use the updated folib functionality.
