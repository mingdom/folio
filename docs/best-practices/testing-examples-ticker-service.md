---
description: Examples of good and bad tests for the ticker service refactoring
---

# Testing Examples: Ticker Service Refactoring

This document provides concrete examples of good and bad testing practices based on our recent ticker service refactoring. It serves as a practical companion to our testing guidelines.

## The Refactoring Context

We recently refactored our code to use a centralized `ticker_service` instead of directly accessing the `market_data_provider`. This change improved our architecture by:

1. Centralizing market data access
2. Providing consistent handling of special cases (like cash positions)
3. Adding caching capabilities

However, this refactoring broke some tests because they were testing implementation details rather than behavior.

## Example 1: Testing Portfolio Summary Creation

### The Failing Test

```python
@patch("src.folib.services.portfolio_service.market_data_provider")
@patch("src.folib.services.portfolio_service.calculate_option_delta")
def test_create_portfolio_summary_with_stock_and_option(
    self, mock_calculate_delta, mock_market_data, sample_portfolio
):
    """Test creating a portfolio summary with stock and option positions."""
    # Arrange
    # Configure the mock market data provider
    mock_market_data.get_price.return_value = 150.0
    mock_market_data.get_beta.return_value = 1.2
    mock_calculate_delta.return_value = 0.6

    # Act
    summary = create_portfolio_summary(sample_portfolio)

    # Assert
    assert isinstance(summary, PortfolioSummary)
    assert summary.total_value > 0
    assert summary.stock_value == 1500.0  # 10 * 150.0
    assert summary.option_value == 1000.0  # 2 contracts * 100 shares * 5.0
    assert summary.pending_activity_value == 100.0

    # Verify new fields
    assert hasattr(summary, "net_exposure_pct")
    assert hasattr(summary, "beta_adjusted_exposure")
    assert summary.net_exposure_pct >= 0
    assert summary.beta_adjusted_exposure != 0

    # Verify the exposure calculations were called correctly
    mock_market_data.get_price.assert_called_with("AAPL")  # This line fails
    mock_market_data.get_beta.assert_called_with("AAPL")
    # The function is called at least once for option exposure calculation
    assert mock_calculate_delta.call_count >= 1
```

### Why This Test Is Problematic

1. **Testing Implementation Details**: The test verifies that specific methods on `mock_market_data` are called, which is an implementation detail.

2. **Brittle to Refactoring**: The test broke when we refactored to use `ticker_service` instead of directly using `market_data_provider`.

3. **Focusing on Calls Rather Than Results**: The test is more concerned with which methods are called than with the correctness of the final result.

### A Better Approach

```python
def test_create_portfolio_summary_with_stock_and_option_better(self, sample_portfolio):
    """Test creating a portfolio summary with stock and option positions."""
    # Arrange
    # Create a test double for the external dependency
    mock_ticker_service = create_mock_ticker_service({
        "AAPL": {"price": 150.0, "beta": 1.2}
    })

    # Act
    # Use a test-specific factory or dependency injection
    with use_mock_ticker_service(mock_ticker_service):
        summary = create_portfolio_summary(sample_portfolio)

    # Assert
    # Focus on the results, not how they were calculated
    assert isinstance(summary, PortfolioSummary)
    assert summary.total_value > 0
    assert summary.stock_value == 1500.0  # 10 * 150.0
    assert summary.option_value == 1000.0  # 2 contracts * 100 shares * 5.0
    assert summary.pending_activity_value == 100.0
    assert summary.net_exposure_pct >= 0
    assert summary.beta_adjusted_exposure != 0

    # Optional: Verify the beta-adjusted exposure is calculated correctly
    # This tests the business logic without testing implementation details
    expected_beta_adjusted = 1500.0 * 1.2  # stock value * beta
    assert abs(summary.beta_adjusted_exposure - expected_beta_adjusted) < 0.01
```

## Example 2: Testing Portfolio Exposures

### The Failing Test

```python
@patch("src.folib.services.portfolio_service.market_data_provider")
@patch("src.folib.services.portfolio_service.calculate_option_delta")
def test_get_portfolio_exposures(
    self, mock_calculate_delta, mock_market_data, sample_portfolio
):
    """Test calculating portfolio exposures."""
    # Arrange
    # Configure the mock market data provider
    mock_market_data.get_price.return_value = 150.0
    mock_market_data.get_beta.return_value = 1.2
    mock_calculate_delta.return_value = 0.6

    # Act
    exposures = get_portfolio_exposures(sample_portfolio)

    # Assert
    assert isinstance(exposures, dict)
    assert "long_stock_exposure" in exposures
    assert "long_option_exposure" in exposures
    assert "net_market_exposure" in exposures
    assert "beta_adjusted_exposure" in exposures

    # Verify the exposure calculations were called correctly
    mock_market_data.get_price.assert_called_with("AAPL")  # This line fails
    mock_market_data.get_beta.assert_called_with("AAPL")
    mock_calculate_delta.assert_called_once()
```

### Why This Test Is Problematic

1. **Testing Implementation Details**: The test verifies that specific methods on `mock_market_data` are called, which is an implementation detail.

2. **Brittle to Refactoring**: The test broke when we refactored to use `ticker_service` instead of directly using `market_data_provider`.

3. **Insufficient Verification of Results**: The test only checks that certain keys exist in the result, not their values.

### A Better Approach

```python
def test_get_portfolio_exposures_better(self, sample_portfolio):
    """Test calculating portfolio exposures."""
    # Arrange
    # Create a test double for the external dependency
    mock_ticker_service = create_mock_ticker_service({
        "AAPL": {"price": 150.0, "beta": 1.2}
    })

    # Act
    # Use a test-specific factory or dependency injection
    with use_mock_ticker_service(mock_ticker_service):
        exposures = get_portfolio_exposures(sample_portfolio)

    # Assert
    # Focus on the results, not how they were calculated
    assert isinstance(exposures, dict)

    # Verify the actual exposure values
    assert exposures["long_stock_exposure"] == 1500.0  # 10 shares * $150
    assert exposures["beta_adjusted_exposure"] == 1800.0  # $1500 * 1.2 beta

    # Verify the net exposure calculation
    assert exposures["net_market_exposure"] == exposures["long_stock_exposure"] + exposures["long_option_exposure"] + exposures["short_stock_exposure"] + exposures["short_option_exposure"]
```

## Key Takeaways

1. **Focus on Outputs**: Test that the function returns the correct result, not how it calculated that result.

2. **Inject Mocks at System Boundaries**: Use dependency injection or test-specific factories to inject mocks at system boundaries.

3. **Verify Business Logic**: Test that the business logic is correct (e.g., beta-adjusted exposure = exposure * beta), not that specific methods were called.

4. **Use Test Doubles Wisely**: Create test doubles that provide the necessary test data without tightly coupling to implementation details.

## Practical Implementation Tips

1. **Create Test Helpers**: Implement helper functions like `create_mock_ticker_service()` and `use_mock_ticker_service()` to make tests cleaner and more maintainable.

2. **Use Context Managers**: Context managers can help with temporarily replacing services for testing.

3. **Inject Dependencies**: Design your code to accept dependencies through constructors or method parameters, making it easier to inject test doubles.

4. **Test Business Rules**: Focus on testing that business rules are correctly implemented, not that specific methods are called.

By following these practices, we can create tests that are more resilient to refactoring while still providing confidence in our code's correctness.
