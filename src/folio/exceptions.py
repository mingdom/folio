"""
Custom exceptions for the Folio application.

This module defines application-specific exceptions that provide better context
and handling for different error conditions.
"""


class FolioError(Exception):
    """Base class for all Folio application exceptions."""
    pass


class DataError(FolioError):
    """Raised when there are issues with data processing or validation."""
    pass


class PortfolioError(FolioError):
    """Raised when there are issues with portfolio operations."""
    pass


class UIError(FolioError):
    """Raised when there are issues with the UI components."""
    pass


class ConfigurationError(FolioError):
    """Raised when there are issues with application configuration."""
    pass


class StateError(FolioError):
    """Raised when the application is in an invalid state."""

    @classmethod
    def no_selection(cls):
        """Create a StateError for the no selection state."""
        return cls("No row selected (normal during initialization)")

    @classmethod
    def invalid_row(cls, row, length):
        """Create a StateError for an invalid row index."""
        return cls(f"Row index out of range: {row}, groups length: {length}")
