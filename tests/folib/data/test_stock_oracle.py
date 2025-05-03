"""
Unit tests for the StockOracle class and provider implementations in src/folib/data/stock.py.

These tests focus on:
1. Provider selection logic
2. The ability to switch between providers
3. Basic interface validation
4. Provider functionality with mocked API responses

The tests use mocking to avoid actual API calls to external services.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.folib.data.provider_fmp import FMPProvider
from src.folib.data.provider_yfinance import YFinanceProvider
from src.folib.data.stock import StockOracle


class TestStockOracleProviders:
    """Test the provider selection functionality of StockOracle."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_provider_selection_yfinance(self, temp_cache_dir):
        """Test that YFinance provider is selected when explicitly specified."""
        # Patch the environment variables to ensure they don't affect the test
        with patch.dict(os.environ, {"DATA_SOURCE": "", "FMP_API_KEY": ""}, clear=True):
            # Reset the singleton first
            StockOracle._instance = None

            # Create oracle with temp cache dir and explicit provider
            oracle = StockOracle.get_instance(
                provider_name="yfinance", cache_dir=temp_cache_dir
            )

            # Verify the provider
            assert oracle.provider_name == "yfinance"
            assert oracle.provider.__class__.__name__ == "YFinanceProvider"

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_provider_selection_fmp(self, temp_cache_dir):
        """Test that FMP provider is selected when specified."""
        # Reset the singleton first
        StockOracle._instance = None

        # Create oracle with temp cache dir
        oracle = StockOracle.get_instance(
            provider_name="fmp", fmp_api_key="test_key", cache_dir=temp_cache_dir
        )

        # Verify the provider
        assert oracle.provider_name == "fmp"
        assert oracle.provider.__class__.__name__ == "FMPProvider"

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_provider_selection_from_env(self, temp_cache_dir):
        """Test that provider is selected from environment variables."""
        # Reset the singleton first
        StockOracle._instance = None

        # Patch the environment variables
        with patch.dict(
            os.environ, {"DATA_SOURCE": "fmp", "FMP_API_KEY": "test_key"}, clear=True
        ):
            # Create oracle with temp cache dir
            oracle = StockOracle.get_instance(cache_dir=temp_cache_dir)

            # Verify the provider
            assert oracle.provider_name == "fmp"
            assert oracle.provider.__class__.__name__ == "FMPProvider"

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_provider_selection_invalid(self, temp_cache_dir):
        """Test that invalid provider selection raises ValueError."""
        # Try to create oracle with invalid provider
        with pytest.raises(ValueError, match="Unknown provider"):
            StockOracle.get_instance(provider_name="invalid", cache_dir=temp_cache_dir)

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_fmp_provider_without_api_key(self, temp_cache_dir):
        """Test that FMP provider without API key raises ValueError."""
        # Reset the singleton first
        StockOracle._instance = None

        # Patch the environment variables to ensure they don't affect the test
        with patch.dict(os.environ, {"DATA_SOURCE": "", "FMP_API_KEY": ""}, clear=True):
            # Try to create oracle with FMP provider but no API key
            with pytest.raises(
                ValueError, match="API key is required for FMP provider"
            ):
                StockOracle.get_instance(provider_name="fmp", cache_dir=temp_cache_dir)

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_provider_interface_consistency(self, temp_cache_dir):
        """Test that both providers implement the same interface methods."""
        # Reset the singleton first
        StockOracle._instance = None

        # Create YFinance oracle
        yf_oracle = StockOracle.get_instance(
            provider_name="yfinance", cache_dir=temp_cache_dir
        )

        # Reset the singleton
        StockOracle._instance = None

        # Create FMP oracle
        fmp_oracle = StockOracle.get_instance(
            provider_name="fmp", fmp_api_key="test_key", cache_dir=temp_cache_dir
        )

        # Get the provider instances
        yf_provider = yf_oracle.provider
        fmp_provider = fmp_oracle.provider

        # Check that both providers have the same interface methods
        yf_methods = [
            method for method in dir(yf_provider) if not method.startswith("_")
        ]
        fmp_methods = [
            method for method in dir(fmp_provider) if not method.startswith("_")
        ]

        # Check required methods exist in both providers
        required_methods = [
            "get_historical_data",
            "try_get_beta_from_provider",
        ]
        for method in required_methods:
            assert method in yf_methods, f"YFinance provider missing {method} method"
            assert method in fmp_methods, f"FMP provider missing {method} method"

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_switching_providers(self, temp_cache_dir):
        """Test that we can switch between providers."""
        # Reset the singleton first
        StockOracle._instance = None

        # Create YFinance oracle
        yf_oracle = StockOracle.get_instance(
            provider_name="yfinance", cache_dir=temp_cache_dir
        )
        assert yf_oracle.provider_name == "yfinance"

        # Reset the singleton
        StockOracle._instance = None

        # Create FMP oracle
        fmp_oracle = StockOracle.get_instance(
            provider_name="fmp", fmp_api_key="test_key", cache_dir=temp_cache_dir
        )
        assert fmp_oracle.provider_name == "fmp"

        # Reset the singleton for other tests
        StockOracle._instance = None

    def test_folio_respects_data_source(self, temp_cache_dir):
        """Test that both folib and folio respect the DATA_SOURCE environment variable.

        This test verifies that when we set the DATA_SOURCE environment variable to "fmp",
        both folib and folio modules use the FMP provider.

        Note: This test is related to a fix in src/folio/__init__.py that ensures
        environment variables are loaded early in the module initialization process.
        """
        # Save original modules to restore later
        original_modules = dict(sys.modules)

        try:
            # Remove relevant modules if they were previously imported
            for module in list(sys.modules.keys()):
                if module.startswith("src.folib") or module.startswith("src.folio"):
                    del sys.modules[module]

            # Reset the singleton
            StockOracle._instance = None

            # Set environment variables to use FMP provider
            with patch.dict(
                os.environ,
                {"DATA_SOURCE": "fmp", "FMP_API_KEY": "test_key"},
                clear=True,
            ):
                # Import folio first (which will trigger import of folib)
                # Now import folib directly to verify its state
                import src.folib.data.stock as folib_stock
                from src.folio.utils import get_beta

                # Verify both are using the FMP provider
                assert folib_stock.DATA_SOURCE == "fmp"
                assert folib_stock.stockdata.provider_name == "fmp"

                # Patch the get_beta method to avoid actual API calls
                with patch.object(
                    folib_stock.stockdata, "get_beta", return_value=1.5
                ) as mock_get_beta:
                    # Call get_beta from folio
                    beta = get_beta("AAPL")

                    # Verify the mock was called, indicating folio is using the same provider
                    mock_get_beta.assert_called_once_with("AAPL")
                    assert beta == 1.5

        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)

            # Reset the singleton for other tests
            StockOracle._instance = None


class TestYFinanceProvider:
    """Test the YFinanceProvider implementation."""

    @pytest.fixture
    def provider(self):
        """Create a YFinanceProvider instance with a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield YFinanceProvider(cache_dir=temp_dir)

    def test_get_historical_data_validates_ticker(self, provider):
        """Test that get_historical_data validates the ticker symbol."""
        # Test with an empty ticker
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            provider.get_historical_data("")

        # Test with an invalid ticker format
        with pytest.raises(ValueError, match="Invalid stock symbol format"):
            provider.get_historical_data("invalid-symbol-123")

        # Mock the yfinance.Ticker.history method to avoid actual API calls
        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker_class.return_value = mock_ticker

            # Set up the mock to return a DataFrame
            mock_df = pd.DataFrame({
                "Open": [100.0],
                "High": [101.0],
                "Low": [99.0],
                "Close": [100.5],
                "Volume": [1000000],
            })
            mock_ticker.history.return_value = mock_df

            # Test with a valid ticker
            result = provider.get_historical_data("AAPL")

            # Verify the result
            assert isinstance(result, pd.DataFrame)
            assert not result.empty

            # Verify that the ticker was created with the correct symbol
            mock_ticker_class.assert_called_once_with("AAPL")

            # Verify that history was called with the correct parameters
            mock_ticker.history.assert_called_once_with(period="1y", interval="1d")

    def test_try_get_beta_from_provider(self, provider):
        """Test that try_get_beta_from_provider works correctly."""
        # Mock the yfinance.Ticker.info property to avoid actual API calls
        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker_class.return_value = mock_ticker

            # Set up the mock to return beta
            mock_ticker.info = {"beta": 1.2}

            # Test with a valid ticker
            beta = provider.try_get_beta_from_provider("AAPL")

            # Verify the result
            assert beta == 1.2

            # Verify that the ticker was created with the correct symbol
            mock_ticker_class.assert_called_once_with("AAPL")


class TestFMPProvider:
    """Test the FMPProvider implementation."""

    @pytest.fixture
    def provider(self):
        """Create a FMPProvider instance with a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield FMPProvider(api_key="test_key", cache_dir=temp_dir)

    def test_get_historical_data_validates_ticker(self, provider):
        """Test that get_historical_data validates the ticker symbol."""
        # Test with an empty ticker
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            provider.get_historical_data("")

        # Test with an invalid ticker format
        with pytest.raises(ValueError, match="Invalid stock symbol format"):
            provider.get_historical_data("invalid-symbol-123")

        # Mock the fmpsdk.historical_price_full method to avoid actual API calls
        with patch("fmpsdk.historical_price_full") as mock_historical:
            # Set up the mock to return a list of dictionaries
            mock_historical.return_value = {
                "historical": [
                    {
                        "date": "2023-01-01",
                        "open": 100.0,
                        "high": 101.0,
                        "low": 99.0,
                        "close": 100.5,
                        "volume": 1000000,
                    }
                ]
            }

            # Test with a valid ticker
            result = provider.get_historical_data("AAPL")

            # Verify the result
            assert isinstance(result, pd.DataFrame)
            assert not result.empty

            # Verify that the API was called with the correct parameters
            mock_historical.assert_called_once()
            call_args = mock_historical.call_args[1]
            assert call_args["apikey"] == "test_key"
            assert call_args["symbol"] == "AAPL"

    def test_try_get_beta_from_provider(self, provider):
        """Test that try_get_beta_from_provider works correctly."""
        # Mock the fmpsdk.company_profile method to avoid actual API calls
        with patch("fmpsdk.company_profile") as mock_profile:
            # Set up the mock to return a list with a dictionary containing beta
            mock_profile.return_value = [{"beta": 1.2}]

            # Test with a valid ticker
            beta = provider.try_get_beta_from_provider("AAPL")

            # Verify the result
            assert beta == 1.2

            # Verify that the API was called with the correct parameters
            mock_profile.assert_called_once_with(apikey="test_key", symbol="AAPL")
