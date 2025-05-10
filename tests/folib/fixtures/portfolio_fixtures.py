"""
Fixtures for portfolio tests.

This module provides fixtures for testing portfolio functionality,
including mock services and test data.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.services.portfolio_service import process_portfolio
from tests.folib.fixtures.mock_ticker_service import (
    TEST_PORTFOLIO_TICKER_DATA,
    MockTickerService,
)


@pytest.fixture
def test_portfolio_path():
    """Return the path to the test portfolio CSV file."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    portfolio_path = project_root / "tests" / "assets" / "test_portfolio.csv"
    assert portfolio_path.exists(), f"Test portfolio file not found at {portfolio_path}"
    return portfolio_path


@pytest.fixture
def mock_ticker_service():
    """Return a mock ticker service with test data."""
    return MockTickerService(TEST_PORTFOLIO_TICKER_DATA)


@pytest.fixture
def patched_ticker_service(mock_ticker_service):
    """
    Patch the ticker_service in the portfolio_service module.

    This fixture temporarily replaces the real ticker_service with a mock
    implementation during test execution, ensuring consistent and
    deterministic test results without making any API calls.
    """
    # Path to the ticker_service in the portfolio_service module
    target = "src.folib.services.portfolio_service.ticker_service"

    # Apply the patch
    with patch(target, mock_ticker_service):
        yield mock_ticker_service


@pytest.fixture
def test_portfolio_holdings(test_portfolio_path):
    """Return the parsed holdings from the test portfolio CSV file."""
    df = load_portfolio_from_csv(test_portfolio_path)
    return parse_portfolio_holdings(df)


@pytest.fixture
def test_portfolio(test_portfolio_holdings, patched_ticker_service):
    """
    Return a processed portfolio from the test portfolio holdings.

    This fixture uses the patched_ticker_service to ensure consistent
    and deterministic test results.

    Args:
        test_portfolio_holdings: The portfolio holdings to process
        patched_ticker_service: Not used directly, but required to ensure the ticker
                               service is patched before processing the portfolio.
    """
    # We need to explicitly use patched_ticker_service to satisfy the linter
    # This is a common pattern in pytest - the fixture is needed for its side effects
    assert patched_ticker_service is not None, "Ticker service must be patched"

    return process_portfolio(test_portfolio_holdings)
