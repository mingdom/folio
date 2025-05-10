"""
Unit tests for the MarketDataProvider class in src/folib/data/market_data.py.

These tests focus on the functionality of the MarketDataProvider class,
with external API calls mocked to prevent network requests.
"""

import os
from unittest.mock import patch

import pytest

from src.folib.data.market_data import MarketDataProvider


class TestMarketDataProvider:
    """Test the MarketDataProvider class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a provider instance with a mock API key
        self.provider = MarketDataProvider(api_key="test_key")

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        provider = MarketDataProvider(api_key="explicit_key")
        assert provider.api_key == "explicit_key"

    def test_initialization_with_env_var(self):
        """Test initialization with API key from environment variable."""
        with patch.dict(os.environ, {"FMP_API_KEY": "env_key"}):
            provider = MarketDataProvider()
            assert provider.api_key == "env_key"

    def test_initialization_without_api_key(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict(os.environ, clear=True):
            with pytest.raises(ValueError, match="FMP_API_KEY is required"):
                MarketDataProvider()

    def test_fetch_profile_success(self):
        """Test successful profile fetching."""
        # Mock response data
        mock_profile = {
            "symbol": "AAPL",
            "price": 150.0,
            "beta": 1.2,
            "name": "Apple Inc.",
        }

        # Mock the fmpsdk.company_profile function
        with patch("fmpsdk.company_profile", return_value=[mock_profile]):
            profile = self.provider._fetch_profile("AAPL")

            # Verify the profile was fetched correctly
            assert profile == mock_profile

    def test_fetch_profile_empty_response(self):
        """Test profile fetching with empty response."""
        # Mock empty response
        with patch("fmpsdk.company_profile", return_value=[]):
            profile = self.provider._fetch_profile("UNKNOWN")

            # Verify the result is None
            assert profile is None

    def test_fetch_profile_api_error(self):
        """Test profile fetching with API error."""
        # Mock API error
        with patch("fmpsdk.company_profile", side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                self.provider._fetch_profile("AAPL")

    def test_get_price_success(self):
        """Test successful price fetching."""
        # Mock response data
        mock_profile = {
            "symbol": "AAPL",
            "price": 150.0,
            "beta": 1.2,
        }

        # Mock the fmpsdk.company_profile function
        with patch("fmpsdk.company_profile", return_value=[mock_profile]):
            price = self.provider.get_price("AAPL")

            # Verify the price was fetched correctly
            assert price == 150.0

    def test_get_price_invalid_value(self):
        """Test price fetching with invalid value."""
        # Mock response with invalid price
        mock_profile = {
            "symbol": "AAPL",
            "price": "invalid",
            "beta": 1.2,
        }

        # Mock the fmpsdk.company_profile function
        with patch("fmpsdk.company_profile", return_value=[mock_profile]):
            price = self.provider.get_price("AAPL")

            # Verify the result is None
            assert price is None

    def test_get_beta_success(self):
        """Test successful beta fetching."""
        # Mock response data
        mock_profile = {
            "symbol": "AAPL",
            "price": 150.0,
            "beta": 1.2,
        }

        # Mock the fmpsdk.company_profile function
        with patch("fmpsdk.company_profile", return_value=[mock_profile]):
            beta = self.provider.get_beta("AAPL")

            # Verify the beta was fetched correctly
            assert beta == 1.2

    def test_get_beta_invalid_value(self):
        """Test beta fetching with invalid value."""
        # Mock response with invalid beta
        mock_profile = {
            "symbol": "AAPL",
            "price": 150.0,
            "beta": "invalid",
        }

        # Mock the fmpsdk.company_profile function
        with patch("fmpsdk.company_profile", return_value=[mock_profile]):
            beta = self.provider.get_beta("AAPL")

            # Verify the result is None
            assert beta is None

    def test_get_data_with_cache_option(self):
        """Test getting price and beta data together."""
        # Mock response data
        mock_profile = {
            "symbol": "AAPL",
            "price": 150.0,
            "beta": 1.2,
        }

        # Mock the fmpsdk.company_profile function
        with patch("fmpsdk.company_profile", return_value=[mock_profile]):
            # We need to patch twice because get_data_with_cache_option calls both get_price and get_beta
            with patch.object(self.provider, "get_price", return_value=150.0):
                with patch.object(self.provider, "get_beta", return_value=1.2):
                    price, beta = self.provider.get_data_with_cache_option("AAPL")

                    # Verify the data was fetched correctly
                    assert price == 150.0
                    assert beta == 1.2
