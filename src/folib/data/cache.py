"""
Caching utilities for data providers.

This module provides decorators and utilities for caching data from external sources.
It supports persistent caching with configurable TTLs and fallback to expired cache.
"""

import functools
import logging
import os
import shutil
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from diskcache import Cache

logger = logging.getLogger(__name__)

# Type variables for better type hinting
T = TypeVar("T")
R = TypeVar("R")

# Cache statistics
_cache_stats: dict[str, dict[str, int]] = {}


def get_cache_dir() -> str:
    """Get the cache directory path."""
    # Use project root/.cache by default
    return os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ),
        ".cache",
    )


def cached(
    ttl: int = 3600,  # Default: 1 hour
    key_prefix: str = "",
    cache_dir: str | None = None,
    use_expired_on_error: bool = True,
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Decorator for caching function results to disk.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_dir: Directory to store cache files
        use_expired_on_error: Whether to use expired cache on error

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        # Initialize cache statistics for this function
        func_name = f"{key_prefix}_{func.__name__}" if key_prefix else func.__name__
        if func_name not in _cache_stats:
            _cache_stats[func_name] = {"hits": 0, "misses": 0, "fallbacks": 0}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            # Check if skip_cache is in kwargs and is True
            skip_cache = kwargs.pop("skip_cache", False)
            if skip_cache:
                # Get the relevant argument for logging (skip self if it's a method)
                arg_str = _get_log_arg_str(args)
                logger.debug(
                    f"Skipping cache for {func_name}{arg_str} (--no-cache flag)"
                )
                _cache_stats[func_name]["misses"] += 1
                return func(*args, **kwargs)

            # Get cache directory
            cache_directory = cache_dir or get_cache_dir()
            os.makedirs(cache_directory, exist_ok=True)

            # Create cache key
            cache_key = _create_cache_key(func, key_prefix, args, kwargs)

            # Initialize cache
            with Cache(cache_directory) as cache:
                # Try to get from cache
                cache_item = cache.get(cache_key)
                current_time = time.time()

                if cache_item is not None:
                    value, timestamp = cache_item

                    # Check if cache is still valid
                    if current_time - timestamp <= ttl:
                        # Get the relevant argument for logging (skip self if it's a method)
                        arg_str = _get_log_arg_str(args)
                        logger.debug(f"Cache hit for {func_name}{arg_str}")
                        _cache_stats[func_name]["hits"] += 1
                        return cast(R, value)

                    # Cache is expired
                    cache_age_hours = (current_time - timestamp) / 3600
                    # Get the relevant argument for logging (skip self if it's a method)
                    arg_str = _get_log_arg_str(args)
                    logger.debug(
                        f"Cache expired for {func_name}{arg_str} (age: {cache_age_hours:.2f} hours)"
                    )

                # Cache miss or expired
                # Get the relevant argument for logging (skip self if it's a method)
                arg_str = _get_log_arg_str(args)
                logger.debug(f"Cache miss for {func_name}{arg_str}")
                _cache_stats[func_name]["misses"] += 1

                try:
                    # Call the original function
                    result = func(*args, **kwargs)

                    # Store in cache
                    cache.set(cache_key, (result, current_time))

                    return result
                except Exception as e:
                    # If we have expired cache and use_expired_on_error is True
                    if cache_item is not None and use_expired_on_error:
                        value, timestamp = cache_item
                        cache_age_hours = (current_time - timestamp) / 3600
                        # Get the relevant argument for logging (skip self if it's a method)
                        arg_str = _get_log_arg_str(args)
                        logger.warning(
                            f"Error calling {func_name}{arg_str}, using expired cache as fallback. "
                            f"Cache age: {cache_age_hours:.2f} hours. Error: {e}"
                        )
                        _cache_stats[func_name]["fallbacks"] += 1
                        return cast(R, value)

                    # Re-raise the exception
                    raise

        return wrapper

    return decorator


def _get_log_arg_str(args: tuple) -> str:
    """
    Get a string representation of the relevant argument for logging.

    For methods, skip the 'self' parameter and use the first actual argument.
    For functions, use the first argument if available.

    Args:
        args: Tuple of positional arguments

    Returns:
        String representation of the relevant argument for logging
    """
    if not args:
        return ""

    # If the first argument is likely a 'self' parameter (has __class__ attribute)
    if hasattr(args[0], "__class__"):
        # If there's a second argument, use that instead
        if len(args) > 1:
            return f"({args[1]})"
        return ""

    # Otherwise, use the first argument
    return f"({args[0]})"


def _create_cache_key(func: Callable, prefix: str, args: tuple, kwargs: dict) -> str:
    """Create a cache key from function name and arguments."""
    # Start with function name
    key_parts = [func.__module__, func.__name__]

    # Add prefix if provided
    if prefix:
        key_parts.insert(0, prefix)

    # Add positional arguments
    for arg in args:
        key_parts.append(str(arg))

    # Add keyword arguments (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    # Join with underscore and return
    return "_".join(key_parts)


def get_cache_stats() -> dict[str, dict[str, int]]:
    """Get cache statistics."""
    return _cache_stats


def log_cache_stats(aggregate: bool = True) -> None:
    """
    Log cache statistics at INFO level.

    Args:
        aggregate: If True, log all statistics in a single message.
                  If False, log overall statistics and detailed statistics separately.
    """
    # Calculate overall statistics
    total_hits = sum(stats["hits"] for stats in _cache_stats.values())
    total_misses = sum(stats["misses"] for stats in _cache_stats.values())
    total_fallbacks = sum(stats["fallbacks"] for stats in _cache_stats.values())
    total_requests = total_hits + total_misses
    overall_hit_rate = (total_hits / total_requests) * 100 if total_requests > 0 else 0

    if aggregate:
        # Build a single aggregated message with all statistics
        message_parts = [
            f"Cache hit rate: {overall_hit_rate:.1f}% (hits: {total_hits}, misses: {total_misses}, fallbacks: {total_fallbacks})"
        ]

        # Add per-function statistics
        for func_name, stats in _cache_stats.items():
            total = stats["hits"] + stats["misses"]
            if total > 0:  # Only include functions with activity
                hit_rate = (stats["hits"] / total) * 100 if total > 0 else 0
                func_display = func_name.replace("_", " ").strip()
                message_parts.append(
                    f"  {func_display}: {hit_rate:.1f}% (hits: {stats['hits']}, misses: {stats['misses']})"
                )

        # Log the aggregated message
        logger.info("\n".join(message_parts))
    else:
        # Log overall statistics
        logger.info(
            f"Cache overall hit rate: {overall_hit_rate:.1f}% "
            f"(hits: {total_hits}, misses: {total_misses}, fallbacks: {total_fallbacks}, "
            f"total requests: {total_requests})"
        )

        # Log detailed statistics for each function
        for func_name, stats in _cache_stats.items():
            total = stats["hits"] + stats["misses"]
            hit_rate = (stats["hits"] / total) * 100 if total > 0 else 0
            logger.info(
                f"Cache stats for {func_name}: "
                f"hit rate: {hit_rate:.1f}% "
                f"(hits: {stats['hits']}, misses: {stats['misses']}, fallbacks: {stats['fallbacks']})"
            )


def clear_cache(cache_dir: str | None = None, backup: bool = False) -> None:
    """
    Clear the entire cache.

    Args:
        cache_dir: Directory containing the cache. If None, uses the default cache directory.
        backup: If True, backs up the cache to a backup directory before clearing it.
    """
    cache_directory = cache_dir or get_cache_dir()

    if os.path.exists(cache_directory):
        if backup:
            # Create backup directory
            backup_dir = os.path.join(cache_directory, "backup")
            backup_timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"cache_backup_{backup_timestamp}")

            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)

            # Copy cache files to backup directory
            try:
                # Copy all files except the backup directory itself
                for item in os.listdir(cache_directory):
                    if item != "backup":
                        src_path = os.path.join(cache_directory, item)
                        dst_path = os.path.join(backup_path, item)
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                        else:
                            # Ensure parent directory exists
                            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                            shutil.copy2(src_path, dst_path)
                logger.info(f"Cache backed up to {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to backup cache: {e}")

        # Clear the cache
        with Cache(cache_directory) as cache:
            cache.clear()
        logger.info(f"Cache cleared from {cache_directory}")

    # Reset statistics
    for func_stats in _cache_stats.values():
        for key in func_stats:
            func_stats[key] = 0
