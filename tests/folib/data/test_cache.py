"""
Unit tests for the cache module in src/folib/data/cache.py.

These tests focus on the functionality of the caching decorator and utilities,
with a focus on ensuring proper cache invalidation and fallback behavior.
"""

import os
import shutil
import time
from unittest.mock import MagicMock, patch

from src.folib.data.cache import (
    cached,
    clear_cache,
    get_cache_dir,
    get_cache_stats,
    log_cache_stats,
)


class TestCache:
    """Test the cache module functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary cache directory for testing
        self.test_cache_dir = os.path.join(os.path.dirname(__file__), "test_cache")
        os.makedirs(self.test_cache_dir, exist_ok=True)

    def teardown_method(self):
        """Tear down test fixtures."""
        # Remove the temporary cache directory
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

    def test_get_cache_dir(self):
        """Test that get_cache_dir returns a valid directory path."""
        cache_dir = get_cache_dir()
        assert isinstance(cache_dir, str)
        assert cache_dir.endswith(".cache")

    def test_cached_decorator_basic(self):
        """Test basic functionality of the cached decorator."""

        # Define a function to cache
        def test_func(*args, **kwargs):
            return "test_result"

        # Create a mock to track calls
        mock_func = MagicMock(side_effect=test_func)
        mock_func.__name__ = "test_func"

        # Apply the cached decorator
        cached_func = cached(ttl=3600, cache_dir=self.test_cache_dir)(mock_func)

        # Call the function twice
        result1 = cached_func("arg1", "arg2", kwarg1="value1")
        result2 = cached_func("arg1", "arg2", kwarg1="value1")

        # Check that the function was only called once
        assert mock_func.call_count == 1

        # Check that both calls returned the same result
        assert result1 == "test_result"
        assert result2 == "test_result"

        # Check cache stats
        stats = get_cache_stats()
        func_name = mock_func.__name__
        assert func_name in stats
        assert stats[func_name]["hits"] == 1
        assert stats[func_name]["misses"] == 1
        assert stats[func_name]["fallbacks"] == 0

    def test_cached_decorator_ttl(self):
        """Test TTL functionality of the cached decorator."""

        # Define a function to cache
        def test_func(*args, **kwargs):
            return "test_result"

        # Create a mock to track calls
        mock_func = MagicMock(side_effect=test_func)
        mock_func.__name__ = "test_ttl_func"

        # Apply the cached decorator with a TTL of 1 second
        cached_func = cached(ttl=1, cache_dir=self.test_cache_dir)(mock_func)

        # First call
        result1 = cached_func("arg1")

        # Simulate passage of time (2 seconds, which is > TTL)
        with patch("src.folib.data.cache.time.time", return_value=time.time() + 2):
            # Second call (cache should be expired)
            result2 = cached_func("arg1")

        # Check that the function was called twice (cache expired)
        assert mock_func.call_count == 2

        # Check that both calls returned the same result
        assert result1 == "test_result"
        assert result2 == "test_result"

        # Check cache stats
        stats = get_cache_stats()
        func_name = mock_func.__name__
        assert stats[func_name]["hits"] == 0
        assert stats[func_name]["misses"] == 2
        assert stats[func_name]["fallbacks"] == 0

    def test_cached_decorator_different_args(self):
        """Test that different arguments result in different cache entries."""

        # Define a function to cache
        def test_func(x):
            return f"result_{x}"

        # Create a mock to track calls
        mock_func = MagicMock(side_effect=test_func)
        mock_func.__name__ = "test_diff_args_func"

        # Apply the cached decorator
        cached_func = cached(ttl=3600, cache_dir=self.test_cache_dir)(mock_func)

        # Call the function with different arguments
        result1 = cached_func("arg1")
        result2 = cached_func("arg2")

        # Call the function again with the first argument
        result3 = cached_func("arg1")

        # Check that the function was called twice (once for each unique argument)
        assert mock_func.call_count == 2

        # Check that the results are correct
        assert result1 == "result_arg1"
        assert result2 == "result_arg2"
        assert result3 == "result_arg1"

        # Check cache stats
        stats = get_cache_stats()
        func_name = mock_func.__name__
        assert stats[func_name]["hits"] == 1
        assert stats[func_name]["misses"] == 2
        assert stats[func_name]["fallbacks"] == 0

    def test_cached_decorator_error_fallback(self):
        """Test that expired cache is used as fallback on error."""

        # Define a function with side effects
        def test_func(*args, **kwargs):
            if test_func.call_count == 0:
                test_func.call_count += 1
                return "result"
            else:
                test_func.call_count += 1
                raise Exception("Test error")

        test_func.call_count = 0

        # Create a mock to track calls
        mock_func = MagicMock(side_effect=test_func)
        mock_func.__name__ = "test_error_func"

        # Apply the cached decorator with a TTL of 1 second
        cached_func = cached(ttl=1, cache_dir=self.test_cache_dir)(mock_func)

        # First call
        result1 = cached_func("arg1")

        # Simulate passage of time (2 seconds, which is > TTL)
        with patch("src.folib.data.cache.time.time", return_value=time.time() + 2):
            # Second call (cache should be expired, but function will raise an exception)
            result2 = cached_func("arg1")

        # Check that the function was called twice
        assert mock_func.call_count == 2

        # Check that both calls returned the same result
        assert result1 == "result"
        assert result2 == "result"

        # Check cache stats
        stats = get_cache_stats()
        func_name = mock_func.__name__
        assert stats[func_name]["hits"] == 0
        assert stats[func_name]["misses"] == 2
        assert stats[func_name]["fallbacks"] == 1

    def test_clear_cache(self):
        """Test clearing the cache."""

        # Define a function to cache
        def test_func(*args, **kwargs):
            return "test_result"

        # Create a mock to track calls
        mock_func = MagicMock(side_effect=test_func)
        mock_func.__name__ = "test_clear_func"

        # Apply the cached decorator
        cached_func = cached(ttl=3600, cache_dir=self.test_cache_dir)(mock_func)

        # Call the function
        cached_func("arg1")

        # Clear the cache
        clear_cache(cache_dir=self.test_cache_dir)

        # Call the function again
        cached_func("arg1")

        # Check that the function was called twice
        assert mock_func.call_count == 2

        # Check cache stats were reset
        stats = get_cache_stats()
        func_name = mock_func.__name__
        assert stats[func_name]["hits"] == 0
        assert stats[func_name]["misses"] == 1
        assert stats[func_name]["fallbacks"] == 0

    def test_log_cache_stats(self, caplog):
        """Test logging cache statistics."""

        # Define a function to cache
        def test_func(*args, **kwargs):
            return "test_result"

        # Create a mock to track calls
        mock_func = MagicMock(side_effect=test_func)
        mock_func.__name__ = "test_log_func"

        # Apply the cached decorator
        cached_func = cached(ttl=3600, cache_dir=self.test_cache_dir)(mock_func)

        # Call the function twice
        cached_func("arg1")
        cached_func("arg1")

        # Log cache stats
        with caplog.at_level("INFO"):
            log_cache_stats()

        # Check that the log message contains the expected information
        assert "hit rate: 50.0%" in caplog.text
        assert "hits: 1" in caplog.text
        assert "misses: 1" in caplog.text
