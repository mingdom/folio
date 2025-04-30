---
description: Testing guidelines and best practices for the Folio project
alwaysApply: true
---

# Folio Testing Guidelines

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
    mock_data_fetcher.get_beta.assert_called_once_with("AAPL")
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

## Mocking

Use mocking judiciously to isolate the code under test:

```python
# ❌ Bad: Over-mocking
def test_over_mocked():
    # Mocking too many things makes tests brittle
    mock_portfolio = MagicMock()
    mock_position = MagicMock()
    mock_calculator = MagicMock()
    mock_logger = MagicMock()
    # ...

# ✅ Good: Focused mocking
def test_portfolio_beta_calculation():
    # Only mock external dependencies
    portfolio = Portfolio()
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10, price=150))

    # Mock only the external data fetcher
    mock_data_fetcher = MagicMock()
    mock_data_fetcher.get_beta.return_value = 1.2

    beta = portfolio.calculate_beta(data_fetcher=mock_data_fetcher)
    assert beta == 1.2
```

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

## Examples of Good vs. Bad Tests

### Example 1: Testing Public vs. Private Methods

```python
class PortfolioAnalyzer:
    def calculate_portfolio_metrics(self, portfolio):
        """Public method that calculates portfolio metrics."""
        total_value = self._calculate_total_value(portfolio)
        beta = self._calculate_portfolio_beta(portfolio, total_value)
        return {
            "total_value": total_value,
            "beta": beta,
        }

    def _calculate_total_value(self, portfolio):
        """Private helper method."""
        return sum(position.market_value for position in portfolio.positions)

    def _calculate_portfolio_beta(self, portfolio, total_value):
        """Private helper method."""
        if total_value == 0:
            return 0

        weighted_beta_sum = sum(
            position.market_value * position.beta
            for position in portfolio.positions
        )
        return weighted_beta_sum / total_value

# ❌ Bad: Testing private methods
def test_calculate_total_value():
    analyzer = PortfolioAnalyzer()
    portfolio = create_test_portfolio()

    # Testing a private method directly
    value = analyzer._calculate_total_value(portfolio)

    assert value == 2000

# ✅ Good: Testing public interface
def test_calculate_portfolio_metrics():
    analyzer = PortfolioAnalyzer()
    portfolio = create_test_portfolio()

    # Testing the public method
    metrics = analyzer.calculate_portfolio_metrics(portfolio)

    assert metrics["total_value"] == 2000
    assert metrics["beta"] == 1.1
```

### Example 2: Testing Behavior vs. Implementation

```python
class PortfolioLoader:
    def load_portfolio(self, file_path):
        """Loads a portfolio from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            return self._process_portfolio_data(df)
        except FileNotFoundError:
            logger.error(f"Portfolio file not found: {file_path}")
            raise

    def _process_portfolio_data(self, df):
        # Process the data...
        return Portfolio(positions=positions)

# ❌ Bad: Testing implementation details
def test_load_portfolio_implementation():
    loader = PortfolioLoader()

    # Mocking pandas and testing implementation details
    with patch("pandas.read_csv") as mock_read_csv:
        mock_df = pd.DataFrame({"ticker": ["AAPL"], "quantity": [10], "price": [150]})
        mock_read_csv.return_value = mock_df

        with patch.object(loader, "_process_portfolio_data") as mock_process:
            mock_process.return_value = "processed_portfolio"

            result = loader.load_portfolio("portfolio.csv")

            mock_read_csv.assert_called_once_with("portfolio.csv")
            mock_process.assert_called_once_with(mock_df)
            assert result == "processed_portfolio"

# ✅ Good: Testing behavior
def test_load_portfolio_behavior():
    loader = PortfolioLoader()

    # Create a temporary CSV file for testing
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+") as temp_file:
        # Write test data to the file
        temp_file.write("ticker,quantity,price\nAAPL,10,150\n")
        temp_file.flush()

        # Test the behavior
        portfolio = loader.load_portfolio(temp_file.name)

        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].ticker == "AAPL"
        assert portfolio.positions[0].quantity == 10
        assert portfolio.positions[0].price == 150
```

### Example 3: Simple vs. Complex Tests

```python
# ❌ Bad: Overly complex test
def test_complex_portfolio_analysis():
    # Setting up a complex scenario with too many moving parts
    portfolio = Portfolio()
    for i in range(20):
        portfolio.add_position(
            StockPosition(
                ticker=f"STOCK{i}",
                quantity=10 * i,
                price=100 + i * 5
            )
        )

    # Adding options positions
    for i in range(5):
        portfolio.add_position(
            OptionPosition(
                ticker=f"STOCK{i}",
                quantity=5,
                strike=100,
                expiry=date.today() + timedelta(days=30),
                option_type="CALL",
                price=5
            )
        )

    # Complex setup of mocks
    mock_data_fetcher = MagicMock()
    mock_data_fetcher.get_beta.side_effect = lambda ticker: float(ticker[5:]) * 0.1
    mock_data_fetcher.get_price.side_effect = lambda ticker: 100 + float(ticker[5:]) * 5

    # Complex analysis with multiple steps
    analyzer = PortfolioAnalyzer(data_fetcher=mock_data_fetcher)
    result = analyzer.perform_complex_analysis(
        portfolio,
        include_options=True,
        risk_free_rate=0.02,
        market_return=0.08,
        volatility=0.15
    )

    # Multiple assertions checking many different things
    assert result["total_value"] > 0
    assert result["beta"] > 0
    assert result["sharpe_ratio"] > 0
    assert result["option_delta"] > 0
    assert result["option_gamma"] > 0
    # ... many more assertions

# ✅ Good: Simple, focused tests
def test_portfolio_total_value_calculation():
    portfolio = Portfolio()
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10, price=150))
    portfolio.add_position(StockPosition(ticker="MSFT", quantity=5, price=200))

    analyzer = PortfolioAnalyzer()
    result = analyzer.calculate_portfolio_metrics(portfolio)

    assert result["total_value"] == 2500  # 10*150 + 5*200

def test_portfolio_beta_calculation():
    portfolio = Portfolio()
    portfolio.add_position(StockPosition(ticker="AAPL", quantity=10, price=150, beta=1.2))
    portfolio.add_position(StockPosition(ticker="MSFT", quantity=5, price=200, beta=1.0))

    analyzer = PortfolioAnalyzer()
    result = analyzer.calculate_portfolio_metrics(portfolio)

    # (1500*1.2 + 1000*1.0) / 2500 = 1.12
    assert result["beta"] == 1.12

def test_option_delta_calculation():
    portfolio = Portfolio()
    portfolio.add_position(
        OptionPosition(
            ticker="AAPL",
            quantity=1,
            strike=150,
            expiry=date.today() + timedelta(days=30),
            option_type="CALL",
            price=5,
            delta=0.6
        )
    )

    analyzer = PortfolioAnalyzer()
    result = analyzer.calculate_option_exposure(portfolio)

    assert result["delta_exposure"] == 60  # 1 contract * 100 shares * 0.6 delta
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

## Test Coverage

Aim for high test coverage, but don't pursue 100% coverage at the expense of test quality:

- Focus on testing critical business logic thoroughly
- It's okay to have lower coverage for simple, low-risk code
- Use coverage tools to identify untested code, not as a goal in itself

## Testing Asynchronous Code

For asynchronous code, ensure your tests properly await async functions:

```python
async def test_async_stock_price_fetch():
    mock_api = AsyncMock()
    mock_api.get_price.return_value = 150.0

    stock_service = AsyncStockService(api=mock_api)
    price = await stock_service.get_stock_price("AAPL")

    assert price == 150.0
    mock_api.get_price.assert_called_once_with("AAPL")
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

## Test Organization

Organize tests to mirror your production code structure:

```
src/
  folio/
    portfolio.py
    stock.py
tests/
  folio/
    test_portfolio.py
    test_stock.py
```

Group related tests into classes:

```python
class TestPortfolio:
    def test_add_position(self):
        # ...

    def test_calculate_total_value(self):
        # ...

    def test_calculate_beta(self):
        # ...
```

## Continuous Integration

Run tests automatically on every pull request and merge to main:

- Run unit tests on every PR
- Run integration tests on every PR
- Run E2E tests before merging to main

## Conclusion

Following these testing guidelines will help maintain a high-quality, maintainable test suite that provides confidence in our codebase. Remember that tests are code too, and they should be held to the same quality standards as production code.

The goal is not to have the most tests, but to have the right tests that give us confidence in our code without becoming a burden to maintain.
