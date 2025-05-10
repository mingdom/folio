# Critical Tests for Portfolio Functionality

This directory contains critical tests for the portfolio functionality in the Folio application. These tests are marked as 'critical' because they verify core functionality that directly impacts user experience. Failures in these tests indicate serious issues that must be addressed immediately.

## Running Critical Tests

To run only the critical tests:

```bash
python -m pytest -m critical
```

To run critical tests with verbose output:

```bash
python -m pytest -m critical -v
```

To run all tests except critical tests:

```bash
python -m pytest -m "not critical"
```

## Adding New Critical Tests

To add a new critical test:

1. Create a test function in an appropriate test file
2. Add the `@pytest.mark.critical` decorator to the test function
3. Add a detailed docstring explaining why the test is critical

Example:

```python
@pytest.mark.critical
def test_important_functionality():
    """
    CRITICAL TEST: Verify that important functionality works correctly.

    This test ensures that... [detailed explanation]

    Failure in this test indicates a serious issue with... [impact explanation]
    """
    # Test implementation
```

## Current Critical Tests

### Portfolio Parsing Critical Tests

Located in `test_portfolio_parsing_critical.py`:

1. `test_option_positions_parsing`: Verifies that all option positions are correctly parsed from the portfolio CSV
2. `test_option_symbols_with_leading_space_or_hyphen`: Verifies that option symbols with leading spaces or hyphens are correctly parsed

### Portfolio Calculations Critical Tests

Located in `test_portfolio_calculations_critical.py`:

1. `test_portfolio_total_value_calculation`: Verifies that the portfolio total value is correctly calculated
2. `test_portfolio_exposure_calculation`: Verifies that portfolio exposure is correctly calculated
3. `test_portfolio_beta_adjusted_exposure_calculation`: Verifies that beta-adjusted exposure is correctly calculated
4. `test_portfolio_calculation_consistency`: Verifies that portfolio calculations are consistent across processing

## Why Critical Tests?

Critical tests help ensure that core functionality remains intact during development. They:

1. Highlight the most important aspects of the system
2. Provide early warning of regressions in critical functionality
3. Document expected behavior for core features
4. Serve as a safety net for refactoring

When a critical test fails, it should be addressed immediately before proceeding with other development work.
