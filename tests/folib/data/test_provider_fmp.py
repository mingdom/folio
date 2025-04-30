"""
Unit tests for the FMPProvider class in src/folib/data/provider_fmp.py.

These tests focus only on the pure functions: period and interval parsing.
No provider functionality is tested to avoid API calls.
"""

import pytest

from src.folib.data.provider_fmp import FMPProvider


class TestFMPProviderParsing:
    """Test the period and interval parsing functions in FMPProvider."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a provider instance with a mock API key
        self.provider = FMPProvider(api_key="test_key", cache_dir=None)

    def test_period_parsing_days(self):
        """Test parsing period strings with days."""
        assert self.provider._map_period_to_days("1d") == "1"
        assert self.provider._map_period_to_days("5d") == "5"
        assert self.provider._map_period_to_days("30d") == "30"

    def test_period_parsing_months(self):
        """Test parsing period strings with months."""
        assert self.provider._map_period_to_days("1mo") == "30"
        assert self.provider._map_period_to_days("3mo") == "90"
        assert self.provider._map_period_to_days("6mo") == "180"

    def test_period_parsing_years(self):
        """Test parsing period strings with years."""
        assert self.provider._map_period_to_days("1y") == "365"
        assert self.provider._map_period_to_days("2y") == "730"
        assert self.provider._map_period_to_days("5y") == "1825"

    def test_period_parsing_special_cases(self):
        """Test parsing special period strings."""
        assert self.provider._map_period_to_days("ytd") == "ytd"
        assert self.provider._map_period_to_days("max") == "max"

    def test_period_parsing_invalid(self):
        """Test that invalid period strings raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported period format"):
            self.provider._map_period_to_days("")

        with pytest.raises(ValueError, match="Unsupported period format"):
            self.provider._map_period_to_days("invalid")

        with pytest.raises(ValueError, match="Unsupported period format"):
            self.provider._map_period_to_days("1x")

    def test_interval_parsing_minutes(self):
        """Test parsing interval strings with minutes."""
        assert self.provider._map_interval_to_fmp("1m") == "1min"
        assert self.provider._map_interval_to_fmp("5m") == "5min"
        assert self.provider._map_interval_to_fmp("15m") == "15min"
        assert self.provider._map_interval_to_fmp("30m") == "30min"

    def test_interval_parsing_hours(self):
        """Test parsing interval strings with hours."""
        assert self.provider._map_interval_to_fmp("1h") == "1hour"
        assert self.provider._map_interval_to_fmp("4h") == "4hour"

    def test_interval_parsing_special_cases(self):
        """Test parsing special interval strings."""
        assert self.provider._map_interval_to_fmp("1d") == "daily"
        assert self.provider._map_interval_to_fmp("1wk") == "weekly"
        assert self.provider._map_interval_to_fmp("1mo") == "monthly"

    def test_interval_parsing_invalid(self):
        """Test that invalid interval strings raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported interval format"):
            self.provider._map_interval_to_fmp("")

        with pytest.raises(ValueError, match="Unsupported interval format"):
            self.provider._map_interval_to_fmp("invalid")

        with pytest.raises(ValueError, match="Unsupported interval format"):
            self.provider._map_interval_to_fmp("1d1")
