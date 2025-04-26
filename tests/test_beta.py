from unittest.mock import patch

import pandas as pd
import pytest

from src.folio.utils import get_beta

# Test categories based on check_beta.py:
# 1. Money market funds (SPAXX**, FMPXX) - should have beta ≈ 0
# 2. Low volatility instruments (TLT, SHY, BIL) - should have beta near 0
# 3. Market correlated ETFs (MCHI, IEFA) - should have significant beta
# 4. High beta stocks (AAPL, GOOGL) - should have beta > 1
# 5. Market benchmark (SPY) - should have beta ≈ 1


@pytest.fixture
def mock_data_fetcher():
    """Create a mock DataFetcher that can be configured per test."""
    with patch("src.folio.utils.data_fetcher") as mock:
        yield mock


def create_price_data(returns_data, base_price=100.0):
    """Helper to create price data from a list of returns."""
    prices = [base_price]
    for ret in returns_data:
        prices.append(prices[-1] * (1 + ret))
    return pd.DataFrame({"Close": prices})


def test_money_market_fund(mock_data_fetcher):
    """Test that instruments with constant price return beta of 0."""
    # Money market funds typically have constant or near-constant prices
    constant_prices = pd.DataFrame({"Close": [1.00] * 100})
    market_data = create_price_data([0.01] * 99)  # Market with some movement

    mock_data_fetcher.fetch_data.return_value = constant_prices
    mock_data_fetcher.fetch_market_data.return_value = market_data

    beta = get_beta("SPAXX")
    assert beta == 0.0


def test_low_volatility_instrument(mock_data_fetcher):
    """Test that instruments with very low correlation to market have near-zero beta."""
    # Create price data with very small, uncorrelated movements
    tiny_movements = [0.0001 if i % 2 == 0 else -0.0001 for i in range(100)]
    market_movements = [0.01 if i % 3 == 0 else -0.01 for i in range(100)]

    mock_data_fetcher.fetch_data.return_value = create_price_data(tiny_movements)
    mock_data_fetcher.fetch_market_data.return_value = create_price_data(
        market_movements
    )

    beta = get_beta("TLT")
    assert abs(beta) < 0.1  # Low volatility instruments should have beta near 0


def test_market_correlated_etf(mock_data_fetcher):
    """Test that market-correlated ETFs have significant positive beta."""
    # Create correlated but dampened market movements
    market_moves = [0.01, -0.01, 0.02, -0.015, 0.025] * 20
    etf_moves = [0.007, -0.007, 0.014, -0.011, 0.018] * 20  # ~0.7x market moves

    mock_data_fetcher.fetch_data.return_value = create_price_data(etf_moves)
    mock_data_fetcher.fetch_market_data.return_value = create_price_data(market_moves)

    beta = get_beta("MCHI")
    assert 0.5 < beta < 1.0  # Should have significant but less than market beta


def test_high_beta_stock(mock_data_fetcher):
    """Test that volatile stocks can have beta > 1."""
    # Create amplified market movements
    market_moves = [0.01, -0.01, 0.02, -0.015, 0.025] * 20
    stock_moves = [0.015, -0.015, 0.03, -0.022, 0.037] * 20  # ~1.5x market moves

    mock_data_fetcher.fetch_data.return_value = create_price_data(stock_moves)
    mock_data_fetcher.fetch_market_data.return_value = create_price_data(market_moves)

    beta = get_beta("AAPL")
    assert beta > 1.0  # Should have higher than market beta


def test_market_benchmark(mock_data_fetcher):
    """Test that perfectly correlated instrument has beta ≈ 1."""
    # Use exact same movements for both
    moves = [0.01, -0.01, 0.02, -0.015, 0.025] * 20

    mock_data_fetcher.fetch_data.return_value = create_price_data(moves)
    mock_data_fetcher.fetch_market_data.return_value = create_price_data(moves)

    beta = get_beta("SPY")
    assert abs(beta - 1.0) < 0.01  # Should be very close to 1.0


def test_insufficient_data(mock_data_fetcher):
    """Test that instruments with insufficient data points return beta of 0."""
    mock_data_fetcher.fetch_data.return_value = create_price_data(
        [0.01]
    )  # Only 2 prices
    mock_data_fetcher.fetch_market_data.return_value = create_price_data([0.01])

    beta = get_beta("NEWSTOCK")
    assert beta == 0.0


def test_data_fetch_failure(mock_data_fetcher):
    """Test that data fetching failures raise appropriate errors."""
    mock_data_fetcher.fetch_data.return_value = None

    with pytest.raises(RuntimeError, match="Failed to fetch data"):
        get_beta("INVALID")


def test_all_null_data(mock_data_fetcher):
    """Test that all-null data returns beta of 0.0."""
    invalid_data = pd.DataFrame({"Close": [None, None, None]})
    mock_data_fetcher.fetch_data.return_value = invalid_data
    mock_data_fetcher.fetch_market_data.return_value = invalid_data

    beta = get_beta("BADDATA")
    assert beta == 0.0  # Should return 0.0 as we can't calculate meaningful beta


def test_invalid_data_format(mock_data_fetcher):
    """Test that data with invalid format raises appropriate errors."""
    # Data without required 'Close' column
    invalid_data = pd.DataFrame({"Wrong_Column": [1, 2, 3]})
    mock_data_fetcher.fetch_data.return_value = invalid_data
    mock_data_fetcher.fetch_market_data.return_value = create_price_data([0.01] * 10)

    with pytest.raises(KeyError):  # Should raise KeyError when trying to access 'Close'
        get_beta("BADFORMAT")
