"""
Tests for the TickerService class.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.folib.data.ticker_data import TickerData
from src.folib.services.ticker_service import TickerService


@pytest.fixture
def mock_market_data_provider():
    """Create a mock market data provider."""
    provider = MagicMock()

    # Set up mock responses
    provider.get_price.return_value = 150.0
    provider.get_beta.return_value = 1.2
    provider.get_company_profile.return_value = {"name": "Apple Inc."}

    return provider


@pytest.fixture
def ticker_service(mock_market_data_provider):
    """Create a TickerService with a mock market data provider."""
    return TickerService(market_data_provider=mock_market_data_provider)


def test_get_ticker_data(ticker_service, mock_market_data_provider):
    """Test getting ticker data."""
    # Get ticker data
    ticker_data = ticker_service.get_ticker_data("AAPL")

    # Verify the result
    assert ticker_data.ticker == "AAPL"
    assert ticker_data.price == 150.0
    assert ticker_data.beta == 1.2
    assert ticker_data.company_profile == {"name": "Apple Inc."}
    assert ticker_data.last_updated is not None

    # Verify the market data provider was called
    mock_market_data_provider.get_price.assert_called_once_with("AAPL")
    mock_market_data_provider.get_beta.assert_called_once_with("AAPL")
    mock_market_data_provider.get_company_profile.assert_called_once_with("AAPL")


def test_get_ticker_data_caching(ticker_service, mock_market_data_provider):
    """Test that ticker data is cached."""
    # Get ticker data twice
    ticker_service.get_ticker_data("AAPL")
    ticker_service.get_ticker_data("AAPL")

    # Verify the market data provider was called only once
    mock_market_data_provider.get_price.assert_called_once_with("AAPL")
    mock_market_data_provider.get_beta.assert_called_once_with("AAPL")
    mock_market_data_provider.get_company_profile.assert_called_once_with("AAPL")


def test_get_price(ticker_service):
    """Test getting a price."""
    price = ticker_service.get_price("AAPL")
    assert price == 150.0


def test_get_beta(ticker_service):
    """Test getting a beta value."""
    beta = ticker_service.get_beta("AAPL")
    assert beta == 1.2


def test_get_company_profile(ticker_service):
    """Test getting a company profile."""
    profile = ticker_service.get_company_profile("AAPL")
    assert profile == {"name": "Apple Inc."}


def test_prefetch_tickers(ticker_service, mock_market_data_provider):
    """Test prefetching multiple tickers."""

    # Set up different responses for different tickers
    def get_price_side_effect(ticker):
        if ticker == "AAPL":
            return 150.0
        elif ticker == "MSFT":
            return 250.0
        else:
            raise ValueError(f"Unknown ticker: {ticker}")

    mock_market_data_provider.get_price.side_effect = get_price_side_effect

    # Prefetch tickers
    ticker_service.prefetch_tickers(["AAPL", "MSFT", "UNKNOWN"])

    # Verify the results
    assert ticker_service.get_price("AAPL") == 150.0
    assert ticker_service.get_price("MSFT") == 250.0

    # The unknown ticker should not cause an error in prefetch
    # but should return default values when accessed
    assert ticker_service.get_price("UNKNOWN") == 0.0


def test_clear_cache(ticker_service):
    """Test clearing the cache."""
    # Get ticker data to populate the cache
    ticker_service.get_ticker_data("AAPL")

    # Clear the cache
    ticker_service.clear_cache()

    # Get ticker data again
    ticker_service.get_ticker_data("AAPL")

    # Verify the market data provider was called twice
    assert ticker_service._market_data_provider.get_price.call_count == 2


def test_cache_expiration(ticker_service, mock_market_data_provider):
    """Test that cached data expires."""
    # Get ticker data
    ticker_data = ticker_service.get_ticker_data("AAPL")

    # Modify the last_updated time to make it expired
    expired_time = datetime.now() - timedelta(days=2)
    ticker_service._ticker_data["AAPL"] = TickerData(
        ticker="AAPL",
        price=ticker_data.price,
        beta=ticker_data.beta,
        company_profile=ticker_data.company_profile,
        last_updated=expired_time,
    )

    # Get ticker data again
    ticker_service.get_ticker_data("AAPL")

    # Verify the market data provider was called twice
    assert mock_market_data_provider.get_price.call_count == 2


def test_cash_like_ticker(ticker_service, mock_market_data_provider):
    """Test handling of cash-like tickers."""
    # Set up mock to return None for cash-like ticker
    mock_market_data_provider.get_price.return_value = None
    mock_market_data_provider.get_beta.return_value = None

    # Get data for a cash-like ticker
    ticker_data = ticker_service.get_ticker_data("SPAXX")

    # Verify the effective values
    assert ticker_data.effective_price == 1.0
    assert ticker_data.effective_beta == 0.0

    # Verify the service methods return the correct values
    assert ticker_service.get_price("SPAXX") == 1.0
    assert ticker_service.get_beta("SPAXX") == 0.0
