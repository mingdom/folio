# Testing Guidelines

This document outlines the testing philosophy, principles, and best practices for the Folio project. These guidelines are designed to help maintain a high-quality, maintainable test suite that provides confidence in our codebase without becoming a burden to maintain.

## Testing Philosophy

Our testing approach is guided by the following principles:

1. **Test behavior, not implementation**: Focus on what the code does, not how it does it.
2. **Optimize for maintainability**: Tests should be easy to understand and modify.
3. **Prefer unit tests with selective integration tests**: Unit tests for most code, integration tests for critical paths.
4. **Test public interfaces**: Only test public methods and functions, not implementation details.
5. **Keep tests simple**: Simple tests are easier to understand and maintain.
6. **Tests should fail for a single reason**: Each test should verify one specific behavior.
7. **Tests should be deterministic**: Tests should consistently pass or fail.

## Test Types and Their Purpose

### Unit Tests

Unit tests verify that individual components (functions, methods, classes) work correctly in isolation. They should:

- Be fast and lightweight
- Test a single unit of functionality
- Mock external dependencies
- Cover the majority of your codebase

### Integration Tests

Integration tests verify that multiple components work correctly together. They should:

- Test critical paths through the system
- Use minimal mocking (only for external services)
- Be more focused on end-to-end behavior

### End-to-End Tests

E2E tests verify that the entire system works correctly from the user's perspective. They should:

- Be few in number
- Test only the most critical user flows
- Run in a realistic environment

## Test Structure

Follow the Arrange-Act-Assert (AAA) pattern:

```python
def test_calculate_portfolio_beta():
    # Arrange: Set up test data and dependencies
    portfolio = Portfolio()
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10, price=150))
    mock_data_fetcher = MagicMock()
    mock_data_fetcher.get_beta.return_value = 1.2

    # Act: Call the method under test
    beta = portfolio.calculate_beta(data_fetcher=mock_data_fetcher)

    # Assert: Verify the result
    assert beta == 1.2
```

## Test Naming

Use descriptive names that explain what is being tested and the expected outcome:

```python
# ❌ Bad: Vague test name
def test_portfolio():
    # ...

# ✅ Good: Clear test name
def test_portfolio_beta_calculation_with_single_stock():
    # ...
```

## Key Guidelines

### 1. Focus on Outputs, Not Internal Calls

Tests should verify the outputs of functions/methods based on given inputs, not which internal methods were called.

```python
# ❌ Bad: Testing internal calls
def test_bad_internal_calls():
    mock_data_provider = MagicMock()
    mock_data_provider.get_price.return_value = 150.0

    portfolio_service = PortfolioService(data_provider=mock_data_provider)
    result = portfolio_service.calculate_exposure("AAPL", 10)

    # Testing implementation details
    mock_data_provider.get_price.assert_called_once_with("AAPL")

# ✅ Good: Testing outputs
def test_good_outputs():
    mock_data_provider = MagicMock()
    mock_data_provider.get_price.return_value = 150.0

    portfolio_service = PortfolioService(data_provider=mock_data_provider)
    result = portfolio_service.calculate_exposure("AAPL", 10)

    # Testing the result, not how it was calculated
    assert result == 1500.0  # 10 shares * $150 per share
```

### 2. Mock at the System Boundaries

Only mock external dependencies (APIs, databases, etc.), not internal components.

```python
# ❌ Bad: Mocking internal components
def test_bad_internal_mocking():
    # TickerService is an internal component
    mock_ticker_service = MagicMock()
    mock_ticker_service.get_price.return_value = 150.0

    # Mocking an internal component
    portfolio_service = PortfolioService()
    portfolio_service.ticker_service = mock_ticker_service

    result = portfolio_service.calculate_exposure("AAPL", 10)
    assert result == 1500.0

# ✅ Good: Mocking at system boundaries
def test_good_boundary_mocking():
    # MarketDataProvider is an external API
    mock_market_data = MagicMock()
    mock_market_data.get_price.return_value = 150.0

    # Injecting the mock at the system boundary
    portfolio_service = PortfolioService(market_data_provider=mock_market_data)

    result = portfolio_service.calculate_exposure("AAPL", 10)
    assert result == 1500.0
```

### 3. Test State Changes, Not Implementation

Verify that the expected state changes occurred, not how they occurred.

```python
# ❌ Bad: Testing implementation details
def test_bad_implementation_testing():
    portfolio = Portfolio()

    with patch.object(portfolio, '_update_position_price') as mock_update:
        portfolio.add_position(StockPosition(ticker="AAPL", quantity=10))

        # Testing that a specific internal method was called
        mock_update.assert_called_once()

# ✅ Good: Testing state changes
def test_good_state_testing():
    portfolio = Portfolio()

    # Before state
    assert len(portfolio.positions) == 0

    # Action
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10))

    # After state - testing what changed, not how
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].ticker == "AAPL"
    assert portfolio.positions[0].quantity == 10
```

### 4. Write Refactor-Friendly Tests

Tests should survive reasonable refactoring of the implementation.

```python
# ❌ Bad: Brittle test that breaks with refactoring
def test_brittle():
    mock_data_provider = MagicMock()
    mock_data_provider.get_price.return_value = 150.0

    service = PortfolioService(data_provider=mock_data_provider)
    result = service.calculate_portfolio_value([
        {"ticker": "AAPL", "quantity": 10}
    ])

    # This will break if implementation changes to use a different method
    mock_data_provider.get_price.assert_called_once_with("AAPL")

# ✅ Good: Resilient test that survives refactoring
def test_resilient():
    mock_data_provider = MagicMock()
    mock_data_provider.get_price.return_value = 150.0

    service = PortfolioService(data_provider=mock_data_provider)
    result = service.calculate_portfolio_value([
        {"ticker": "AAPL", "quantity": 10}
    ])

    # This will pass regardless of how the value is calculated
    assert result == 1500.0
```

## Real-World Example: Ticker Service Refactoring

The following examples demonstrate how our tests should handle the refactoring from direct `market_data_provider` usage to using the `ticker_service`.

### Example: Testing Portfolio Exposures

```python
# ❌ Bad: Testing implementation details
def test_bad_get_portfolio_exposures():
    # Setup
    portfolio = create_test_portfolio_with_stock("AAPL", 10, 150.0)
    mock_market_data = MagicMock()
    mock_market_data.get_price.return_value = 150.0
    mock_market_data.get_beta.return_value = 1.2

    # Patching an internal implementation detail
    with patch('src.folib.services.portfolio_service.market_data_provider', mock_market_data):
        # Act
        exposures = get_portfolio_exposures(portfolio)

        # Assert implementation details
        mock_market_data.get_price.assert_called_with("AAPL")
        mock_market_data.get_beta.assert_called_with("AAPL")

# ✅ Good: Testing behavior and results
def test_good_get_portfolio_exposures():
    # Setup
    portfolio = create_test_portfolio_with_stock("AAPL", 10, 150.0)

    # Create a test double for the external dependency
    mock_market_data = MagicMock()
    mock_market_data.get_price.return_value = 150.0
    mock_market_data.get_beta.return_value = 1.2

    # Inject the mock at the system boundary
    # This could be through dependency injection or a test-specific factory
    portfolio_service = create_portfolio_service_with_mock_data(mock_market_data)

    # Act
    exposures = portfolio_service.get_portfolio_exposures(portfolio)

    # Assert the results, not the implementation
    assert exposures["long_stock_exposure"] == 1500.0  # 10 shares * $150
    assert exposures["beta_adjusted_exposure"] == 1800.0  # $1500 * 1.2 beta
```

## Common Testing Pitfalls

### 1. Over-specifying Tests

```python
# ❌ Bad: Over-specified test
def test_over_specified():
    service = PortfolioService()

    # Testing exact implementation details
    with patch('src.folib.services.portfolio_service._calculate_beta') as mock_calc:
        mock_calc.return_value = 1.2
        result = service.get_portfolio_beta(portfolio)

        # Testing internal implementation
        mock_calc.assert_called_once()
        assert result == 1.2
```

### 2. Testing Private Methods

```python
# ❌ Bad: Testing private methods
def test_private_method():
    service = PortfolioService()

    # Directly testing a private method
    result = service._calculate_beta(portfolio)

    assert result == 1.2
```

### 3. Excessive Mocking

```python
# ❌ Bad: Excessive mocking
def test_excessive_mocking():
    # Mocking too many things
    mock_portfolio = MagicMock()
    mock_position = MagicMock()
    mock_calculator = MagicMock()
    mock_data_provider = MagicMock()
    mock_logger = MagicMock()

    # Test becomes hard to understand and brittle
    service = PortfolioService(
        data_provider=mock_data_provider,
        calculator=mock_calculator,
        logger=mock_logger
    )
    result = service.analyze_portfolio(mock_portfolio)
```

## What to Test

### Do Test

1. **Public interfaces**: Methods and functions that are part of your public API
2. **Business logic**: Core calculations and algorithms
3. **Edge cases**: Boundary conditions, empty inputs, etc.
4. **Error handling**: How your code handles invalid inputs or error conditions

### Don't Test

1. **Implementation details**: Private methods, internal state
2. **Framework functionality**: Features provided by libraries or frameworks
3. **Trivial code**: Simple getters/setters, pass-through methods
4. **External services**: Use mocks instead

## Test Data

Keep test data minimal and focused on what's being tested:

```python
# ❌ Bad: Excessive test data
def test_with_excessive_data():
    # Creating more data than needed
    portfolio = create_complex_portfolio_with_50_positions()
    # ...

# ✅ Good: Minimal test data
def test_with_minimal_data():
    # Only create what's needed for this specific test
    portfolio = Portfolio()
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10, price=150))
    # ...
```

## Test Fixtures and Setup

Use fixtures for common setup, but keep them focused:

```python
# ❌ Bad: Monolithic fixture
@pytest.fixture
def complex_test_environment():
    # Setting up too many things
    db = setup_database()
    cache = setup_cache()
    api = setup_api()
    portfolio = create_portfolio()
    market_data = load_market_data()
    # ...
    return {
        "db": db,
        "cache": cache,
        "api": api,
        "portfolio": portfolio,
        "market_data": market_data,
    }

# ✅ Good: Focused fixtures
@pytest.fixture
def sample_portfolio():
    portfolio = Portfolio()
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10, price=150))
    portfolio.add_position(StockPosition(ticker="MSFT", quantity=5, price=200))
    return portfolio

@pytest.fixture
def mock_data_fetcher():
    mock = MagicMock()
    mock.get_beta.return_value = 1.2
    mock.get_price.return_value = 150.0
    return mock
```

## Testing External Dependencies

For code that interacts with external services (APIs, databases, etc.):

1. **Unit tests**: Mock the external dependency completely
2. **Integration tests**: Use a test double (e.g., in-memory database)
3. **E2E tests**: Use the real dependency in a controlled environment

```python
# Unit test with mocked dependency
def test_get_stock_price_unit():
    mock_api = MagicMock()
    mock_api.get_price.return_value = 150.0

    stock_service = StockService(api=mock_api)
    price = stock_service.get_stock_price("AAPL")

    assert price == 150.0
    mock_api.get_price.assert_called_once_with("AAPL")

# Integration test with test double
def test_get_stock_price_integration():
    # Using a fake API implementation that doesn't make real network calls
    fake_api = FakeStockAPI({
        "AAPL": 150.0,
        "MSFT": 200.0
    })

    stock_service = StockService(api=fake_api)
    price = stock_service.get_stock_price("AAPL")

    assert price == 150.0
```

## Testing Error Handling

Test both the happy path and error cases:

```python
def test_get_stock_price_success():
    mock_api = MagicMock()
    mock_api.get_price.return_value = 150.0

    stock_service = StockService(api=mock_api)
    price = stock_service.get_stock_price("AAPL")

    assert price == 150.0

def test_get_stock_price_api_error():
    mock_api = MagicMock()
    mock_api.get_price.side_effect = APIError("API rate limit exceeded")

    stock_service = StockService(api=mock_api)

    with pytest.raises(StockServiceError) as excinfo:
        stock_service.get_stock_price("AAPL")

    assert "Failed to fetch stock price" in str(excinfo.value)
    assert "API rate limit exceeded" in str(excinfo.value)
```

## Conclusion

By following these guidelines, we can create tests that:

1. Focus on behavior, not implementation
2. Are resilient to refactoring
3. Provide confidence in our code
4. Are easier to maintain

Remember: The goal of testing is to verify that our code works correctly, not to verify how it works.
