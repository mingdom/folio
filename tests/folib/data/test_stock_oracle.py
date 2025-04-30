"""
Unit tests for the StockOracle class in src/folib/data/stock.py.

These tests focus only on:
1. Provider selection logic
2. The ability to switch between providers
3. Basic interface validation

No actual provider functionality is tested to avoid API calls.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

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
            "is_valid_stock_symbol",
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
