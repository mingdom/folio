"""
Unit tests for the enhanced StockData and StockDataService classes with filesystem caching.

These tests focus on:
1. StockData object creation and properties
2. StockDataService in-memory caching behavior
3. StockDataService filesystem caching behavior
4. Data loading and refreshing
5. Error handling

The tests use mocking to avoid actual API calls to external services.
"""

import datetime
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.folib.data.stock_data import StockData, StockDataService


class TestStockData:
    """Tests for the StockData class."""

    def test_init(self):
        """Test StockData initialization."""
        stock_data = StockData("AAPL")

        assert stock_data.ticker == "AAPL"
        assert stock_data.price is None
        assert stock_data.beta is None
        assert stock_data.volatility is None
        assert stock_data.last_updated is None

    def test_repr(self):
        """Test StockData string representation."""
        stock_data = StockData("AAPL")
        stock_data.price = 150.0
        stock_data.beta = 1.2
        stock_data.volatility = 0.25
        stock_data.last_updated = datetime.datetime(2023, 1, 1, 12, 0, 0)

        repr_str = repr(stock_data)

        assert "AAPL" in repr_str
        assert "150.0" in repr_str
        assert "1.2" in repr_str
        assert "0.25" in repr_str
        assert "2023-01-01" in repr_str


class TestStockDataService:
    """Tests for the StockDataService class."""

    @pytest.fixture
    def mock_oracle(self):
        """Create a mock StockOracle."""
        mock = MagicMock()
        mock.get_price.return_value = 150.0
        mock.get_beta.return_value = 1.2
        mock.get_volatility.return_value = 0.25
        mock.is_cash_like.return_value = False
        mock.is_valid_stock_symbol.return_value = True
        return mock

    @pytest.fixture
    def service(self, mock_oracle):
        """Create a StockDataService with a mock oracle."""
        # Patch the _load_cache_from_disk method to do nothing
        with patch.object(StockDataService, "_load_cache_from_disk"):
            service = StockDataService(oracle=mock_oracle)
            return service

    def test_get_stock_data_new(self, service):
        """Test getting a new StockData object."""
        stock_data = service.get_stock_data("AAPL")

        assert stock_data.ticker == "AAPL"
        assert stock_data.price is None  # Data not loaded yet
        assert stock_data.beta is None
        assert stock_data.volatility is None

    def test_get_stock_data_existing(self, service):
        """Test getting an existing StockData object from cache."""
        # First call creates the object
        stock_data1 = service.get_stock_data("AAPL")

        # Second call should return the same object
        stock_data2 = service.get_stock_data("AAPL")

        assert stock_data1 is stock_data2  # Same object (identity check)

    def test_get_stock_data_case_insensitive(self, service):
        """Test that ticker symbols are case-insensitive."""
        # Get with lowercase
        stock_data1 = service.get_stock_data("aapl")

        # Get with uppercase
        stock_data2 = service.get_stock_data("AAPL")

        assert stock_data1 is stock_data2  # Same object (identity check)

    def test_load_market_data_new(self, service, mock_oracle):
        """Test loading market data for a new ticker."""
        # Patch the _save_to_disk method to do nothing
        with patch.object(service, "_save_to_disk"):
            stock_data = service.load_market_data("AAPL")

        # Check that data was loaded
        assert stock_data.price == 150.0
        assert stock_data.beta == 1.2
        assert stock_data.volatility == 0.25
        assert stock_data.last_updated is not None

        # Check that oracle methods were called
        mock_oracle.get_price.assert_called_once_with("AAPL")
        mock_oracle.get_beta.assert_called_once_with("AAPL")
        mock_oracle.get_volatility.assert_called_once_with("AAPL")

    def test_load_market_data_cached(self, service, mock_oracle):
        """Test that cached data is used when available."""
        # First load to populate cache
        with patch.object(service, "_save_to_disk"):
            service.load_market_data("AAPL")

        # Reset mock to check if methods are called again
        mock_oracle.reset_mock()

        # Second load should use cache
        stock_data = service.load_market_data("AAPL")

        # Check that data is still available
        assert stock_data.price == 150.0
        assert stock_data.beta == 1.2
        assert stock_data.volatility == 0.25

        # Check that oracle methods were NOT called again
        mock_oracle.get_price.assert_not_called()
        mock_oracle.get_beta.assert_not_called()
        mock_oracle.get_volatility.assert_not_called()

    def test_load_market_data_force_refresh(self, service, mock_oracle):
        """Test forcing a refresh of market data."""
        # First load to populate cache
        with patch.object(service, "_save_to_disk"):
            service.load_market_data("AAPL")

        # Change mock return values
        mock_oracle.get_price.return_value = 160.0
        mock_oracle.get_beta.return_value = 1.3
        mock_oracle.get_volatility.return_value = 0.3

        # Reset mock to check if methods are called again
        mock_oracle.reset_mock()

        # Force refresh
        with patch.object(service, "_save_to_disk"):
            stock_data = service.load_market_data("AAPL", force_refresh=True)

        # Check that new data was loaded
        assert stock_data.price == 160.0
        assert stock_data.beta == 1.3
        assert stock_data.volatility == 0.3

        # Check that oracle methods were called again
        mock_oracle.get_price.assert_called_once_with("AAPL")
        mock_oracle.get_beta.assert_called_once_with("AAPL")
        mock_oracle.get_volatility.assert_called_once_with("AAPL")

    def test_is_data_stale(self, service):
        """Test the _is_data_stale method."""
        stock_data = StockData("AAPL")

        # No last_updated timestamp should be stale
        assert service._is_data_stale(stock_data) is True

        # Recent timestamp should not be stale
        stock_data.last_updated = datetime.datetime.now()
        assert service._is_data_stale(stock_data) is False

        # Old timestamp should be stale
        old_time = datetime.datetime.now() - datetime.timedelta(hours=2)
        stock_data.last_updated = old_time
        assert service._is_data_stale(stock_data) is True

    def test_load_market_data_stale(self, service, mock_oracle):
        """Test that stale data is refreshed."""
        # First load to populate cache
        with patch.object(service, "_save_to_disk"):
            stock_data = service.load_market_data("AAPL")

        # Make the data stale
        old_time = datetime.datetime.now() - datetime.timedelta(hours=2)
        stock_data.last_updated = old_time

        # Change mock return values
        mock_oracle.get_price.return_value = 160.0
        mock_oracle.get_beta.return_value = 1.3
        mock_oracle.get_volatility.return_value = 0.3

        # Reset mock to check if methods are called again
        mock_oracle.reset_mock()

        # Load again, should refresh due to staleness
        with patch.object(service, "_save_to_disk"):
            stock_data = service.load_market_data("AAPL")

        # Check that new data was loaded
        assert stock_data.price == 160.0
        assert stock_data.beta == 1.3
        assert stock_data.volatility == 0.3

        # Check that oracle methods were called again
        mock_oracle.get_price.assert_called_once_with("AAPL")
        mock_oracle.get_beta.assert_called_once_with("AAPL")
        mock_oracle.get_volatility.assert_called_once_with("AAPL")

    def test_load_market_data_error(self, service, mock_oracle):
        """Test error handling when loading market data."""
        # Make the oracle raise an exception
        mock_oracle.get_price.side_effect = ValueError("Invalid ticker")

        # Check that the exception is propagated
        with pytest.raises(ValueError, match="Invalid ticker"):
            with patch.object(service, "_save_to_disk"):
                service.load_market_data("INVALID")

    def test_is_cash_like(self, service, mock_oracle):
        """Test the is_cash_like method."""
        service.is_cash_like("SPAXX", "MONEY MARKET")

        # Check that the oracle method was called
        mock_oracle.is_cash_like.assert_called_once_with("SPAXX", "MONEY MARKET")

    def test_is_valid_stock_symbol(self, service, mock_oracle):
        """Test the is_valid_stock_symbol method."""
        service.is_valid_stock_symbol("AAPL")

        # Check that the oracle method was called
        mock_oracle.is_valid_stock_symbol.assert_called_once_with("AAPL")

    def test_clear_cache(self, service):
        """Test clearing the cache."""
        # Populate cache
        service.get_stock_data("AAPL")
        service.get_stock_data("MSFT")

        # Clear cache
        service.clear_cache()

        # Check that cache is empty
        assert len(service._cache) == 0

    def test_remove_from_cache(self, service):
        """Test removing a specific ticker from the cache."""
        # Populate cache
        service.get_stock_data("AAPL")
        service.get_stock_data("MSFT")

        # Remove one ticker
        service.remove_from_cache("AAPL")

        # Check that only the specified ticker was removed
        assert "AAPL" not in service._cache
        assert "MSFT" in service._cache

    def test_remove_from_cache_case_insensitive(self, service):
        """Test that removing from cache is case-insensitive."""
        # Populate cache with uppercase
        service.get_stock_data("AAPL")

        # Remove with lowercase
        service.remove_from_cache("aapl")

        # Check that the ticker was removed
        assert "AAPL" not in service._cache

    def test_get_cache_dir(self, service):
        """Test the _get_cache_dir method."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            cache_dir = service._get_cache_dir()

            # Check that the directory is correct
            assert cache_dir.name == ".cache_stock_data"

            # Check that mkdir was called with exist_ok=True
            mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_get_cache_file_path(self, service):
        """Test the _get_cache_file_path method."""
        with patch.object(service, "_get_cache_dir") as mock_get_cache_dir:
            mock_get_cache_dir.return_value = Path("/tmp/.cache_stock_data")

            # Get cache file path
            cache_file = service._get_cache_file_path("aapl")

            # Check that the path is correct
            assert cache_file == Path("/tmp/.cache_stock_data/AAPL.json")
            assert cache_file.name == "AAPL.json"

    def test_save_to_disk(self, service):
        """Test the _save_to_disk method."""
        # Create a StockData object
        stock_data = StockData("AAPL")
        stock_data.price = 150.0
        stock_data.beta = 1.2
        stock_data.volatility = 0.25
        stock_data.last_updated = datetime.datetime(2023, 1, 1, 12, 0, 0)

        # Mock the file operations

        with patch("json.dump") as mock_json_dump:
            with patch("builtins.open", mock_open()) as mock_file:
                with patch.object(service, "_get_cache_file_path") as mock_get_path:
                    mock_get_path.return_value = Path(
                        "/tmp/.cache_stock_data/AAPL.json"
                    )

                    # Save to disk
                    service._save_to_disk(stock_data)

                    # Check that the file was opened for writing
                    mock_file.assert_called_once_with(
                        Path("/tmp/.cache_stock_data/AAPL.json"), "w"
                    )

                    # Check that json.dump was called with the correct data
                    mock_json_dump.assert_called_once()
                    args, _kwargs = mock_json_dump.call_args

                    # First argument should be the data dictionary
                    actual_data = args[0]
                    assert actual_data["ticker"] == "AAPL"
                    assert actual_data["last_updated"] == "2023-01-01T12:00:00"
                    assert actual_data["data"]["price"] == 150.0
                    assert actual_data["data"]["beta"] == 1.2
                    assert actual_data["data"]["volatility"] == 0.25

                    # Second argument should be the file handle
                    assert args[1] == mock_file()

    def test_load_from_disk(self, service):
        """Test the _load_from_disk method."""
        # Mock the file operations
        mock_data = {
            "ticker": "AAPL",
            "last_updated": "2023-01-01T12:00:00",
            "data": {"price": 150.0, "beta": 1.2, "volatility": 0.25},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            with patch.object(service, "_get_cache_file_path") as mock_get_path:
                with patch("pathlib.Path.exists", return_value=True):
                    mock_get_path.return_value = Path(
                        "/tmp/.cache_stock_data/AAPL.json"
                    )

                    # Load from disk
                    stock_data = service._load_from_disk("AAPL")

                    # Check that the data was loaded correctly
                    assert stock_data.ticker == "AAPL"
                    assert stock_data.price == 150.0
                    assert stock_data.beta == 1.2
                    assert stock_data.volatility == 0.25
                    assert stock_data.last_updated == datetime.datetime(
                        2023, 1, 1, 12, 0, 0
                    )

    def test_load_from_disk_file_not_found(self, service):
        """Test the _load_from_disk method when the file doesn't exist."""
        with patch.object(service, "_get_cache_file_path") as mock_get_path:
            with patch("pathlib.Path.exists", return_value=False):
                mock_get_path.return_value = Path("/tmp/.cache_stock_data/AAPL.json")

                # Load from disk
                stock_data = service._load_from_disk("AAPL")

                # Check that None was returned
                assert stock_data is None

    def test_load_from_disk_error(self, service):
        """Test the _load_from_disk method when there's an error."""
        with patch.object(service, "_get_cache_file_path") as mock_get_path:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", side_effect=Exception("File error")):
                    mock_get_path.return_value = Path(
                        "/tmp/.cache_stock_data/AAPL.json"
                    )

                    # Load from disk
                    stock_data = service._load_from_disk("AAPL")

                    # Check that None was returned
                    assert stock_data is None

    def test_load_cache_from_disk(self, service):
        """Test the _load_cache_from_disk method."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock cache files
            temp_path = Path(temp_dir)
            (temp_path / "AAPL.json").write_text(
                json.dumps({
                    "ticker": "AAPL",
                    "last_updated": "2023-01-01T12:00:00",
                    "data": {"price": 150.0, "beta": 1.2, "volatility": 0.25},
                })
            )
            (temp_path / "MSFT.json").write_text(
                json.dumps({
                    "ticker": "MSFT",
                    "last_updated": "2023-01-01T12:00:00",
                    "data": {"price": 250.0, "beta": 1.1, "volatility": 0.2},
                })
            )

            # Mock the cache directory
            with patch.object(service, "_get_cache_dir", return_value=temp_path):
                # Load cache from disk
                service._load_cache_from_disk()

                # Check that the cache was populated
                assert len(service._cache) == 2
                assert "AAPL" in service._cache
                assert "MSFT" in service._cache
                assert service._cache["AAPL"].price == 150.0
                assert service._cache["MSFT"].price == 250.0

    def test_save_cache_to_disk(self, service):
        """Test the save_cache_to_disk method."""
        # Populate cache
        aapl_data = StockData("AAPL")
        aapl_data.price = 150.0
        aapl_data.beta = 1.2
        aapl_data.volatility = 0.25
        aapl_data.last_updated = datetime.datetime.now()

        msft_data = StockData("MSFT")
        msft_data.price = 250.0
        msft_data.beta = 1.1
        msft_data.volatility = 0.2
        msft_data.last_updated = datetime.datetime.now()

        service._cache = {"AAPL": aapl_data, "MSFT": msft_data}

        # Mock the _save_to_disk method
        with patch.object(service, "_save_to_disk") as mock_save:
            # Save cache to disk
            service.save_cache_to_disk()

            # Check that _save_to_disk was called for each ticker
            assert mock_save.call_count == 2
            mock_save.assert_any_call(aapl_data)
            mock_save.assert_any_call(msft_data)

    def test_clear_disk_cache(self, service):
        """Test the clear_disk_cache method."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock cache files
            temp_path = Path(temp_dir)
            (temp_path / "AAPL.json").touch()
            (temp_path / "MSFT.json").touch()

            # Mock the cache directory
            with patch.object(service, "_get_cache_dir", return_value=temp_path):
                # Clear disk cache
                service.clear_disk_cache()

                # Check that the files were deleted
                assert not (temp_path / "AAPL.json").exists()
                assert not (temp_path / "MSFT.json").exists()

    def test_remove_from_disk_cache(self, service):
        """Test the remove_from_disk_cache method."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock cache files
            temp_path = Path(temp_dir)
            (temp_path / "AAPL.json").touch()
            (temp_path / "MSFT.json").touch()

            # Mock the cache directory and file path
            with patch.object(service, "_get_cache_file_path") as mock_get_path:
                mock_get_path.return_value = temp_path / "AAPL.json"

                # Remove from disk cache
                service.remove_from_disk_cache("AAPL")

                # Check that only the specified file was deleted
                assert not (temp_path / "AAPL.json").exists()
                assert (temp_path / "MSFT.json").exists()

    def test_load_market_data_from_disk_cache(self, service, mock_oracle):
        """Test loading market data from disk cache."""
        # Mock the _load_from_disk method
        mock_disk_data = StockData("AAPL")
        mock_disk_data.price = 150.0
        mock_disk_data.beta = 1.2
        mock_disk_data.volatility = 0.25
        mock_disk_data.last_updated = datetime.datetime.now()

        with patch.object(service, "_load_from_disk", return_value=mock_disk_data):
            with patch.object(service, "_save_to_disk"):  # Prevent actual saving
                # Load market data
                stock_data = service.load_market_data("AAPL")

                # Check that data was loaded from disk
                assert stock_data.price == 150.0
                assert stock_data.beta == 1.2
                assert stock_data.volatility == 0.25

                # Check that oracle methods were NOT called
                mock_oracle.get_price.assert_not_called()
                mock_oracle.get_beta.assert_not_called()
                mock_oracle.get_volatility.assert_not_called()

    def test_load_market_data_disk_cache_stale(self, service, mock_oracle):
        """Test loading market data when disk cache is stale."""
        # Mock the _load_from_disk method with stale data
        mock_disk_data = StockData("AAPL")
        mock_disk_data.price = 150.0
        mock_disk_data.beta = 1.2
        mock_disk_data.volatility = 0.25
        mock_disk_data.last_updated = datetime.datetime.now() - datetime.timedelta(
            hours=2
        )

        with patch.object(service, "_load_from_disk", return_value=mock_disk_data):
            with patch.object(service, "_save_to_disk"):  # Prevent actual saving
                # Load market data
                stock_data = service.load_market_data("AAPL")

                # Check that fresh data was fetched
                assert stock_data.price == 150.0  # From mock_oracle

                # Check that oracle methods WERE called
                mock_oracle.get_price.assert_called_once_with("AAPL")
                mock_oracle.get_beta.assert_called_once_with("AAPL")
                mock_oracle.get_volatility.assert_called_once_with("AAPL")
