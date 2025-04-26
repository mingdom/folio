"""
Utility functions for error handling in the Folio application.

This module provides helper functions for consistent error handling
throughout the application.
"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from .logger import logger

# Type variable for function return type
T = TypeVar("T")


def log_exception(
    exc: Exception, message: str, include_traceback: bool = True, level: str = "error"
) -> None:
    """
    Log an exception with consistent formatting.

    Args:
        exc: The exception to log
        message: A descriptive message about what was happening
        include_traceback: Whether to include the traceback in the log
        level: The log level to use (error, warning, info, debug)
    """
    log_method = getattr(logger, level.lower())

    if include_traceback:
        log_method(f"{message}: {exc}", exc_info=True)
    else:
        log_method(f"{message}: {exc}")


def handle_callback_error(
    default_return: Any = None,
    error_message: str = "Error in callback",
    include_traceback: bool = True,
    log_level: str = "error",
    raise_exception: bool = False,
) -> Callable:
    """
    Decorator for handling errors in Dash callbacks.

    Args:
        default_return: The value to return if an exception occurs
        error_message: A descriptive message about what was happening
        include_traceback: Whether to include the traceback in the log
        log_level: The log level to use (error, warning, info, debug)
        raise_exception: Whether to re-raise the exception after logging

    Returns:
        A decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the exception
                log_exception(
                    e,
                    f"{error_message} in {func.__name__}",
                    include_traceback=include_traceback,
                    level=log_level,
                )

                # Re-raise if requested
                if raise_exception:
                    raise

                # Otherwise return the default value
                return default_return

        return wrapper

    return decorator


def safe_operation(
    operation_name: str,
    default_return: Any | None = None,
    include_traceback: bool = True,
    log_level: str = "error",
    raise_exception: bool = False,
) -> Callable:
    """
    Context manager for safely executing operations that might fail.

    Args:
        operation_name: A descriptive name for the operation
        default_return: The value to return if an exception occurs
        include_traceback: Whether to include the traceback in the log
        log_level: The log level to use (error, warning, info, debug)
        raise_exception: Whether to re-raise the exception after logging

    Returns:
        A context manager
    """

    class SafeOperation:
        def __init__(self):
            self.result = default_return

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, _exc_tb):
            if exc_type is not None:
                # Log the exception
                log_exception(
                    exc_val,
                    f"Error in {operation_name}",
                    include_traceback=include_traceback,
                    level=log_level,
                )

                # Don't re-raise if we're handling it
                return not raise_exception

            return False

    return SafeOperation()
