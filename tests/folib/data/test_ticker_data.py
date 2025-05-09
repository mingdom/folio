"""
Tests for the TickerData class.
"""

from datetime import datetime

from src.folib.data.ticker_data import TickerData


def test_ticker_data_creation():
    """Test creating a TickerData object."""
    ticker_data = TickerData(
        ticker="AAPL",
        price=150.0,
        beta=1.2,
        company_profile={"name": "Apple Inc."},
        last_updated=datetime.now(),
        description="Apple Inc.",
    )

    assert ticker_data.ticker == "AAPL"
    assert ticker_data.price == 150.0
    assert ticker_data.beta == 1.2
    assert ticker_data.company_profile == {"name": "Apple Inc."}
    assert ticker_data.description == "Apple Inc."
    assert ticker_data.last_updated is not None


def test_is_cash_like_property():
    """Test the is_cash_like property."""
    # Cash-like ticker
    cash_ticker = TickerData(
        ticker="SPAXX",
        price=1.0,
        description="Fidelity Government Money Market Fund",
    )
    assert cash_ticker.is_cash_like is True

    # Regular stock ticker
    stock_ticker = TickerData(
        ticker="AAPL",
        price=150.0,
        description="Apple Inc.",
    )
    assert stock_ticker.is_cash_like is False


def test_effective_beta_property():
    """Test the effective_beta property."""
    # Cash-like ticker should have beta of 0.0 regardless of stored value
    cash_ticker = TickerData(
        ticker="SPAXX",
        beta=0.5,  # This should be ignored for cash-like tickers
        description="Fidelity Government Money Market Fund",
    )
    assert cash_ticker.effective_beta == 0.0

    # Regular stock ticker with beta
    stock_ticker = TickerData(
        ticker="AAPL",
        beta=1.2,
    )
    assert stock_ticker.effective_beta == 1.2

    # Regular stock ticker without beta should default to 1.0
    stock_ticker_no_beta = TickerData(
        ticker="AAPL",
    )
    assert stock_ticker_no_beta.effective_beta == 1.0


def test_effective_price_property():
    """Test the effective_price property."""
    # Ticker with price
    ticker_with_price = TickerData(
        ticker="AAPL",
        price=150.0,
    )
    assert ticker_with_price.effective_price == 150.0

    # Cash-like ticker without price should default to 1.0
    cash_ticker_no_price = TickerData(
        ticker="SPAXX",
        description="Fidelity Government Money Market Fund",
    )
    assert cash_ticker_no_price.effective_price == 1.0

    # Regular ticker without price should default to 0.0
    ticker_no_price = TickerData(
        ticker="AAPL",
    )
    assert ticker_no_price.effective_price == 0.0
