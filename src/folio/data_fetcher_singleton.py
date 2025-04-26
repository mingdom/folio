"""Singleton module for data fetcher.

This module provides a singleton instance of the data fetcher to ensure
it's only initialized once across the application.
"""

import os

import yaml

from src.stockdata import create_data_fetcher

from .logger import logger


class DataFetcherSingleton:
    """Singleton class for data fetcher."""

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the data fetcher.

        Returns:
            DataFetcherInterface: The data fetcher instance.
        """
        if cls._instance is None:
            cls._instance = cls._initialize_data_fetcher()
        return cls._instance

    @classmethod
    def _initialize_data_fetcher(cls):
        """Initialize the data fetcher.

        Returns:
            DataFetcherInterface: The initialized data fetcher.

        Raises:
            RuntimeError: If the data fetcher initialization fails.
        """
        if cls._initialized:
            return cls._instance

        # Load configuration
        config = cls._load_config()

        try:
            # Get data source from config (default to "yfinance" if not specified)
            data_source = config.get("app", {}).get("data_source", "yfinance")
            logger.info(f"Using data source: {data_source}")

            # Create data fetcher using factory
            data_fetcher = create_data_fetcher(source=data_source)

            if data_fetcher is None:
                raise RuntimeError(
                    "Data fetcher initialization failed but didn't raise an exception"
                )

            cls._initialized = True
            return data_fetcher
        except ValueError as e:
            logger.error(f"Failed to initialize data fetcher: {e}")
            # Re-raise to fail fast rather than continuing with a null reference
            raise RuntimeError(
                f"Critical component data fetcher could not be initialized: {e}"
            ) from e

    @staticmethod
    def _load_config():
        """Load configuration from folio.yaml.

        Returns:
            dict: The configuration dictionary.
        """
        config_path = os.path.join(os.path.dirname(__file__), "folio.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(
                    f"Failed to load folio.yaml: {e}. Using default configuration."
                )
        return {}


# Convenience function to get the data fetcher instance
def get_data_fetcher():
    """Get the singleton instance of the data fetcher.

    Returns:
        DataFetcherInterface: The data fetcher instance.
    """
    return DataFetcherSingleton.get_instance()
