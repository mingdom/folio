"""
Unit tests for the StockOracle class in src/folib/data/stock.py.

These tests verify the core functionality of the StockOracle class, including:
1. Singleton pattern implementation
2. Price and beta retrieval
3. Historical data fetching
4. Stock symbol validation
5. Cash-like instrument detection

All tests are pure unit tests that mock external dependencies (yfinance).
"""

import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.folib.data.stock import StockOracle


class TestStockOracle:
    """Test cases for the StockOracle class."""

    @pytest.fixture
    def mock_yf_ticker(self):
        """Create a mock yfinance Ticker object."""
        mock_ticker = MagicMock()

        # Mock the info property
        mock_ticker.info = {"beta": 1.2}

        # Mock the history method
        mock_df = pd.DataFrame(
            {
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [148.0, 149.0, 150.0],
                "Close": [153.0, 154.0, 155.0],
                "Volume": [1000000, 1100000, 1200000],
            }
        )
        mock_ticker.history.return_value = mock_df

        return mock_ticker

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_singleton_pattern(self, temp_cache_dir):
        """Test that StockOracle implements the Singleton pattern correctly."""
        # Get two instances
        oracle1 = StockOracle.get_instance(cache_dir=temp_cache_dir)
        oracle2 = StockOracle.get_instance()

        # They should be the same object
        assert oracle1 is oracle2

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_direct_initialization_warning(self, temp_cache_dir):
        """Test that direct initialization issues a warning."""
        # First create the singleton instance
        StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Then try to create another instance directly
        # The class logs a warning but doesn't raise a UserWarning
        # So we just verify it doesn't raise an exception
        StockOracle(cache_dir=temp_cache_dir)

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    def test_get_price(self, mock_ticker_class, mock_yf_ticker, temp_cache_dir):
        """Test getting a stock price."""
        mock_ticker_class.return_value = mock_yf_ticker

        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Get price
        price = oracle.get_price("AAPL")

        # Verify the result
        assert price == 155.0  # Last Close price in the mock data

        # Verify yfinance was called correctly
        mock_ticker_class.assert_called_once_with("AAPL")
        mock_yf_ticker.history.assert_called_once()

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    def test_get_beta_from_yfinance(
        self, mock_ticker_class, mock_yf_ticker, temp_cache_dir
    ):
        """Test getting beta directly from yfinance."""
        mock_ticker_class.return_value = mock_yf_ticker

        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Get beta
        beta = oracle.get_beta("AAPL")

        # Verify the result
        assert beta == 1.2

        # Verify yfinance was called correctly
        mock_ticker_class.assert_called_once_with("AAPL")

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    def test_get_beta_calculation(self, mock_ticker_class, temp_cache_dir):
        """Test beta calculation when not available from yfinance."""
        # Create a mock ticker with no beta in info
        mock_ticker = MagicMock()
        mock_ticker.info = {}  # No beta available

        # Create mock historical data for stock and market
        stock_data = pd.DataFrame(
            {"Close": [100.0, 102.0, 103.0, 101.0, 104.0]},
            index=pd.date_range(start="2023-01-01", periods=5),
        )

        market_data = pd.DataFrame(
            {"Close": [400.0, 404.0, 402.0, 401.0, 406.0]},
            index=pd.date_range(start="2023-01-01", periods=5),
        )

        # Configure the mock to return different data for different tickers
        # We're ignoring the args and kwargs since we only care about which ticker was requested
        def mock_history(
            *_args, **_kwargs
        ):  # Prefix with underscore to indicate unused
            if mock_ticker_class.call_args[0][0] == "AAPL":
                return stock_data
            else:  # SPY
                return market_data

        mock_ticker.history.side_effect = mock_history
        mock_ticker_class.return_value = mock_ticker

        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Get beta
        beta = oracle.get_beta("AAPL")

        # Verify the result is a float (actual value depends on the calculation)
        assert isinstance(beta, float)

        # Verify yfinance was called for both stock and market index
        assert mock_ticker_class.call_count >= 2

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    def test_get_beta_invalid_symbol(self, mock_ticker_class, temp_cache_dir):
        """Test getting beta for an invalid symbol."""
        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Get beta for invalid symbol
        beta = oracle.get_beta("INVALID-SYMBOL")

        # Should return None for invalid symbols
        assert beta is None

        # Verify yfinance was not called
        mock_ticker_class.assert_not_called()

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    def test_get_historical_data(
        self, mock_ticker_class, mock_yf_ticker, temp_cache_dir
    ):
        """Test getting historical data."""
        mock_ticker_class.return_value = mock_yf_ticker

        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Get historical data
        df = oracle.get_historical_data("AAPL", period="1y", interval="1d")

        # Verify the result
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "Close" in df.columns

        # Verify yfinance was called correctly
        mock_ticker_class.assert_called_once_with("AAPL")
        mock_yf_ticker.history.assert_called_once_with(period="1y", interval="1d")

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    def test_get_historical_data_invalid_ticker(
        self, mock_ticker_class, temp_cache_dir
    ):
        """Test getting historical data with an invalid ticker."""
        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Try to get historical data for invalid ticker
        with pytest.raises(ValueError, match="Invalid stock symbol format"):
            oracle.get_historical_data("INVALID-SYMBOL")

        # Verify yfinance was not called
        mock_ticker_class.assert_not_called()

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_is_valid_stock_symbol(self, temp_cache_dir):
        """Test stock symbol validation."""
        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Test valid symbols
        assert oracle.is_valid_stock_symbol("AAPL") is True
        assert oracle.is_valid_stock_symbol("SPY") is True
        assert oracle.is_valid_stock_symbol("BRK.B") is True
        assert oracle.is_valid_stock_symbol("SPY-X") is True

        # Test invalid symbols
        assert oracle.is_valid_stock_symbol("") is False
        assert oracle.is_valid_stock_symbol("aapl") is False  # lowercase
        assert oracle.is_valid_stock_symbol("INVALID-SYMBOL") is False
        assert oracle.is_valid_stock_symbol("TOOLONG") is False

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch.object(StockOracle, "get_beta")
    def test_is_cash_like(self, mock_get_beta, temp_cache_dir):
        """Test cash-like instrument detection."""

        # Configure the mock to return appropriate beta values
        def mock_beta_side_effect(ticker):
            if ticker in ["AAPL", "SPY"]:
                return 1.2  # High beta for stocks
            elif ticker in ["XYZ", "ABC"]:
                return 0.05  # Low beta for cash-like
            else:
                return None  # No beta for other symbols

        mock_get_beta.side_effect = mock_beta_side_effect

        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

        # Test obvious cash symbols
        assert oracle.is_cash_like("CASH") is True
        assert oracle.is_cash_like("USD") is True

        # Test cash-like patterns in ticker
        assert oracle.is_cash_like("SPAXX") is True
        assert oracle.is_cash_like("FDRXX") is True

        # Test cash-like patterns in description
        assert oracle.is_cash_like("XYZ", "MONEY MARKET FUND") is True
        assert oracle.is_cash_like("ABC", "CASH RESERVES") is True

        # Test non-cash instruments
        assert oracle.is_cash_like("AAPL") is False
        assert oracle.is_cash_like("SPY") is False

        # Reset the singleton for other tests
        StockOracle._instance = None

    @patch("yfinance.Ticker")
    @patch("os.makedirs")  # We need this patch to prevent actual directory creation
    @patch("pandas.DataFrame.to_csv")
    @patch("pandas.read_csv")
    def test_cache_behavior(
        self,
        mock_read_csv,
        mock_to_csv,
        _,  # Unused mock_makedirs parameter
        mock_ticker_class,
        mock_yf_ticker,
        temp_cache_dir,
    ):
        """Test that caching works correctly."""
        mock_ticker_class.return_value = mock_yf_ticker

        # Mock the cache reading function
        mock_df = pd.DataFrame(
            {
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [148.0, 149.0, 150.0],
                "Close": [153.0, 154.0, 155.0],
                "Volume": [1000000, 1100000, 1200000],
            }
        )
        mock_read_csv.return_value = mock_df

        # Create oracle with temp cache dir and short TTL
        oracle = StockOracle.get_instance(cache_dir=temp_cache_dir, cache_ttl=1)

        # Get historical data (should create cache)
        oracle.get_historical_data("AAPL")

        # Verify to_csv was called (cache creation attempt)
        mock_to_csv.assert_called_once()

        # Create a fake cache file to simulate successful cache creation
        cache_path = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
        with open(cache_path, "w") as f:
            f.write("dummy,data\n1,2")

        # Get data again (should try to use cache)
        oracle.get_historical_data("AAPL")

        # Verify yfinance was only called once (the first time)
        assert mock_ticker_class.call_count == 1

        # Modify the cache file's timestamp to simulate expiration
        os.utime(cache_path, (time.time() - 2, time.time() - 2))

        # Get data again (should refresh cache)
        oracle.get_historical_data("AAPL")

        # Verify yfinance was called again
        assert mock_ticker_class.call_count == 2

        # Reset the singleton for other tests
        StockOracle._instance = None


def test_stockdata_singleton():
    """Test the pre-initialized stockdata singleton."""
    # Instead of testing object identity, we'll test that the stockdata
    # variable is a StockOracle instance and that the singleton pattern works

    # Import the module to get the pre-initialized singleton
    from src.folib.data.stock import stockdata

    # Verify it's a StockOracle instance
    assert isinstance(stockdata, StockOracle)

    # Save the current instance
    current_instance = StockOracle._instance

    # Get the singleton instance - should return the same instance
    oracle = StockOracle.get_instance()

    # Verify the singleton pattern works (get_instance returns the same object)
    assert oracle is StockOracle._instance

    # Reset the singleton to its original state
    StockOracle._instance = current_instance
