"""
Unit tests for the MarketDataProvider class in src/folib/data/market_data.py.

These tests focus on the functionality of the MarketDataProvider class,
with external API calls mocked to prevent network requests.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from src.folib.data.market_data import MarketDataProvider


class TestMarketDataProvider:
    """Test the MarketDataProvider class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a provider instance with a mock API key
        self.provider = MarketDataProvider(api_key="test_key")
        # Clear the session cache before each test
        self.provider.clear_session_cache()

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

            # Verify the profile was fetched and cached correctly
            assert profile == mock_profile
            assert self.provider._session_cache["AAPL"]["profile"] == mock_profile
            assert self.provider._session_cache["AAPL"]["price"] == 150.0
            assert self.provider._session_cache["AAPL"]["beta"] == 1.2

    def test_fetch_profile_empty_response(self):
        """Test profile fetching with empty response."""
        # Mock empty response
        with patch("fmpsdk.company_profile", return_value=[]):
            profile = self.provider._fetch_profile("UNKNOWN")

            # Verify the result is None and cache reflects that
            assert profile is None
            assert self.provider._session_cache["UNKNOWN"]["profile"] is None

    def test_fetch_profile_api_error(self):
        """Test profile fetching with API error."""
        # Mock API error
        with patch("fmpsdk.company_profile", side_effect=Exception("API Error")):
            # The function should now raise the exception
            with pytest.raises(Exception, match="API Error"):
                self.provider._fetch_profile("AAPL")

            # Verify the session cache was updated before the exception was raised
            assert self.provider._session_cache["AAPL"]["profile"] is None

    def test_fetch_profile_cache_hit(self):
        """Test profile fetching with cache hit."""
        # Populate cache
        self.provider._session_cache["AAPL"] = {
            "profile": {"symbol": "AAPL", "price": 150.0, "beta": 1.2},
            "price": 150.0,
            "beta": 1.2,
        }

        # Mock should not be called due to cache hit
        with patch("fmpsdk.company_profile") as mock_company_profile:
            profile = self.provider._fetch_profile("AAPL")

            # Verify the profile was returned from cache
            assert profile == self.provider._session_cache["AAPL"]["profile"]
            mock_company_profile.assert_not_called()

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

    def test_get_price_cache_hit(self):
        """Test price fetching with cache hit."""
        # Populate cache
        self.provider._session_cache["AAPL"] = {
            "price": 150.0,
        }

        # Mock should not be called due to cache hit
        with patch("fmpsdk.company_profile") as mock_company_profile:
            price = self.provider.get_price("AAPL")

            # Verify the price was returned from cache
            assert price == 150.0
            mock_company_profile.assert_not_called()

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

    def test_get_beta_cache_hit(self):
        """Test beta fetching with cache hit."""
        # Populate cache
        self.provider._session_cache["AAPL"] = {
            "beta": 1.2,
        }

        # Mock should not be called due to cache hit
        with patch("fmpsdk.company_profile") as mock_company_profile:
            beta = self.provider.get_beta("AAPL")

            # Verify the beta was returned from cache
            assert beta == 1.2
            mock_company_profile.assert_not_called()

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

    def test_clear_session_cache(self):
        """Test clearing the session cache."""
        # Populate cache
        self.provider._session_cache["AAPL"] = {
            "profile": {"symbol": "AAPL", "price": 150.0, "beta": 1.2},
            "price": 150.0,
            "beta": 1.2,
        }

        # Clear cache
        self.provider.clear_session_cache()

        # Verify cache is empty
        assert self.provider._session_cache == {}

    def test_clear_all_cache(self):
        """Test clearing both in-session and disk cache."""
        # Populate session cache
        self.provider._session_cache["AAPL"] = {
            "profile": {"symbol": "AAPL", "price": 150.0, "beta": 1.2},
            "price": 150.0,
            "beta": 1.2,
        }

        # Mock the clear_disk_cache function
        with patch(
            "src.folib.data.market_data.clear_disk_cache"
        ) as mock_clear_disk_cache:
            # Clear all caches
            self.provider.clear_all_cache()

            # Verify session cache is empty
            assert self.provider._session_cache == {}

            # Verify disk cache was cleared
            mock_clear_disk_cache.assert_called_once()

    def test_log_cache_statistics(self, caplog):
        """Test logging cache statistics."""
        # Mock the log_cache_stats function
        with patch(
            "src.folib.data.market_data.log_cache_stats"
        ) as mock_log_cache_stats:
            # Log cache statistics
            self.provider.log_cache_statistics()

            # Verify log_cache_stats was called
            mock_log_cache_stats.assert_called_once()

    def test_persistent_cache_integration(self):
        """Test integration with persistent cache."""
        # Create a temporary directory for cache
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the get_cache_dir function to return our temp directory
            with patch("src.folib.data.cache.get_cache_dir", return_value=temp_dir):
                # Mock response data
                mock_profile = {
                    "symbol": "AAPL",
                    "price": 150.0,
                    "beta": 1.2,
                }

                # First call should miss cache and call the API
                with patch(
                    "fmpsdk.company_profile", return_value=[mock_profile]
                ) as mock_api:
                    price = self.provider.get_price("AAPL")
                    assert price == 150.0
                    mock_api.assert_called_once()

                # Second call should hit cache and not call the API
                with patch("fmpsdk.company_profile") as mock_api:
                    price = self.provider.get_price("AAPL")
                    assert price == 150.0
                    mock_api.assert_not_called()

                # Clear the session cache but keep the disk cache
                self.provider.clear_session_cache()

                # Third call should hit disk cache and not call the API
                with patch("fmpsdk.company_profile") as mock_api:
                    price = self.provider.get_price("AAPL")
                    assert price == 150.0
                    mock_api.assert_not_called()
