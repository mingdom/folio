"""Tests for option processing in portfolio.py.

This module tests the option processing functionality in portfolio.py to ensure
that refactoring doesn't introduce regressions.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.folio.portfolio import process_portfolio_data


@pytest.fixture
def sample_portfolio_with_options():
    """Create a sample portfolio DataFrame with options."""
    data = [
        # Stock position
        {
            "Symbol": "SPY",
            "Description": "SPDR S&P 500 ETF TRUST",
            "Quantity": "10",
            "Last Price": "100.00",
            "Current Value": "1000.00",
            "Percent Of Account": "10.00",
            "Type": "Cash",
            "Average Cost Basis": "95.00",
        },
        # Long call option
        {
            "Symbol": "-SPY",  # Option symbol starts with hyphen
            "Description": "SPY JUN 15 2025 $100 CALL",
            "Quantity": "2",
            "Last Price": "5.00",
            "Current Value": "1000.00",
            "Percent Of Account": "10.00",
            "Type": "Cash",
            "Average Cost Basis": "4.50",
        },
        # Short call option
        {
            "Symbol": "-SPY",
            "Description": "SPY JUN 15 2025 $110 CALL",
            "Quantity": "-1",
            "Last Price": "2.00",
            "Current Value": "-200.00",
            "Percent Of Account": "-2.00",
            "Type": "Cash",
            "Average Cost Basis": "1.80",
        },
        # Long put option
        {
            "Symbol": "-SPY",
            "Description": "SPY JUN 15 2025 $90 PUT",
            "Quantity": "1",
            "Last Price": "2.00",
            "Current Value": "200.00",
            "Percent Of Account": "2.00",
            "Type": "Cash",
            "Average Cost Basis": "1.90",
        },
        # Short put option
        {
            "Symbol": "-SPY",
            "Description": "SPY JUN 15 2025 $80 PUT",
            "Quantity": "-2",
            "Last Price": "1.00",
            "Current Value": "-200.00",
            "Percent Of Account": "-2.00",
            "Type": "Cash",
            "Average Cost Basis": "0.90",
        },
        # Orphaned option (no corresponding stock)
        {
            "Symbol": "-AAPL",
            "Description": "AAPL JUN 15 2025 $200 CALL",
            "Quantity": "1",
            "Last Price": "10.00",
            "Current Value": "1000.00",
            "Percent Of Account": "10.00",
            "Type": "Cash",
            "Average Cost Basis": "9.50",
        },
    ]
    return pd.DataFrame(data)


@patch("src.folio.portfolio.get_beta")
@patch("src.folio.portfolio.data_fetcher")
def test_option_processing(
    mock_data_fetcher, mock_get_beta, sample_portfolio_with_options
):
    """Test that option processing works correctly."""
    # Mock the data fetcher to return stock prices
    # Create a mock DataFrame with the expected structure
    mock_df = pd.DataFrame({"Close": [100.0]}, index=[pd.Timestamp("2025-01-01")])
    mock_aapl_df = pd.DataFrame({"Close": [200.0]}, index=[pd.Timestamp("2025-01-01")])

    # Set up the fetch_data method to return the mock DataFrame
    mock_data_fetcher.fetch_data.side_effect = (
        lambda symbol, period=None, interval=None: {
            "SPY": mock_df,
            "AAPL": mock_aapl_df,
        }.get(symbol, mock_df)
    )

    # Mock the beta function to return a fixed beta
    mock_get_beta.return_value = 1.0

    # Process the portfolio data
    groups, summary, cash_like = process_portfolio_data(sample_portfolio_with_options)

    # Verify that we have the expected number of groups
    assert len(groups) == 2, "Should have 2 groups (SPY and AAPL)"

    # Find the SPY group
    spy_group = next((g for g in groups if g.ticker == "SPY"), None)
    assert spy_group is not None, "Should have a group for SPY"

    # Verify that the SPY group has the expected number of options
    assert len(spy_group.option_positions) == 4, "SPY group should have 4 options"

    # Verify that each option has the expected attributes
    for opt in spy_group.option_positions:
        assert hasattr(opt, "delta"), "Option should have delta"
        assert hasattr(opt, "delta_exposure"), "Option should have delta_exposure"
        assert hasattr(opt, "beta_adjusted_exposure"), (
            "Option should have beta_adjusted_exposure"
        )
        assert hasattr(opt, "notional_value"), "Option should have notional_value"

    # Verify that the options have the correct signs for delta and exposure
    long_call = next(
        (
            o
            for o in spy_group.option_positions
            if o.option_type == "CALL" and o.quantity > 0
        ),
        None,
    )
    assert long_call is not None, "Should have a long call option"
    assert long_call.delta > 0, "Long call should have positive delta"
    assert long_call.delta_exposure > 0, "Long call should have positive delta exposure"

    short_call = next(
        (
            o
            for o in spy_group.option_positions
            if o.option_type == "CALL" and o.quantity < 0
        ),
        None,
    )
    assert short_call is not None, "Should have a short call option"
    assert short_call.delta < 0, "Short call should have negative delta"
    assert short_call.delta_exposure < 0, (
        "Short call should have negative delta exposure"
    )

    long_put = next(
        (
            o
            for o in spy_group.option_positions
            if o.option_type == "PUT" and o.quantity > 0
        ),
        None,
    )
    assert long_put is not None, "Should have a long put option"
    assert long_put.delta < 0, "Long put should have negative delta"
    assert long_put.delta_exposure < 0, "Long put should have negative delta exposure"

    short_put = next(
        (
            o
            for o in spy_group.option_positions
            if o.option_type == "PUT" and o.quantity < 0
        ),
        None,
    )
    assert short_put is not None, "Should have a short put option"
    assert short_put.delta > 0, "Short put should have positive delta"
    assert short_put.delta_exposure > 0, "Short put should have positive delta exposure"

    # Find the AAPL group (orphaned option)
    aapl_group = next((g for g in groups if g.ticker == "AAPL"), None)
    assert aapl_group is not None, "Should have a group for AAPL"

    # Verify that the AAPL group has the expected number of options
    assert len(aapl_group.option_positions) == 1, "AAPL group should have 1 option"

    # Verify that the orphaned option has the expected attributes
    aapl_option = aapl_group.option_positions[0]
    assert hasattr(aapl_option, "delta"), "Option should have delta"
    assert hasattr(aapl_option, "delta_exposure"), "Option should have delta_exposure"
    assert hasattr(aapl_option, "beta_adjusted_exposure"), (
        "Option should have beta_adjusted_exposure"
    )
    assert hasattr(aapl_option, "notional_value"), "Option should have notional_value"

    # Verify that the summary has option exposures
    assert hasattr(summary, "long_exposure"), "Summary should have long_exposure"
    assert hasattr(summary, "short_exposure"), "Summary should have short_exposure"
    assert hasattr(summary, "options_exposure"), "Summary should have options_exposure"

    # Verify that the option exposures are included in the summary
    assert summary.long_exposure.option_delta_exposure > 0, (
        "Summary should have positive long option exposure"
    )
    assert summary.short_exposure.option_delta_exposure < 0, (
        "Summary should have negative short option exposure"
    )
    assert summary.options_exposure.option_delta_exposure != 0, (
        "Summary should have non-zero net option exposure"
    )


@patch("src.folio.portfolio.get_beta")
@patch("src.folio.portfolio.data_fetcher")
def test_option_processing_with_errors(
    mock_data_fetcher, mock_get_beta, sample_portfolio_with_options
):
    """Test that option processing handles errors gracefully."""
    # Add an invalid option to the portfolio
    invalid_option = {
        "Symbol": "-SPY",
        "Description": "Invalid option description",  # Invalid description
        "Quantity": "1",
        "Last Price": "5.00",
        "Current Value": "500.00",
        "Percent Of Account": "5.00",
        "Type": "Cash",
    }
    df_with_invalid = pd.concat(
        [sample_portfolio_with_options, pd.DataFrame([invalid_option])]
    )

    # Mock the data fetcher to return stock prices
    # Create a mock DataFrame with the expected structure
    mock_df = pd.DataFrame({"Close": [100.0]}, index=[pd.Timestamp("2025-01-01")])
    mock_aapl_df = pd.DataFrame({"Close": [200.0]}, index=[pd.Timestamp("2025-01-01")])

    # Set up the fetch_data method to return the mock DataFrame
    mock_data_fetcher.fetch_data.side_effect = (
        lambda symbol, period=None, interval=None: {
            "SPY": mock_df,
            "AAPL": mock_aapl_df,
        }.get(symbol, mock_df)
    )

    # Mock the beta function to return a fixed beta
    mock_get_beta.return_value = 1.0

    # Process the portfolio data
    groups, summary, cash_like = process_portfolio_data(df_with_invalid)

    # Verify that we have the expected number of groups
    # Note: The invalid option creates a separate group with ticker '-SPY'
    assert len(groups) == 3, "Should have 3 groups (SPY, -SPY, and AAPL)"

    # Find the SPY group
    spy_group = next((g for g in groups if g.ticker == "SPY"), None)
    assert spy_group is not None, "Should have a group for SPY"

    # Verify that the SPY group still has the expected number of options (invalid one should be skipped)
    assert len(spy_group.option_positions) == 4, (
        "SPY group should have 4 options (invalid one should be skipped)"
    )
