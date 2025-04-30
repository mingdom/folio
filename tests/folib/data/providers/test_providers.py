"""
Unit tests for market data providers.

These tests verify that the provider interface is correctly implemented
and that the StockOracle class can use different providers.
"""

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.folib.data.provider import MarketDataProvider
from src.folib.data.provider_fmp import FMPProvider
from src.folib.data.provider_yfinance import YFinanceProvider
from src.folib.data.stock import StockOracle


class TestProviders:
    """Test suite for market data providers."""

    def test_yfinance_provider_implements_interface(self):
        """Test that YFinanceProvider implements the MarketDataProvider interface."""
        provider = YFinanceProvider(cache_dir=".cache_test")
        assert isinstance(provider, MarketDataProvider)
        assert hasattr(provider, "get_price")
        assert hasattr(provider, "get_beta")
        assert hasattr(provider, "get_historical_data")
        assert hasattr(provider, "is_valid_stock_symbol")

    def test_fmp_provider_implements_interface(self):
        """Test that FMPProvider implements the MarketDataProvider interface."""
        provider = FMPProvider(api_key="test_key", cache_dir=".cache_test")
        assert isinstance(provider, MarketDataProvider)
        assert hasattr(provider, "get_price")
        assert hasattr(provider, "get_beta")
        assert hasattr(provider, "get_historical_data")
        assert hasattr(provider, "is_valid_stock_symbol")

    def test_stockoracle_with_yfinance_provider(self):
        """Test that StockOracle can use YFinanceProvider."""
        # Reset singleton instance
        StockOracle._instance = None

        # Create a mock YFinanceProvider
        mock_provider = MagicMock(spec=YFinanceProvider)
        mock_provider.get_price.return_value = 150.0
        mock_provider.get_beta.return_value = 1.2
        mock_provider.get_historical_data.return_value = pd.DataFrame(
            {
                "Open": [150.0, 151.0],
                "High": [152.0, 153.0],
                "Low": [149.0, 150.0],
                "Close": [151.0, 152.0],
                "Volume": [1000000, 1100000],
            }
        )
        mock_provider.is_valid_stock_symbol.return_value = True

        # Patch YFinanceProvider to return our mock
        with patch("src.folib.data.stock.YFinanceProvider", return_value=mock_provider):
            # Create StockOracle with YFinanceProvider
            oracle = StockOracle.get_instance(provider_name="yfinance")

            # Test that StockOracle uses the provider correctly
            assert oracle.get_price("AAPL") == 150.0
            assert oracle.get_beta("AAPL") == 1.2
            assert oracle.get_historical_data("AAPL").shape == (2, 5)
            assert oracle.is_valid_stock_symbol("AAPL") is True

            # Verify that provider methods were called with correct arguments
            mock_provider.get_price.assert_called_once_with("AAPL")
            mock_provider.get_beta.assert_called_once_with("AAPL")
            mock_provider.get_historical_data.assert_called_once_with(
                "AAPL", "1y", "1d"
            )
            mock_provider.is_valid_stock_symbol.assert_called_once_with("AAPL")

    def test_stockoracle_with_fmp_provider(self):
        """Test that StockOracle can use FMPProvider."""
        # Reset singleton instance
        StockOracle._instance = None

        # Create a mock FMPProvider
        mock_provider = MagicMock(spec=FMPProvider)
        mock_provider.get_price.return_value = 150.0
        mock_provider.get_beta.return_value = 1.2
        mock_provider.get_historical_data.return_value = pd.DataFrame(
            {
                "Open": [150.0, 151.0],
                "High": [152.0, 153.0],
                "Low": [149.0, 150.0],
                "Close": [151.0, 152.0],
                "Volume": [1000000, 1100000],
            }
        )
        mock_provider.is_valid_stock_symbol.return_value = True

        # Patch FMPProvider to return our mock
        with patch("src.folib.data.stock.FMPProvider", return_value=mock_provider):
            # Create StockOracle with FMPProvider
            oracle = StockOracle.get_instance(
                provider_name="fmp", fmp_api_key="test_key"
            )

            # Test that StockOracle uses the provider correctly
            assert oracle.get_price("AAPL") == 150.0
            assert oracle.get_beta("AAPL") == 1.2
            assert oracle.get_historical_data("AAPL").shape == (2, 5)
            assert oracle.is_valid_stock_symbol("AAPL") is True

            # Verify that provider methods were called with correct arguments
            mock_provider.get_price.assert_called_once_with("AAPL")
            mock_provider.get_beta.assert_called_once_with("AAPL")
            mock_provider.get_historical_data.assert_called_once_with(
                "AAPL", "1y", "1d"
            )
            mock_provider.is_valid_stock_symbol.assert_called_once_with("AAPL")

    def test_stockoracle_validates_fmp_api_key(self):
        """Test that StockOracle validates FMP API key."""
        # Reset singleton instance
        StockOracle._instance = None

        # Test that StockOracle raises ValueError when FMP provider is selected but no API key is provided
        # We need to clear the environment variables to ensure the test is not affected by them
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="API key is required for FMP provider"
            ):
                StockOracle.get_instance(provider_name="fmp", fmp_api_key=None)

    def test_stockoracle_validates_provider_name(self):
        """Test that StockOracle validates provider name."""
        # Reset singleton instance
        StockOracle._instance = None

        # Test that StockOracle raises ValueError when an unknown provider is selected
        with pytest.raises(ValueError, match="Unknown provider: invalid_provider"):
            StockOracle.get_instance(provider_name="invalid_provider")

    def test_stockoracle_with_environment_variables(self):
        """Test that StockOracle uses environment variables for configuration."""
        # This test directly tests the StockOracle class's behavior with environment variables
        # without relying on the module-level singleton initialization

        # Reset singleton instance
        StockOracle._instance = None

        # Test with DATA_SOURCE=yfinance (default)
        with patch.dict(os.environ, {"DATA_SOURCE": "yfinance"}):
            # Create a new instance
            oracle = StockOracle.get_instance()
            assert oracle.provider_name == "yfinance"
            assert isinstance(oracle.provider, YFinanceProvider)

        # Reset singleton instance
        StockOracle._instance = None

        # Test with DATA_SOURCE=fmp and FMP_API_KEY set
        with patch.dict(os.environ, {"DATA_SOURCE": "fmp", "FMP_API_KEY": "test_key"}):
            # Create a new instance
            oracle = StockOracle.get_instance()
            assert oracle.provider_name == "fmp"
            assert isinstance(oracle.provider, FMPProvider)

        # Reset singleton instance
        StockOracle._instance = None

        # Test with DATA_SOURCE=fmp but no FMP_API_KEY (should raise ValueError)
        with patch.dict(os.environ, {"DATA_SOURCE": "fmp"}, clear=True):
            # Should raise ValueError because FMP_API_KEY is required
            with pytest.raises(
                ValueError, match="API key is required for FMP provider"
            ):
                StockOracle.get_instance()
