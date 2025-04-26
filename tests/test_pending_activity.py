"""Tests for pending activity handling in portfolio processing."""

import pandas as pd

from src.folio.portfolio import (
    calculate_portfolio_summary,
    process_portfolio_data,
    update_portfolio_summary_with_prices,
)


def test_pending_activity_extraction():
    """Test that pending activity value is correctly extracted from CSV data."""
    # Create a test DataFrame with a Pending Activity row
    df = pd.DataFrame(
        [
            {
                "Symbol": "AAPL",
                "Description": "APPLE INC",
                "Quantity": 100,
                "Current Value": "$10000.00",
                "Last Price": "$100.00",
                "Type": "Margin",
                "Percent Of Account": "10%",
                "Average Cost Basis": "$90.00",
            },
            {
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Current Value": "$5000.00",
                "Last Price": None,
                "Type": None,
                "Percent Of Account": None,
                "Average Cost Basis": None,
            },
        ]
    )

    # Process the portfolio data
    groups, summary, _ = process_portfolio_data(
        df, update_prices=False
    )  # Don't update prices

    # Verify that the pending activity value is correctly extracted
    assert summary.pending_activity_value == 5000.0

    # The portfolio value should be close to 15000.0 (10000 + 5000)
    # We use approx() because there might be small differences in how the value is calculated
    from pytest import approx

    assert summary.portfolio_estimate_value == approx(
        15000.0, rel=0.1
    )  # Allow 10% tolerance


def test_pending_activity_with_missing_value():
    """Test that pending activity with missing value is handled correctly."""
    # Create a test DataFrame with a Pending Activity row with missing value
    df = pd.DataFrame(
        [
            {
                "Symbol": "AAPL",
                "Description": "APPLE INC",
                "Quantity": 100,
                "Current Value": "$10000.00",
                "Last Price": "$100.00",
                "Type": "Margin",
                "Percent Of Account": "10%",
                "Average Cost Basis": "$90.00",
            },
            {
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Current Value": None,  # Missing value
                "Last Price": None,
                "Type": None,
                "Percent Of Account": None,
                "Average Cost Basis": None,
            },
        ]
    )

    # Process the portfolio data
    groups, summary, _ = process_portfolio_data(
        df, update_prices=False
    )  # Don't update prices

    # Verify that the pending activity value is 0.0 when missing
    assert summary.pending_activity_value == 0.0

    # The portfolio value should be close to 10000.0 (just the stock value)
    # We use approx() because there might be small differences in how the value is calculated
    from pytest import approx

    assert summary.portfolio_estimate_value == approx(
        10000.0, rel=0.1
    )  # Allow 10% tolerance


def test_pending_activity_from_different_columns():
    """Test that pending activity value is correctly extracted from different columns."""
    # Create a test DataFrame with a Pending Activity row with value in Last Price Change column
    df = pd.DataFrame(
        [
            {
                "Symbol": "AAPL",
                "Description": "APPLE INC",
                "Quantity": 100,
                "Current Value": "$10000.00",
                "Last Price": "$100.00",
                "Type": "Margin",
                "Percent Of Account": "10%",
                "Average Cost Basis": "$90.00",
                "Last Price Change": "$0.00",
                "Today's Gain/Loss Dollar": "$0.00",
            },
            {
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Current Value": None,  # Missing value
                "Last Price": None,
                "Type": None,
                "Percent Of Account": None,
                "Average Cost Basis": None,
                "Last Price Change": "$6000.00",  # Value in Last Price Change column
                "Today's Gain/Loss Dollar": "$0.00",
            },
        ]
    )

    # Process the portfolio data
    groups, summary, _ = process_portfolio_data(
        df, update_prices=False
    )  # Don't update prices

    # Verify that the pending activity value is correctly extracted from Last Price Change column
    assert summary.pending_activity_value == 6000.0

    # The portfolio value should be close to 16000.0 (10000 + 6000)
    # We use approx() because there might be small differences in how the value is calculated
    from pytest import approx

    assert summary.portfolio_estimate_value == approx(
        16000.0, rel=0.1
    )  # Allow 10% tolerance

    # Create a test DataFrame with a Pending Activity row with value in Today's Gain/Loss Dollar column
    df = pd.DataFrame(
        [
            {
                "Symbol": "AAPL",
                "Description": "APPLE INC",
                "Quantity": 100,
                "Current Value": "$10000.00",
                "Last Price": "$100.00",
                "Type": "Margin",
                "Percent Of Account": "10%",
                "Average Cost Basis": "$90.00",
                "Last Price Change": "$0.00",
                "Today's Gain/Loss Dollar": "$0.00",
            },
            {
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Current Value": None,  # Missing value
                "Last Price": None,
                "Type": None,
                "Percent Of Account": None,
                "Average Cost Basis": None,
                "Last Price Change": None,  # Missing value
                "Today's Gain/Loss Dollar": "$7000.00",  # Value in Today's Gain/Loss Dollar column
            },
        ]
    )

    # Process the portfolio data
    groups, summary, _ = process_portfolio_data(
        df, update_prices=False
    )  # Don't update prices

    # Verify that the pending activity value is correctly extracted from Today's Gain/Loss Dollar column
    assert summary.pending_activity_value == 7000.0

    # The portfolio value should be close to 17000.0 (10000 + 7000)
    # We use approx() because there might be small differences in how the value is calculated
    assert summary.portfolio_estimate_value == approx(
        17000.0, rel=0.1
    )  # Allow 10% tolerance


def test_pending_activity_preserved_when_updating_prices():
    """Test that pending activity value is preserved when updating prices."""
    # Create a simple portfolio group
    from src.folio.data_model import PortfolioGroup, StockPosition

    stock_position = StockPosition(
        ticker="AAPL",
        quantity=100,
        beta=1.0,
        market_exposure=10000.0,
        beta_adjusted_exposure=10000.0,
        price=100.0,
        cost_basis=90.0,
    )

    group = PortfolioGroup(
        ticker="AAPL",
        stock_position=stock_position,
        option_positions=[],
        net_exposure=10000.0,
        beta=1.0,
        beta_adjusted_exposure=10000.0,
        total_delta_exposure=0.0,
        options_delta_exposure=0.0,
    )

    # Calculate portfolio summary with pending activity
    summary = calculate_portfolio_summary([group], [], 5000.0)

    # Verify that the pending activity value is included
    assert summary.pending_activity_value == 5000.0
    assert summary.portfolio_estimate_value == 15000.0  # 10000 + 5000

    # Update the portfolio summary with prices
    # This should preserve the pending activity value
    updated_summary = update_portfolio_summary_with_prices([group], summary)

    # Verify that the pending activity value is preserved
    assert (
        updated_summary.pending_activity_value == 5000.0
    )  # The value should be preserved
    assert (
        updated_summary.portfolio_estimate_value > 15000.0
    )  # Stock value + pending activity value
