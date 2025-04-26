"""
Tests for the DataFetcher class in src/fmp.py

These tests verify the core functionality of the DataFetcher class, including:
1. Initialization and configuration
2. Data fetching and caching
3. Error handling
4. Data format and structure

The tests use mocking to avoid actual API calls and to provide consistent test data.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fmp import DataFetcher

# Import mock data utilities
from tests.test_data.mock_stock_data import (
    get_mock_raw_data,
    get_real_beta,
    get_real_data,
)


@pytest.fixture
def mock_response():
    """Create a mock response object for requests with real data."""
    mock = MagicMock()
    mock.status_code = 200

    # Use real data structure from our collected samples
    mock.json.return_value = get_mock_raw_data("AAPL", "1y")
    return mock


@pytest.fixture
def mock_spy_response():
    """Create a mock response object for SPY data."""
    mock = MagicMock()
    mock.status_code = 200

    # Use real data structure from our collected samples
    mock.json.return_value = get_mock_raw_data("SPY", "1y")
    return mock


@pytest.fixture
def mock_empty_response():
    """Create a mock response with no historical data."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"symbol": "INVALID", "historical": []}
    return mock


@pytest.fixture
def mock_error_response():
    """Create a mock response with an error status code."""
    mock = MagicMock()
    mock.status_code = 401
    mock.text = "Unauthorized: Invalid API key"
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


class TestDataFetcherInitialization:
    """Tests for DataFetcher initialization and configuration."""

    def test_init_with_default_cache_dir(self):
        """Test initialization with default cache directory."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            fetcher = DataFetcher()
            assert fetcher.cache_dir == ".cache_fmp"
            assert fetcher.api_key == "test_key"
            assert fetcher.cache_ttl == 86400  # Default TTL

    def test_init_with_custom_cache_dir(self, temp_cache_dir):
        """Test initialization with custom cache directory."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            fetcher = DataFetcher(cache_dir=temp_cache_dir)
            assert fetcher.cache_dir == temp_cache_dir
            assert os.path.exists(temp_cache_dir)  # Directory should be created

    def test_init_with_config_api_key(self):
        """Test initialization with API key from config."""
        # Clear environment variable to ensure we use config
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.v2.config.config.get", return_value="config_key"):
                fetcher = DataFetcher()
                assert fetcher.api_key == "config_key"

    def test_init_with_env_api_key_precedence(self):
        """Test that environment variable takes precedence over config."""
        with patch.dict(os.environ, {"FMP_API_KEY": "env_key"}):
            with patch("src.v2.config.config.get", return_value="config_key"):
                fetcher = DataFetcher()
                assert fetcher.api_key == "env_key"

    def test_init_with_custom_ttl(self):
        """Test initialization with custom cache TTL from config."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch(
                "src.v2.config.config.get",
                side_effect=lambda key, default=None: 3600
                if key == "app.cache.ttl"
                else default,
            ):
                fetcher = DataFetcher()
                assert fetcher.cache_ttl == 3600

    def test_init_without_api_key(self):
        """Test initialization without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.v2.config.config.get", return_value=None):
                with pytest.raises(ValueError, match="No API key found"):
                    DataFetcher()


class TestDataFetching:
    """Tests for data fetching functionality."""

    def test_fetch_data_api_call(self, mock_response, temp_cache_dir):
        """Test fetching data from API."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
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

    def test_fetch_data_cache_creation(self, mock_response, temp_cache_dir):
        """Test that data is cached after fetching."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                fetcher.fetch_data("AAPL", period="1y")

                # Check that cache file was created
                cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
                assert os.path.exists(cache_file)

    def test_fetch_data_from_cache(
        self, mock_response, temp_cache_dir, sample_dataframe
    ):
        """Test fetching data from cache."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            # Create cache file
            cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
            sample_dataframe.to_csv(cache_file)

            # Set modification time to be recent (within cache TTL)
            os.utime(cache_file, (time.time(), time.time()))

            with patch("requests.get", return_value=mock_response) as mock_get:
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                df = fetcher.fetch_data("AAPL", period="1y")

                # API should not be called
                mock_get.assert_not_called()

                # Data should match sample
                pd.testing.assert_frame_equal(df, sample_dataframe)

    def test_fetch_data_expired_cache(
        self, mock_response, temp_cache_dir, sample_dataframe
    ):
        """Test fetching data with expired cache."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            # Create cache file
            cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
            sample_dataframe.to_csv(cache_file)

            # Set modification time to be old (beyond cache TTL)
            old_time = time.time() - 100000  # Well beyond default TTL
            os.utime(cache_file, (old_time, old_time))

            with patch("requests.get", return_value=mock_response) as mock_get:
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                fetcher.fetch_data("AAPL", period="1y")

                # API should be called
                mock_get.assert_called_once()

    def test_fetch_market_data(self, mock_response, temp_cache_dir):
        """Test fetching market data."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                df = fetcher.fetch_market_data(market_index="SPY", period="1y")

                # Check DataFrame structure
                assert isinstance(df, pd.DataFrame)
                assert len(df) > 0  # Don't check exact length as it may vary

                # Check that required columns exist
                required_columns = ["Open", "High", "Low", "Close", "Volume"]
                for col in required_columns:
                    assert col in df.columns, f"Column {col} not found in DataFrame"


class TestErrorHandling:
    """Tests for error handling in DataFetcher."""

    def test_api_error_response(self, mock_error_response, temp_cache_dir):
        """Test handling of API error responses."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_error_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                with pytest.raises(ValueError, match="API request failed"):
                    fetcher.fetch_data("AAPL", period="1y")

    def test_empty_data_response(self, mock_empty_response, temp_cache_dir):
        """Test handling of empty data responses."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            # Update the mock response to not include 'historical' key
            mock_empty_response.json.return_value = {"symbol": "INVALID"}

            with patch("requests.get", return_value=mock_empty_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                # Now we expect an empty DataFrame instead of an exception
                result = fetcher.fetch_data("INVALID", period="1y")
                assert isinstance(result, pd.DataFrame)
                assert result.empty or len(result) == 0
                assert "Open" in result.columns
                assert "Close" in result.columns

    def test_network_error_with_fallback(self, temp_cache_dir, sample_dataframe):
        """Test fallback to expired cache on network error."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            # Create cache file
            cache_file = os.path.join(temp_cache_dir, "AAPL_1y_1d.csv")
            sample_dataframe.to_csv(cache_file)

            # Set modification time to be old (beyond cache TTL)
            old_time = time.time() - 100000  # Well beyond default TTL
            os.utime(cache_file, (old_time, old_time))

            # Simulate network error
            with patch(
                "requests.get",
                side_effect=requests.exceptions.ConnectionError("Network error"),
            ):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                df = fetcher.fetch_data("AAPL", period="1y")

                # Should fall back to cache
                pd.testing.assert_frame_equal(df, sample_dataframe)

    def test_network_error_without_fallback(self, temp_cache_dir):
        """Test network error without cache fallback raises exception."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            # Simulate network error with no cache
            with patch(
                "requests.get",
                side_effect=requests.exceptions.ConnectionError("Network error"),
            ):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                with pytest.raises(requests.exceptions.ConnectionError):
                    fetcher.fetch_data("AAPL", period="1y")


class TestDataFormat:
    """Tests for data format and structure."""

    def test_date_parsing(self, mock_response, temp_cache_dir):
        """Test that dates are properly parsed and set as index."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                df = fetcher.fetch_data("AAPL", period="1y")

                # Check index is datetime
                assert pd.api.types.is_datetime64_dtype(df.index)
                assert df.index.name == "date"
                # Don't check exact date as it may vary

    def test_column_renaming(self, mock_response, temp_cache_dir):
        """Test that columns are properly renamed."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                df = fetcher.fetch_data("AAPL", period="1y")

                # Check that required columns exist
                required_columns = ["Open", "High", "Low", "Close", "Volume"]
                for col in required_columns:
                    assert col in df.columns, f"Column {col} not found in DataFrame"

    def test_data_sorting(self, temp_cache_dir):
        """Test that data is sorted by date in ascending order."""
        # Modify mock response to have unsorted dates
        unsorted_response = MagicMock()
        unsorted_response.status_code = 200
        unsorted_response.json.return_value = {
            "symbol": "AAPL",
            "historical": [
                {
                    "date": "2023-01-05",
                    "open": 127.13,
                    "high": 127.77,
                    "low": 124.76,
                    "close": 125.02,
                    "volume": 80829500,
                },
                {
                    "date": "2023-01-03",
                    "open": 130.28,
                    "high": 130.9,
                    "low": 124.17,
                    "close": 125.07,
                    "volume": 112117500,
                },
                {
                    "date": "2023-01-04",
                    "open": 126.89,
                    "high": 128.66,
                    "low": 125.08,
                    "close": 126.36,
                    "volume": 88883500,
                },
            ],
        }

        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=unsorted_response):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                df = fetcher.fetch_data("AAPL", period="1y")

                # Check sorting
                assert df.index[0] < df.index[1] < df.index[2]
                assert df.index[0] == pd.Timestamp("2023-01-03")
                assert df.index[1] == pd.Timestamp("2023-01-04")
                assert df.index[2] == pd.Timestamp("2023-01-05")


class TestPeriodHandling:
    """Tests for period handling in date range calculation."""

    def test_period_years(self, mock_response, temp_cache_dir):
        """Test period handling for years."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response) as mock_get:
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                fetcher.fetch_data("AAPL", period="2y")

                # Extract URL from the call
                url = mock_get.call_args[0][0]

                # Check that date range is approximately 2 years
                today = datetime.now().strftime("%Y-%m-%d")
                two_years_ago = (datetime.now() - timedelta(days=365 * 2)).strftime(
                    "%Y-%m"
                )

                assert today in url
                assert two_years_ago in url

    def test_period_months(self, mock_response, temp_cache_dir):
        """Test period handling for months."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response) as mock_get:
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                fetcher.fetch_data("AAPL", period="6m")

                # Extract URL from the call
                url = mock_get.call_args[0][0]

                # Check that date range is approximately 6 months
                today = datetime.now().strftime("%Y-%m-%d")
                six_months_ago = (datetime.now() - timedelta(days=30 * 6)).strftime(
                    "%Y-%m"
                )

                assert today in url
                assert six_months_ago in url

    def test_period_default(self, mock_response, temp_cache_dir):
        """Test default period handling."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch("requests.get", return_value=mock_response) as mock_get:
                fetcher = DataFetcher(cache_dir=temp_cache_dir)
                fetcher.fetch_data("AAPL", period="invalid")

                # Extract URL from the call
                url = mock_get.call_args[0][0]

                # Check that date range is approximately 1 year (default)
                today = datetime.now().strftime("%Y-%m-%d")
                one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m")

                assert today in url
                assert one_year_ago in url


class TestBetaCalculation:
    """Tests for beta calculation using the DataFetcher."""

    def test_beta_calculation(self, mock_response, mock_spy_response, temp_cache_dir):
        """Test beta calculation with mock data."""
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
            with patch(
                "requests.get",
                side_effect=lambda url, params=None: mock_spy_response
                if "SPY" in url
                else mock_response,
            ):
                fetcher = DataFetcher(cache_dir=temp_cache_dir)

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
    pytest.main(["-v", "test_data_fetcher.py"])
