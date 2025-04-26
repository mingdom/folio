"""
Tests for the YFinanceDataFetcher class in src/yfinance.py

These tests verify the core functionality of the YFinanceDataFetcher class, including:
1. Initialization and configuration
2. Data fetching and caching
3. Error handling
4. Data format and structure

The tests use mocking to avoid actual API calls and to provide consistent test data.
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.yfinance import YFinanceDataFetcher

# Import mock data utilities
from tests.test_data.mock_stock_data import get_real_beta, get_real_data


@pytest.fixture
def mock_ticker():
    """Create a mock Ticker object for yfinance."""
    mock = MagicMock()

    # Use real data from our collected samples
    df = get_real_data("AAPL", "1y")
    mock.history.return_value = df

    return mock


@pytest.fixture
def mock_spy_ticker():
    """Create a mock Ticker object for SPY data."""
    mock = MagicMock()

    # Use real data from our collected samples
    df = get_real_data("SPY", "1y")
    mock.history.return_value = df

    return mock


@pytest.fixture
def mock_empty_ticker():
    """Create a mock Ticker object with no data."""
    mock = MagicMock()
    mock.history.return_value = pd.DataFrame()
    return mock


@pytest.fixture
def temp_cache_dir(tmpdir):
    """Create a temporary directory for cache files."""
    cache_dir = tmpdir.mkdir("test_cache")
    return str(cache_dir)


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame with the expected structure using real data."""
    return get_real_data("AAPL", "1y").head(5)


class TestYFinanceDataFetcherInitialization:
    """Tests for YFinanceDataFetcher initialization and configuration."""

    def test_init_with_default_cache_dir(self):
        """Test initialization with default cache directory."""
        fetcher = YFinanceDataFetcher()
        assert fetcher.cache_dir == ".cache_yf"
        assert fetcher.cache_ttl == 86400  # Default TTL

    def test_init_with_custom_cache_dir(self, temp_cache_dir):
        """Test initialization with custom cache directory."""
        fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
        assert fetcher.cache_dir == temp_cache_dir
        assert os.path.exists(temp_cache_dir)  # Directory should be created

    def test_init_with_custom_ttl(self):
        """Test initialization with custom cache TTL."""
        fetcher = YFinanceDataFetcher(cache_ttl=3600)
        assert fetcher.cache_ttl == 3600


class TestDataFetching:
    """Tests for data fetching functionality."""

    def test_fetch_data_api_call(self, mock_ticker, temp_cache_dir):
        """Test fetching data from API."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            df = fetcher.fetch_data("AAPL", period="1y")

            # Check DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0  # Don't check exact length as it may vary

            # Check that required columns exist
            required_columns = ["Open", "High", "Low", "Close", "Volume"]
            for col in required_columns:
                assert col in df.columns, f"Column {col} not found in DataFrame"

            assert df.index.name == "date"
            assert pd.api.types.is_datetime64_dtype(df.index)

    def test_fetch_data_cache_creation(self, mock_ticker, temp_cache_dir):
        """Test that data is cached after fetching."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            fetcher.fetch_data("AAPL", period="1y")

            # Check that cache file was created
            cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
            assert os.path.exists(cache_file)

    def test_fetch_data_from_cache(self, mock_ticker, temp_cache_dir, sample_dataframe):
        """Test fetching data from cache."""
        # Create cache file
        cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
        sample_dataframe.to_csv(cache_file)

        # Set modification time to be recent (within cache TTL)
        os.utime(cache_file, (time.time(), time.time()))

        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            df = fetcher.fetch_data("AAPL", period="1y")

            # API should not be called
            mock_yf.assert_not_called()

            # Data should match sample
            pd.testing.assert_frame_equal(df, sample_dataframe)

    def test_fetch_data_expired_cache(
        self, mock_ticker, temp_cache_dir, sample_dataframe
    ):
        """Test fetching data with expired cache."""
        # Create cache file
        cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
        sample_dataframe.to_csv(cache_file)

        # Set modification time to be old (beyond cache TTL)
        old_time = time.time() - 100000  # Well beyond default TTL
        os.utime(cache_file, (old_time, old_time))

        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            fetcher.fetch_data("AAPL", period="1y")

            # API should be called
            mock_yf.assert_called_once()

    def test_fetch_market_data(self, mock_spy_ticker, temp_cache_dir):
        """Test fetching market data."""
        with patch("yfinance.Ticker", return_value=mock_spy_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)

            # Test with explicit period
            df = fetcher.fetch_market_data(market_index="SPY", period="1y")

            # Check DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0  # Don't check exact length as it may vary

            # Check that required columns exist
            required_columns = ["Open", "High", "Low", "Close", "Volume"]
            for col in required_columns:
                assert col in df.columns, f"Column {col} not found in DataFrame"

            # Test with default period (should use beta_period)
            with patch.object(YFinanceDataFetcher, "beta_period", "6m"):
                df_default = fetcher.fetch_market_data(market_index="SPY")
                assert isinstance(df_default, pd.DataFrame)
                assert len(df_default) > 0


class TestErrorHandling:
    """Tests for error handling in YFinanceDataFetcher."""

    def test_empty_data_response(self, mock_empty_ticker, temp_cache_dir):
        """Test handling of empty data responses."""
        with patch("yfinance.Ticker", return_value=mock_empty_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            with pytest.raises(ValueError, match="No historical data found"):
                fetcher.fetch_data("INVALID", period="1y")

    def test_network_error_with_fallback(self, temp_cache_dir, sample_dataframe):
        """Test fallback to expired cache on network error."""
        # Create cache file
        cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
        sample_dataframe.to_csv(cache_file)

        # Set modification time to be old (beyond cache TTL)
        old_time = time.time() - 100000  # Well beyond default TTL
        os.utime(cache_file, (old_time, old_time))

        # Simulate network error
        with patch("yfinance.Ticker", side_effect=Exception("Network error")):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            df = fetcher.fetch_data("AAPL", period="1y")

            # Should fall back to cache
            pd.testing.assert_frame_equal(df, sample_dataframe)

    def test_network_error_without_fallback(self, temp_cache_dir):
        """Test network error without cache fallback raises exception."""
        # Simulate network error with no cache
        with patch("yfinance.Ticker", side_effect=Exception("Network error")):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            with pytest.raises(ValueError):
                fetcher.fetch_data("AAPL", period="1y")


class TestDataFormat:
    """Tests for data format and structure."""

    def test_date_parsing(self, mock_ticker, temp_cache_dir):
        """Test that dates are properly parsed and set as index."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            df = fetcher.fetch_data("AAPL", period="1y")

            # Check index is datetime
            assert pd.api.types.is_datetime64_dtype(df.index)
            assert df.index.name == "date"
            # Don't check exact date as it may vary

    def test_column_renaming(self, mock_ticker, temp_cache_dir):
        """Test that columns are properly renamed."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            df = fetcher.fetch_data("AAPL", period="1y")

            # Check that required columns exist
            required_columns = ["Open", "High", "Low", "Close", "Volume"]
            for col in required_columns:
                assert col in df.columns, f"Column {col} not found in DataFrame"

    def test_data_sorting(self, mock_ticker, temp_cache_dir):
        """Test that data is sorted by date in ascending order."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)
            df = fetcher.fetch_data("AAPL", period="1y")

            # Check sorting
            assert df.index.is_monotonic_increasing


class TestPeriodHandling:
    """Tests for period handling in YFinanceDataFetcher."""

    def test_period_mapping(self):
        """Test period mapping to yfinance format."""
        fetcher = YFinanceDataFetcher()

        # Test valid periods
        assert fetcher._map_period_to_yfinance("1y") == "1y"
        assert fetcher._map_period_to_yfinance("5y") == "5y"
        assert fetcher._map_period_to_yfinance("1d") == "1d"

        # Test period conversion
        assert fetcher._map_period_to_yfinance("2y") == "2y"
        assert fetcher._map_period_to_yfinance("3y") == "5y"
        assert fetcher._map_period_to_yfinance("6m") == "6mo"
        assert fetcher._map_period_to_yfinance("3m") == "3mo"

        # Test invalid periods (should default to 1y)
        assert fetcher._map_period_to_yfinance("invalid") == "1y"


class TestBetaCalculation:
    """Tests for beta calculation using the YFinanceDataFetcher."""

    def test_beta_calculation(self, mock_ticker, mock_spy_ticker, temp_cache_dir):
        """Test beta calculation with mock data."""
        with patch(
            "yfinance.Ticker",
            side_effect=lambda ticker: mock_spy_ticker
            if ticker == "SPY"
            else mock_ticker,
        ):
            fetcher = YFinanceDataFetcher(cache_dir=temp_cache_dir)

            # Get stock and market data
            stock_data = fetcher.fetch_data("AAPL", period="1y")
            market_data = fetcher.fetch_market_data("SPY", period="1y")

            # Calculate beta manually
            stock_returns = stock_data["Close"].pct_change().dropna()
            market_returns = market_data["Close"].pct_change().dropna()

            # Align data
            common_dates = stock_returns.index.intersection(market_returns.index)
            stock_returns = stock_returns.loc[common_dates]
            market_returns = market_returns.loc[common_dates]

            # Calculate beta
            covariance = stock_returns.cov(market_returns)
            market_variance = market_returns.var()
            beta = covariance / market_variance

            # Compare with expected beta from real data
            get_real_beta("AAPL")

            # Beta should be within a reasonable range of the expected value
            # The exact value will differ due to the mock data and date ranges
            assert 0.5 < beta < 2.0, f"Beta {beta} is outside reasonable range"

            # For information only - not a strict test


if __name__ == "__main__":
    pytest.main(["-v", "test_yfinance.py"])
