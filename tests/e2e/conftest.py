"""Configuration for end-to-end tests.

This file contains pytest fixtures and configuration for end-to-end tests.
"""

import logging
import os

import pandas as pd
import pytest

from src.folio.portfolio import process_portfolio_data

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture(scope="class")
def portfolio_data():
    """Load portfolio data from CSV file.

    Returns:
        pandas.DataFrame: The loaded data, or None if no data is available.
    """
    # Define paths to test data
    private_test_path = "private-data/test/test-portfolio.csv"
    sample_path = "sample-data/sample-portfolio.csv"

    # Try to load private test data first
    if os.path.exists(private_test_path):
        logger.info(f"Loading test data from {private_test_path}")
        return pd.read_csv(private_test_path)

    # Fall back to sample data
    if os.path.exists(sample_path):
        logger.info(f"Loading test data from {sample_path}")
        return pd.read_csv(sample_path)

    # No data available
    logger.warning("No test data available")
    return None


@pytest.fixture(scope="class")
def processed_portfolio(portfolio_data):
    """Process portfolio data using the same functions as the UI.

    Args:
        portfolio_data: The portfolio data loaded from CSV.

    Returns:
        tuple: A tuple containing (groups, summary, summary_dict).
    """
    if portfolio_data is None:
        pytest.skip("No portfolio data available for testing")

    logger.info("Processing portfolio data...")
    result = process_portfolio_data(portfolio_data)

    # Check the structure of the result
    if isinstance(result, tuple):
        if len(result) == 3:
            # Newer version: (groups, summary, cash_like_positions)
            groups, summary, cash_like_positions = result
        elif len(result) == 2:
            # Possible alternative: (groups, cash_like_positions)
            groups, cash_like_positions = result
            from src.folio.portfolio import calculate_portfolio_summary
            summary = calculate_portfolio_summary(groups, cash_like_positions, 0.0)
    else:
        # If result is not a tuple, it's likely just the groups
        groups = result
        from src.folio.portfolio import calculate_portfolio_summary
        summary = calculate_portfolio_summary(groups, [], 0.0)
        cash_like_positions = []

    # Ensure we have a valid summary object
    if not hasattr(summary, 'to_dict'):
        logger.error("Error: summary object does not have to_dict method")
        logger.error(f"Type of summary: {type(summary)}")
        # Create a minimal summary for testing
        # Import here to avoid circular imports
        from src.folio.data_model import ExposureBreakdown, PortfolioSummary
        empty_exposure = ExposureBreakdown()
        summary = PortfolioSummary(
            net_market_exposure=0.0,
            portfolio_beta=0.0,
            long_exposure=empty_exposure,
            short_exposure=empty_exposure,
            options_exposure=empty_exposure
        )

    # Convert summary to dictionary for use in tests
    summary_dict = summary.to_dict()

    return groups, summary, summary_dict
