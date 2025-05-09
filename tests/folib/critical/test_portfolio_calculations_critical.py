"""
Critical tests for portfolio calculation functionality.

This module contains critical tests for the portfolio calculation functionality,
focusing on ensuring that portfolio values, exposures, and other key metrics
are correctly calculated from portfolio CSV files.

These tests are marked as 'critical' because they verify core functionality
that directly impacts user experience. Failures in these tests indicate
serious issues that must be addressed immediately.

The tests specifically focus on:
1. Correct calculation of portfolio total value
2. Correct calculation of market exposure
3. Correct calculation of beta-adjusted exposure
4. Consistency of calculations across portfolio processing
"""

from pathlib import Path

import pytest

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.services.portfolio_service import (
    create_portfolio_summary,
    get_portfolio_exposures,
    process_portfolio,
)


@pytest.fixture
def test_portfolio_path():
    """Return the path to the test portfolio CSV file."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    portfolio_path = project_root / "tests" / "assets" / "test_portfolio.csv"
    assert portfolio_path.exists(), f"Test portfolio file not found at {portfolio_path}"
    return portfolio_path


@pytest.mark.critical
def test_portfolio_total_value_calculation(test_portfolio_path):
    """
    CRITICAL TEST: Verify that the portfolio total value is correctly calculated.

    This test ensures that the total value of the portfolio is correctly calculated
    from the individual position values in the CSV file. It specifically checks that
    the sum of all position values plus pending activity matches the total value
    reported in the portfolio summary.

    Failure in this test indicates a serious issue with the portfolio value calculation
    logic that would result in incorrect portfolio valuation for users.
    """
    # Load the CSV file
    df = load_portfolio_from_csv(test_portfolio_path)

    # Parse the portfolio holdings
    holdings = parse_portfolio_holdings(df)

    # Process the portfolio
    portfolio = process_portfolio(holdings)

    # Create portfolio summary
    summary = create_portfolio_summary(portfolio)

    # Hardcoded expected values based on test_portfolio.csv
    EXPECTED_TOTAL_VALUE = 2800822.40
    EXPECTED_STOCK_VALUE = 1823711.39
    EXPECTED_OPTION_VALUE = -142570.00
    EXPECTED_CASH_VALUE = 593093.76
    EXPECTED_UNKNOWN_VALUE = 0.00
    EXPECTED_PENDING_ACTIVITY = 526587.25

    # Verify total value matches expected value
    assert abs(summary.total_value - EXPECTED_TOTAL_VALUE) < 0.01, (
        f"Expected total value {EXPECTED_TOTAL_VALUE}, but got {summary.total_value}. "
        f"The portfolio total value calculation is incorrect."
    )

    # Verify individual component values
    assert abs(summary.stock_value - EXPECTED_STOCK_VALUE) < 0.01, (
        f"Expected stock value {EXPECTED_STOCK_VALUE}, but got {summary.stock_value}."
    )

    assert abs(summary.option_value - EXPECTED_OPTION_VALUE) < 0.01, (
        f"Expected option value {EXPECTED_OPTION_VALUE}, but got {summary.option_value}."
    )

    assert abs(summary.cash_value - EXPECTED_CASH_VALUE) < 0.01, (
        f"Expected cash value {EXPECTED_CASH_VALUE}, but got {summary.cash_value}."
    )

    assert abs(summary.unknown_value - EXPECTED_UNKNOWN_VALUE) < 0.01, (
        f"Expected unknown value {EXPECTED_UNKNOWN_VALUE}, but got {summary.unknown_value}."
    )

    assert abs(summary.pending_activity_value - EXPECTED_PENDING_ACTIVITY) < 0.01, (
        f"Expected pending activity {EXPECTED_PENDING_ACTIVITY}, but got {summary.pending_activity_value}."
    )

    # Also verify that the component values add up to the total
    component_sum = (
        summary.stock_value
        + summary.option_value
        + summary.cash_value
        + summary.unknown_value
        + summary.pending_activity_value
    )

    assert abs(summary.total_value - component_sum) < 0.01, (
        f"Expected total value {summary.total_value}, but component sum is {component_sum}. "
        f"The portfolio value components don't add up to the total."
    )


@pytest.mark.critical
def test_portfolio_exposure_calculation(test_portfolio_path):
    """
    CRITICAL TEST: Verify that portfolio exposure is correctly calculated.

    This test ensures that the market exposure of the portfolio is correctly calculated
    from the individual position exposures. It specifically checks that the net market
    exposure reported in the portfolio summary matches the sum of all position exposures.

    Failure in this test indicates a serious issue with the exposure calculation logic
    that would result in incorrect risk assessment for users.
    """
    # Load the CSV file
    df = load_portfolio_from_csv(test_portfolio_path)

    # Parse the portfolio holdings
    holdings = parse_portfolio_holdings(df)

    # Process the portfolio
    portfolio = process_portfolio(holdings)

    # Get portfolio exposures
    exposures = get_portfolio_exposures(portfolio)

    # Create portfolio summary
    summary = create_portfolio_summary(portfolio)

    # Hardcoded expected values based on test_portfolio.csv
    # Note: These values were updated after refactoring the caching architecture
    # to remove redundant caching in market_data_provider
    EXPECTED_NET_MARKET_EXPOSURE = 1268209.07
    EXPECTED_NET_EXPOSURE_PCT = 0.4528
    EXPECTED_LONG_STOCK_EXPOSURE = 2373923.53
    EXPECTED_SHORT_STOCK_EXPOSURE = -550212.15
    EXPECTED_LONG_OPTION_EXPOSURE = 1502530.91
    EXPECTED_SHORT_OPTION_EXPOSURE = -2058033.23

    # Verify net market exposure matches expected value
    assert abs(summary.net_market_exposure - EXPECTED_NET_MARKET_EXPOSURE) < 0.01, (
        f"Expected net market exposure {EXPECTED_NET_MARKET_EXPOSURE}, "
        f"but got {summary.net_market_exposure}. "
        f"The portfolio exposure calculation is incorrect."
    )

    # Verify net exposure percentage matches expected value
    assert abs(summary.net_exposure_pct - EXPECTED_NET_EXPOSURE_PCT) < 0.001, (
        f"Expected net exposure percentage {EXPECTED_NET_EXPOSURE_PCT}, "
        f"but got {summary.net_exposure_pct}. "
        f"The net exposure percentage calculation is incorrect."
    )

    # Verify individual exposure components
    assert (
        abs(exposures["long_stock_exposure"] - EXPECTED_LONG_STOCK_EXPOSURE) < 0.01
    ), (
        f"Expected long stock exposure {EXPECTED_LONG_STOCK_EXPOSURE}, "
        f"but got {exposures['long_stock_exposure']}."
    )

    assert (
        abs(exposures["short_stock_exposure"] - EXPECTED_SHORT_STOCK_EXPOSURE) < 0.01
    ), (
        f"Expected short stock exposure {EXPECTED_SHORT_STOCK_EXPOSURE}, "
        f"but got {exposures['short_stock_exposure']}."
    )

    assert (
        abs(exposures["long_option_exposure"] - EXPECTED_LONG_OPTION_EXPOSURE) < 0.01
    ), (
        f"Expected long option exposure {EXPECTED_LONG_OPTION_EXPOSURE}, "
        f"but got {exposures['long_option_exposure']}."
    )

    assert (
        abs(exposures["short_option_exposure"] - EXPECTED_SHORT_OPTION_EXPOSURE) < 0.01
    ), (
        f"Expected short option exposure {EXPECTED_SHORT_OPTION_EXPOSURE}, "
        f"but got {exposures['short_option_exposure']}."
    )


@pytest.mark.critical
def test_portfolio_beta_adjusted_exposure_calculation(test_portfolio_path):
    """
    CRITICAL TEST: Verify that beta-adjusted exposure is correctly calculated.

    This test ensures that the beta-adjusted exposure of the portfolio is correctly
    calculated from the individual position exposures and betas. It specifically checks
    that the beta-adjusted exposure reported in the portfolio summary matches the
    expected calculation.

    Failure in this test indicates a serious issue with the beta-adjusted exposure
    calculation logic that would result in incorrect risk assessment for users.
    """
    # Load the CSV file
    df = load_portfolio_from_csv(test_portfolio_path)

    # Parse the portfolio holdings
    holdings = parse_portfolio_holdings(df)

    # Process the portfolio
    portfolio = process_portfolio(holdings)

    # Get portfolio exposures
    exposures = get_portfolio_exposures(portfolio)

    # Create portfolio summary
    summary = create_portfolio_summary(portfolio)

    # Hardcoded expected value based on test_portfolio.csv
    # Note: This value was updated after refactoring the caching architecture
    # to remove redundant caching in market_data_provider
    EXPECTED_BETA_ADJUSTED_EXPOSURE = 1525631.01

    # Verify beta-adjusted exposure matches expected value
    assert (
        abs(summary.beta_adjusted_exposure - EXPECTED_BETA_ADJUSTED_EXPOSURE) < 0.01
    ), (
        f"Expected beta-adjusted exposure {EXPECTED_BETA_ADJUSTED_EXPOSURE}, "
        f"but got {summary.beta_adjusted_exposure}. "
        f"The portfolio beta-adjusted exposure calculation is incorrect."
    )

    # Also verify that the summary and exposures values match
    assert (
        abs(summary.beta_adjusted_exposure - exposures["beta_adjusted_exposure"]) < 0.01
    ), (
        f"Summary beta-adjusted exposure {summary.beta_adjusted_exposure} doesn't match "
        f"exposures beta-adjusted exposure {exposures['beta_adjusted_exposure']}. "
        f"The portfolio beta-adjusted exposure calculation is inconsistent."
    )


@pytest.mark.critical
def test_portfolio_calculation_consistency(test_portfolio_path):
    """
    CRITICAL TEST: Verify that portfolio calculations are consistent across processing.

    This test ensures that the portfolio calculations are consistent when the portfolio
    is processed multiple times. It specifically checks that the total value, net market
    exposure, and beta-adjusted exposure remain the same across multiple processing runs.

    Failure in this test indicates a serious issue with the portfolio processing logic
    that would result in inconsistent results for users.
    """
    # Load the CSV file
    df = load_portfolio_from_csv(test_portfolio_path)

    # Parse the portfolio holdings
    holdings = parse_portfolio_holdings(df)

    # Process the portfolio twice
    portfolio1 = process_portfolio(holdings)
    summary1 = create_portfolio_summary(portfolio1)

    portfolio2 = process_portfolio(holdings)
    summary2 = create_portfolio_summary(portfolio2)

    # Verify the total values match
    assert abs(summary1.total_value - summary2.total_value) < 0.01, (
        f"Expected consistent total value, but got {summary1.total_value} and {summary2.total_value}. "
        f"The portfolio processing is not consistent."
    )

    # Verify the net market exposures match
    assert abs(summary1.net_market_exposure - summary2.net_market_exposure) < 0.01, (
        f"Expected consistent net market exposure, but got {summary1.net_market_exposure} and {summary2.net_market_exposure}. "
        f"The portfolio processing is not consistent."
    )

    # Verify the beta-adjusted exposures match
    assert (
        abs(summary1.beta_adjusted_exposure - summary2.beta_adjusted_exposure) < 0.01
    ), (
        f"Expected consistent beta-adjusted exposure, but got {summary1.beta_adjusted_exposure} and {summary2.beta_adjusted_exposure}. "
        f"The portfolio processing is not consistent."
    )
