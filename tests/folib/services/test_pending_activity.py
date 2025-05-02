"""Tests for pending activity detection in portfolio service."""

import pandas as pd

from src.folib.data.loader import parse_portfolio_holdings
from src.folib.services.portfolio_service import (
    _get_pending_activity,  # This will be renamed to get_pending_activity
)


def test_pending_activity_in_current_value_column():
    """Test detection of pending activity value in the Current Value column."""
    # Create a test DataFrame with pending activity in Current Value column
    df = pd.DataFrame(
        {
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [100, None],
            "Last Price": ["$150.00", ""],
            "Last Price Change": ["$1.50", ""],
            "Current Value": [
                "$15000.00",
                "$5000.00",
            ],  # Pending activity value in Current Value
            "Today's Gain/Loss Dollar": ["$150.00", ""],
            "Cost Basis Total": ["$14000.00", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is correctly detected
    assert pending_activity_value == 5000.00


def test_pending_activity_in_last_price_change_column():
    """Test detection of pending activity value in the Last Price Change column."""
    # Create a test DataFrame with pending activity in Last Price Change column
    df = pd.DataFrame(
        {
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [100, None],
            "Last Price": ["$150.00", ""],
            "Last Price Change": [
                "$1.50",
                "$6000.00",
            ],  # Pending activity value in Last Price Change
            "Current Value": ["$15000.00", ""],  # Empty Current Value
            "Today's Gain/Loss Dollar": ["$150.00", ""],
            "Cost Basis Total": ["$14000.00", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is correctly detected
    assert pending_activity_value == 6000.00


def test_pending_activity_in_todays_gain_loss_column():
    """Test detection of pending activity value in the Today's Gain/Loss Dollar column."""
    # Create a test DataFrame with pending activity in Today's Gain/Loss Dollar column
    df = pd.DataFrame(
        {
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [100, None],
            "Last Price": ["$150.00", ""],
            "Last Price Change": ["$1.50", ""],
            "Current Value": ["$15000.00", ""],  # Empty Current Value
            "Today's Gain/Loss Dollar": [
                "$150.00",
                "$7000.00",
            ],  # Pending activity value here
            "Cost Basis Total": ["$14000.00", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is correctly detected
    assert pending_activity_value == 7000.00


def test_pending_activity_with_multiple_rows():
    """Test detection of pending activity with multiple pending activity rows."""
    # Create a test DataFrame with multiple pending activity rows
    df = pd.DataFrame(
        {
            "Symbol": ["AAPL", "Pending Activity", "Pending Activity"],
            "Description": ["APPLE INC", "", ""],
            "Quantity": [100, None, None],
            "Last Price": ["$150.00", "", ""],
            "Last Price Change": [
                "$1.50",
                "$3000.00",
                "",
            ],  # Value in Last Price Change
            "Current Value": ["$15000.00", "", "$2000.00"],  # Value in Current Value
            "Today's Gain/Loss Dollar": ["$150.00", "", ""],
            "Cost Basis Total": ["$14000.00", "", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is correctly detected (sum of both rows)
    assert pending_activity_value == 5000.00


def test_pending_activity_with_no_value():
    """Test detection of pending activity with no value in any column."""
    # Create a test DataFrame with pending activity but no value
    df = pd.DataFrame(
        {
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [100, None],
            "Last Price": ["$150.00", ""],
            "Last Price Change": ["$1.50", ""],
            "Current Value": ["$15000.00", ""],  # Empty
            "Today's Gain/Loss Dollar": ["$150.00", ""],  # Empty
            "Cost Basis Total": ["$14000.00", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is 0 when no value is found
    assert pending_activity_value == 0.0


def test_pending_activity_with_real_world_csv_format1():
    """Test detection of pending activity with a real-world CSV format (Current Value column)."""
    # Create a test DataFrame mimicking the format in portfolio-pending-value1.csv
    df = pd.DataFrame(
        {
            "Account Number": ["Z26522634", "Z26522634"],
            "Account Name": ["GMX", "GMX"],
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [100, None],
            "Last Price": ["$150.00", ""],
            "Last Price Change": ["$1.50", ""],
            "Current Value": ["$15000.00", "$551528.45"],  # Value in Current Value
            "Today's Gain/Loss Dollar": ["$150.00", ""],
            "Today's Gain/Loss Percent": ["1.00%", ""],
            "Total Gain/Loss Dollar": ["$1000.00", ""],
            "Total Gain/Loss Percent": ["7.14%", ""],
            "Percent Of Account": ["5.00%", ""],
            "Cost Basis Total": ["$14000.00", ""],
            "Average Cost Basis": ["$140.00", ""],
            "Type": ["Margin", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is correctly detected
    assert pending_activity_value == 551528.45


def test_pending_activity_with_real_world_csv_format2():
    """Test detection of pending activity with a real-world CSV format (Last Price Change column)."""
    # Create a test DataFrame mimicking the format in portfolio-pending-value2.csv
    df = pd.DataFrame(
        {
            "Account Number": ["Z26522634", "Z26522634"],
            "Account Name": ["GMX", "GMX"],
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [100, None],
            "Last Price": ["$150.00", ""],
            "Last Price Change": ["$1.50", "$524609.67"],  # Value in Last Price Change
            "Current Value": ["$15000.00", ""],  # Empty Current Value
            "Today's Gain/Loss Dollar": ["$150.00", ""],
            "Today's Gain/Loss Percent": ["1.00%", ""],
            "Total Gain/Loss Dollar": ["$1000.00", ""],
            "Total Gain/Loss Percent": ["7.14%", ""],
            "Percent Of Account": ["5.00%", ""],
            "Cost Basis Total": ["$14000.00", ""],
            "Average Cost Basis": ["$140.00", ""],
            "Type": ["Margin", ""],
        }
    )

    # Parse the holdings
    holdings = parse_portfolio_holdings(df)

    # Detect pending activity
    pending_activity_value = _get_pending_activity(holdings)

    # Verify the pending activity value is correctly detected
    assert pending_activity_value == 524609.67
