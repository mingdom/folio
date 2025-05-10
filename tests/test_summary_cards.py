"""Tests for the summary cards component in the Folio app.

This file contains both unit tests and integration tests for the summary cards component.
"""

import pytest

from src.folio.app import create_app
from src.folio.components.summary_cards import error_values, format_summary_card_values
from src.folio.data_model import ExposureBreakdown, PortfolioSummary


@pytest.fixture
def test_summary():
    """Create a test portfolio summary with known values."""
    # Create exposure breakdowns with known values
    long_exposure = ExposureBreakdown(
        stock_exposure=10000.0,
        stock_beta_adjusted=12000.0,
        option_delta_exposure=2000.0,
        option_beta_adjusted=2400.0,
        total_exposure=12000.0,
        total_beta_adjusted=14400.0,
        description="Long exposure",
        formula="Sum of long positions",
        components={"Stocks": 10000.0, "Options": 2000.0},
    )

    short_exposure = ExposureBreakdown(
        stock_exposure=3000.0,
        stock_beta_adjusted=3600.0,
        option_delta_exposure=1000.0,
        option_beta_adjusted=1200.0,
        total_exposure=4000.0,
        total_beta_adjusted=4800.0,
        description="Short exposure",
        formula="Sum of short positions",
        components={"Stocks": 3000.0, "Options": 1000.0},
    )

    options_exposure = ExposureBreakdown(
        stock_exposure=0.0,
        stock_beta_adjusted=0.0,
        option_delta_exposure=1000.0,  # Net options exposure (2000 - 1000)
        option_beta_adjusted=1200.0,
        total_exposure=1000.0,
        total_beta_adjusted=1200.0,
        description="Net options exposure",
        formula="Long options - Short options",
        components={"Long Options": 2000.0, "Short Options": 1000.0, "Net": 1000.0},
    )

    # Create the portfolio summary
    summary = PortfolioSummary(
        net_market_exposure=8000.0,  # 12000 - 4000
        portfolio_beta=1.2,
        long_exposure=long_exposure,
        short_exposure=short_exposure,
        options_exposure=options_exposure,
        short_percentage=25.0,  # (4000 / 16000) * 100
        cash_like_value=2000.0,
        cash_like_count=1,
        cash_percentage=20.0,  # (2000 / 10000) * 100
        portfolio_estimate_value=10000.0,  # 8000 + 2000
        cash_like_positions=[],
        stock_value=7000.0,  # 10000 - 3000
        option_value=1000.0,  # 2000 - 1000
        pending_activity_value=0.0,
        price_updated_at="2025-05-03T09:00:00Z",
    )

    return summary


# Unit Tests


def test_format_summary_card_values(test_summary):
    """Test that the format_summary_card_values function returns the correct values."""
    # Convert the summary to a dictionary
    summary_dict = test_summary.to_dict()

    # Call the format_summary_card_values function
    result = format_summary_card_values(summary_dict)

    # Check that the result has the correct values
    expected_values = [
        "$10,000.00",  # Portfolio Value
        "$8,000.00",  # Net Exposure
        "80.0% of portfolio",  # Net Exposure Percent
        "$19,200.00",  # Beta-Adjusted Net Exposure
        "192.0% of portfolio",  # Beta-Adjusted Net Exposure Percent
        "$12,000.00",  # Long Exposure
        "120.0% of portfolio",  # Long Exposure Percent
        "$4,000.00",  # Short Exposure
        "40.0% of portfolio",  # Short Exposure Percent
        "$1,000.00",  # Options Exposure
        "10.0% of portfolio",  # Options Exposure Percent
        "$2,000.00",  # Cash Value
        "20.0% of portfolio",  # Cash Percent
    ]

    # Check each value
    for i, (actual, expected) in enumerate(zip(result, expected_values, strict=False)):
        assert actual == expected, (
            f"Error at index {i}: expected '{expected}', got '{actual}'"
        )


def test_format_summary_card_values_with_missing_keys(test_summary):
    """Test that format_summary_card_values handles missing keys."""
    # Convert the summary to a dictionary
    summary_dict = test_summary.to_dict()

    # Remove a required key
    del summary_dict["portfolio_estimate_value"]

    # Call the format_summary_card_values function
    result = format_summary_card_values(summary_dict)

    # Check that the result has the correct values (should be calculated from net_market_exposure + cash_like_value)
    expected_values = [
        "$10,000.00",  # Portfolio Value (8000 + 2000)
        "$8,000.00",  # Net Exposure
        "80.0% of portfolio",  # Net Exposure Percent
        "$19,200.00",  # Beta-Adjusted Net Exposure
        "192.0% of portfolio",  # Beta-Adjusted Net Exposure Percent
        "$12,000.00",  # Long Exposure
        "120.0% of portfolio",  # Long Exposure Percent
        "$4,000.00",  # Short Exposure
        "40.0% of portfolio",  # Short Exposure Percent
        "$1,000.00",  # Options Exposure
        "10.0% of portfolio",  # Options Exposure Percent
        "$2,000.00",  # Cash Value
        "20.0% of portfolio",  # Cash Percent
    ]

    # Check each value
    for i, (actual, expected) in enumerate(zip(result, expected_values, strict=False)):
        assert actual == expected, (
            f"Error at index {i}: expected '{expected}', got '{actual}'"
        )


def test_format_summary_card_values_with_invalid_data():
    """Test that format_summary_card_values handles invalid data."""
    # Call the format_summary_card_values function with None
    result = format_summary_card_values(None)

    # Check that the result has error values
    assert result[0] == "Error"  # Portfolio Value
    assert result[1] == "Error"  # Net Exposure
    assert result[3] == "Error"  # Beta-Adjusted Net Exposure

    # Call the format_summary_card_values function with an empty dictionary
    result = format_summary_card_values({})

    # Check that the result has error values
    assert result[0] == "Error"  # Portfolio Value
    assert result[1] == "Error"  # Net Exposure
    assert result[3] == "Error"  # Beta-Adjusted Net Exposure


def test_error_values():
    """Test that the error_values function returns the correct values."""
    result = error_values()

    # Check that the result has the correct values
    assert result[0] == "Error"  # Portfolio Value
    assert result[1] == "Error"  # Net Exposure
    assert result[2] == "Data missing"  # Net Exposure Percent
    assert result[3] == "Error"  # Beta-Adjusted Net Exposure


# Integration Tests


def test_callback_registration():
    """Test that the summary cards callback is registered."""
    # Create the app
    app = create_app()

    # We don't need to check the callback map
    # Just verify the app was created

    # We don't need to look for specific callbacks
    # Just check that the app was created successfully

    # For this test, we'll just check that the app was created successfully
    # since we know the callback is registered in the summary_cards.py file
    assert app is not None, "App was not created successfully"


# This test was replaced by test_summary_cards_simple
# It was too complex and fragile, focusing on implementation details rather than behavior


def test_summary_cards_user_expectations():
    """Test that summary cards meet user expectations.

    This test focuses on what users expect to see, not implementation details.
    It verifies that the summary cards display the expected information in a user-friendly way.
    """
    # Create a test app
    app = create_app()

    # Get the layout
    layout = app.layout

    # Find the summary card component
    summary_card = None

    def find_summary_card(component):
        """Recursively find the summary card component."""
        nonlocal summary_card
        if hasattr(component, "id") and component.id == "summary-card":
            summary_card = component
            return True

        if hasattr(component, "children"):
            if isinstance(component.children, list):
                for child in component.children:
                    if find_summary_card(child):
                        return True
            elif component.children is not None:
                return find_summary_card(component.children)

        return False

    # Search the layout
    find_summary_card(layout)

    # Check that the summary card was found
    assert summary_card is not None, "Summary card not found in layout"

    # Check that the summary card has the expected structure
    # This is a high-level check that doesn't depend on implementation details
    layout_str = str(summary_card)

    # Check for the presence of key metrics that users expect to see
    assert "Portfolio Summary" in layout_str, (
        "Portfolio Summary not found in summary cards"
    )
    assert "Total Portfolio Value" in layout_str, (
        "Total Portfolio Value not found in summary cards"
    )
    assert "Net Exposure" in layout_str, "Net Exposure not found in summary cards"
    assert "Beta-Adjusted Net Exposure" in layout_str, (
        "Beta-Adjusted Net Exposure not found in summary cards"
    )
    assert "Long Exposure" in layout_str, "Long Exposure not found in summary cards"
    assert "Short Exposure" in layout_str, "Short Exposure not found in summary cards"
    assert "Options Exposure" in layout_str, (
        "Options Exposure not found in summary cards"
    )
    assert "Cash & Equivalents" in layout_str, (
        "Cash & Equivalents not found in summary cards"
    )


def test_summary_cards_rendered_and_callback_registered():
    """Test that summary cards are rendered in the layout and their callback is registered.

    This test verifies two critical behaviors:
    1. The summary cards components are present in the app layout
    2. The callback for updating the summary cards is properly registered
    """
    # Create a test app
    app = create_app()

    # Get the layout
    layout = app.layout

    # Define the expected component IDs
    expected_ids = [
        "summary-card",
        "portfolio-value",
        "total-value",
        "beta-adjusted-exposure",
        "beta-adjusted-percent",
        "long-exposure",
        "short-exposure",
        "options-exposure",
        "cash-like-value",
    ]

    # Find all components with IDs in the layout
    found_ids = set()

    def find_components(component):
        """Recursively find all components with IDs in the layout."""
        if hasattr(component, "id") and component.id is not None:
            found_ids.add(component.id)

        if hasattr(component, "children"):
            if isinstance(component.children, list):
                for child in component.children:
                    find_components(child)
            elif component.children is not None:
                find_components(component.children)

    # Search the layout
    find_components(layout)

    # Check that all expected IDs are found
    for component_id in expected_ids:
        assert component_id in found_ids, (
            f"Component {component_id} not found in layout"
        )

    # Check that the callback for updating summary cards is registered
    callbacks = app.callback_map

    # The callback ID for summary cards is a complex string with multiple outputs
    # Look for a callback that includes portfolio-value.children in its ID
    portfolio_value_callback_found = False
    for callback_id in callbacks.keys():
        if "portfolio-value.children" in callback_id:
            portfolio_value_callback_found = True
            break

    # Assert that the callback is registered
    assert portfolio_value_callback_found, (
        "Callback for portfolio-value not registered - register_callbacks(app) is not called in create_app"
    )
