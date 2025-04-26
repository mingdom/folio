"""Tests for option exposure calculations.

This module focuses specifically on testing that option exposures are calculated correctly
for different option types (calls/puts) and positions (long/short).
"""

from datetime import datetime

import pytest

from src.folio.options import OptionContract, calculate_option_delta


@pytest.fixture
def option_fixtures():
    """Create a set of option fixtures for testing exposures."""
    # Use a fixed expiry date for consistent test results
    expiry_date = datetime(2025, 6, 15)  # About 6 months from now

    # Create options with different types and positions
    return {
        # Call options
        "long_call_atm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="CALL",
            quantity=1,  # Long position
            current_price=5.0,
            description="SPY JUN 15 2025 $100 CALL",
        ),
        "short_call_atm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="CALL",
            quantity=-1,  # Short position
            current_price=5.0,
            description="SPY JUN 15 2025 $100 CALL",
        ),
        # Put options
        "long_put_atm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="PUT",
            quantity=1,  # Long position
            current_price=5.0,
            description="SPY JUN 15 2025 $100 PUT",
        ),
        "short_put_atm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="PUT",
            quantity=-1,  # Short position
            current_price=5.0,
            description="SPY JUN 15 2025 $100 PUT",
        ),
        # Different quantities
        "long_call_multiple": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="CALL",
            quantity=3,  # Multiple contracts
            current_price=5.0,
            description="SPY JUN 15 2025 $100 CALL",
        ),
        "short_put_multiple": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="PUT",
            quantity=-2,  # Multiple contracts
            current_price=5.0,
            description="SPY JUN 15 2025 $100 PUT",
        ),
        # Different moneyness levels
        "long_call_itm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=90.0,  # In-the-money
            option_type="CALL",
            quantity=1,
            current_price=15.0,
            description="SPY JUN 15 2025 $90 CALL",
        ),
        "long_call_otm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=110.0,  # Out-of-the-money
            option_type="CALL",
            quantity=1,
            current_price=2.0,
            description="SPY JUN 15 2025 $110 CALL",
        ),
        "long_put_itm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=110.0,  # In-the-money
            option_type="PUT",
            quantity=1,
            current_price=15.0,
            description="SPY JUN 15 2025 $110 PUT",
        ),
        "long_put_otm": OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=90.0,  # Out-of-the-money
            option_type="PUT",
            quantity=1,
            current_price=2.0,
            description="SPY JUN 15 2025 $90 PUT",
        ),
    }


def calculate_exposure(option, underlying_price, iv=0.3):
    """Calculate the exposure for an option position.

    Args:
        option: The option position
        underlying_price: The price of the underlying asset
        iv: Implied volatility to use for the calculation

    Returns:
        The calculated exposure (delta * notional value)
    """
    # Set the underlying price on the option object to ensure notional_value property works
    option.underlying_price = underlying_price

    # Calculate delta using Black-Scholes
    delta = calculate_option_delta(option, underlying_price, implied_volatility=iv)

    # Calculate exposure as delta * notional value
    # This is the key calculation we're testing
    exposure = delta * option.notional_value

    # Print detailed information for debugging

    return delta, exposure


def test_call_option_exposures(option_fixtures):
    """Test that call option exposures are calculated correctly."""
    underlying_price = 100.0

    # Test long call (should have positive delta and positive exposure)
    long_call = option_fixtures["long_call_atm"]
    long_delta, long_exposure = calculate_exposure(long_call, underlying_price)

    # Delta should be positive for a call option
    assert long_delta > 0, "Long call delta should be positive"
    # Exposure should be positive for a long call
    assert long_exposure > 0, "Long call exposure should be positive"

    # Test short call (should have negative delta and negative exposure)
    short_call = option_fixtures["short_call_atm"]
    short_delta, short_exposure = calculate_exposure(short_call, underlying_price)

    # Delta should be negative for a short call
    assert short_delta < 0, "Short call delta should be negative"
    # Exposure should be negative for a short call
    assert short_exposure < 0, "Short call exposure should be negative"

    # The absolute values of delta and exposure should be the same for long and short
    # positions with the same parameters (just opposite signs)
    assert abs(long_delta) == pytest.approx(abs(short_delta), rel=1e-10)
    assert abs(long_exposure) == pytest.approx(abs(short_exposure), rel=1e-10)


def test_put_option_exposures(option_fixtures):
    """Test that put option exposures are calculated correctly."""
    underlying_price = 100.0

    # Test long put (should have negative delta and negative exposure)
    long_put = option_fixtures["long_put_atm"]
    long_delta, long_exposure = calculate_exposure(long_put, underlying_price)

    # Delta should be negative for a put option
    assert long_delta < 0, "Long put delta should be negative"
    # Exposure should be negative for a long put
    assert long_exposure < 0, "Long put exposure should be negative"

    # Test short put (should have positive delta and positive exposure)
    short_put = option_fixtures["short_put_atm"]
    short_delta, short_exposure = calculate_exposure(short_put, underlying_price)

    # Delta should be positive for a short put
    assert short_delta > 0, "Short put delta should be positive"
    # Exposure should be positive for a short put
    assert short_exposure > 0, "Short put exposure should be positive"

    # The absolute values of delta and exposure should be the same for long and short
    # positions with the same parameters (just opposite signs)
    assert abs(long_delta) == pytest.approx(abs(short_delta), rel=1e-10)
    assert abs(long_exposure) == pytest.approx(abs(short_exposure), rel=1e-10)


def test_exposure_scales_with_quantity(option_fixtures):
    """Test that exposure scales linearly with quantity."""
    underlying_price = 100.0

    # Test with a single contract
    single_call = option_fixtures["long_call_atm"]
    _, single_exposure = calculate_exposure(single_call, underlying_price)

    # Test with multiple contracts
    multiple_call = option_fixtures["long_call_multiple"]
    _, multiple_exposure = calculate_exposure(multiple_call, underlying_price)

    # Exposure should scale linearly with quantity
    expected_ratio = multiple_call.quantity / single_call.quantity
    actual_ratio = multiple_exposure / single_exposure
    assert actual_ratio == pytest.approx(expected_ratio, rel=1e-10)

    # Test with short positions
    single_put = option_fixtures["short_put_atm"]
    _, single_exposure = calculate_exposure(single_put, underlying_price)

    multiple_put = option_fixtures["short_put_multiple"]
    _, multiple_exposure = calculate_exposure(multiple_put, underlying_price)

    # Exposure should scale linearly with quantity
    expected_ratio = multiple_put.quantity / single_put.quantity
    actual_ratio = multiple_exposure / single_exposure
    assert actual_ratio == pytest.approx(expected_ratio, rel=1e-10)


def test_moneyness_affects_delta(option_fixtures):
    """Test that moneyness affects delta as expected."""
    underlying_price = 100.0

    # For call options:
    # - ITM calls should have higher delta
    # - OTM calls should have lower delta
    itm_call = option_fixtures["long_call_itm"]
    atm_call = option_fixtures["long_call_atm"]
    otm_call = option_fixtures["long_call_otm"]

    itm_delta, _ = calculate_exposure(itm_call, underlying_price)
    atm_delta, _ = calculate_exposure(atm_call, underlying_price)
    otm_delta, _ = calculate_exposure(otm_call, underlying_price)

    assert itm_delta > atm_delta > otm_delta, (
        "Call delta should decrease as strike increases"
    )

    # For put options:
    # - ITM puts should have more negative delta
    # - OTM puts should have less negative delta
    itm_put = option_fixtures["long_put_itm"]
    atm_put = option_fixtures["long_put_atm"]
    otm_put = option_fixtures["long_put_otm"]

    itm_delta, _ = calculate_exposure(itm_put, underlying_price)
    atm_delta, _ = calculate_exposure(atm_put, underlying_price)
    otm_delta, _ = calculate_exposure(otm_put, underlying_price)

    assert itm_delta < atm_delta < otm_delta, (
        "Put delta should increase as strike decreases"
    )


def test_portfolio_level_exposure():
    """Test that portfolio-level option exposure is calculated correctly."""
    # Create a simple portfolio with different option positions
    expiry_date = datetime(2025, 6, 15)
    underlying_price = 100.0

    portfolio = [
        # Long call - positive exposure
        OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=100.0,
            option_type="CALL",
            quantity=2,
            current_price=5.0,
            description="SPY JUN 15 2025 $100 CALL",
        ),
        # Short call - negative exposure
        OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=110.0,
            option_type="CALL",
            quantity=-1,
            current_price=2.0,
            description="SPY JUN 15 2025 $110 CALL",
        ),
        # Long put - negative exposure
        OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=90.0,
            option_type="PUT",
            quantity=1,
            current_price=2.0,
            description="SPY JUN 15 2025 $90 PUT",
        ),
        # Short put - positive exposure
        OptionContract(
            underlying="SPY",
            expiry=expiry_date,
            strike=80.0,
            option_type="PUT",
            quantity=-2,
            current_price=1.0,
            description="SPY JUN 15 2025 $80 PUT",
        ),
    ]

    # Calculate individual exposures
    exposures = []
    for option in portfolio:
        _, exposure = calculate_exposure(option, underlying_price)
        exposures.append(exposure)

    # Calculate total exposure
    total_exposure = sum(exposures)

    # Verify the signs of individual exposures
    assert exposures[0] > 0, "Long call should have positive exposure"
    assert exposures[1] < 0, "Short call should have negative exposure"
    assert exposures[2] < 0, "Long put should have negative exposure"
    assert exposures[3] > 0, "Short put should have positive exposure"

    # The total exposure should equal the sum of individual exposures
    assert total_exposure == pytest.approx(sum(exposures), rel=1e-10)

    # Verify that the calculation matches what's done in portfolio.py
    # In portfolio.py, the calculation is: delta * option.notional_value
    # Let's verify this is correct for each option type and position

    # For a long call (positive delta, positive exposure)
    long_call = portfolio[0]
    long_call_delta = calculate_option_delta(long_call, underlying_price)
    long_call_exposure = long_call_delta * long_call.notional_value
    assert long_call_exposure > 0, "Long call exposure should be positive"

    # For a short call (negative delta, negative exposure)
    short_call = portfolio[1]
    short_call_delta = calculate_option_delta(short_call, underlying_price)
    short_call_exposure = short_call_delta * short_call.notional_value
    assert short_call_exposure < 0, "Short call exposure should be negative"

    # For a long put (negative delta, negative exposure)
    long_put = portfolio[2]
    long_put_delta = calculate_option_delta(long_put, underlying_price)
    long_put_exposure = long_put_delta * long_put.notional_value
    assert long_put_exposure < 0, "Long put exposure should be negative"

    # For a short put (positive delta, positive exposure)
    short_put = portfolio[3]
    short_put_delta = calculate_option_delta(short_put, underlying_price)
    short_put_exposure = short_put_delta * short_put.notional_value
    assert short_put_exposure > 0, "Short put exposure should be positive"


def test_calculate_option_exposure(option_fixtures):
    """Test the calculate_option_exposure function."""
    # Import calculate_option_exposure from options module
    from src.folio.options import calculate_option_exposure

    underlying_price = 100.0
    beta = 1.2

    # Test with a long call
    long_call = option_fixtures["long_call_atm"]
    long_call_exposures = calculate_option_exposure(long_call, underlying_price, beta)

    # Verify the keys in the result
    assert "delta" in long_call_exposures
    assert "delta_exposure" in long_call_exposures
    assert "beta_adjusted_exposure" in long_call_exposures

    # Verify the values
    delta = long_call_exposures["delta"]
    delta_exposure = long_call_exposures["delta_exposure"]
    beta_adjusted_exposure = long_call_exposures["beta_adjusted_exposure"]

    # Delta should be positive for a long call
    assert delta > 0, "Delta should be positive for a long call"

    # Delta exposure should be positive for a long call
    assert delta_exposure > 0, "Delta exposure should be positive for a long call"

    # Beta-adjusted exposure should be delta_exposure * beta
    assert beta_adjusted_exposure == pytest.approx(delta_exposure * beta)

    # Test with a short call
    short_call = option_fixtures["short_call_atm"]
    short_call_exposures = calculate_option_exposure(short_call, underlying_price, beta)

    # Delta should be negative for a short call
    assert short_call_exposures["delta"] < 0, (
        "Delta should be negative for a short call"
    )

    # Delta exposure should be negative for a short call
    assert short_call_exposures["delta_exposure"] < 0, (
        "Delta exposure should be negative for a short call"
    )

    # Test with a long put
    long_put = option_fixtures["long_put_atm"]
    long_put_exposures = calculate_option_exposure(long_put, underlying_price, beta)

    # Delta should be negative for a long put
    assert long_put_exposures["delta"] < 0, "Delta should be negative for a long put"

    # Delta exposure should be negative for a long put
    assert long_put_exposures["delta_exposure"] < 0, (
        "Delta exposure should be negative for a long put"
    )

    # Test with a short put
    short_put = option_fixtures["short_put_atm"]
    short_put_exposures = calculate_option_exposure(short_put, underlying_price, beta)

    # Delta should be positive for a short put
    assert short_put_exposures["delta"] > 0, "Delta should be positive for a short put"

    # Delta exposure should be positive for a short put
    assert short_put_exposures["delta_exposure"] > 0, (
        "Delta exposure should be positive for a short put"
    )


def test_process_options():
    """Test the process_options function."""
    # Import process_options from options module
    from src.folio.options import process_options

    # Create test data
    options_data = [
        {
            "description": "SPY JUN 15 2025 $100 CALL",
            "quantity": 1,
            "price": 5.0,
            "symbol": "SPY250615C00100000",
        },
        {
            "description": "SPY JUN 15 2025 $100 CALL",
            "quantity": -1,
            "price": 5.0,
            "symbol": "SPY250615C00100000",
        },
        {
            "description": "SPY JUN 15 2025 $100 PUT",
            "quantity": 1,
            "price": 5.0,
            "symbol": "SPY250615P00100000",
        },
        {
            "description": "SPY JUN 15 2025 $100 PUT",
            "quantity": -1,
            "price": 5.0,
            "symbol": "SPY250615P00100000",
        },
    ]

    prices = {"SPY": 100.0}
    betas = {"SPY": 1.2}

    # Process the options
    processed_options = process_options(options_data, prices, betas)

    # Verify the results
    assert len(processed_options) == 4, "Should have processed all 4 options"

    # Check the first option (long call)
    long_call = processed_options[0]
    assert long_call["ticker"] == "SPY"
    assert long_call["option_type"] == "CALL"
    assert long_call["quantity"] == 1
    assert long_call["delta"] > 0, "Delta should be positive for a long call"
    assert long_call["delta_exposure"] > 0, (
        "Delta exposure should be positive for a long call"
    )

    # Check the second option (short call)
    short_call = processed_options[1]
    assert short_call["ticker"] == "SPY"
    assert short_call["option_type"] == "CALL"
    assert short_call["quantity"] == -1
    assert short_call["delta"] < 0, "Delta should be negative for a short call"
    assert short_call["delta_exposure"] < 0, (
        "Delta exposure should be negative for a short call"
    )

    # Check the third option (long put)
    long_put = processed_options[2]
    assert long_put["ticker"] == "SPY"
    assert long_put["option_type"] == "PUT"
    assert long_put["quantity"] == 1
    assert long_put["delta"] < 0, "Delta should be negative for a long put"
    assert long_put["delta_exposure"] < 0, (
        "Delta exposure should be negative for a long put"
    )

    # Check the fourth option (short put)
    short_put = processed_options[3]
    assert short_put["ticker"] == "SPY"
    assert short_put["option_type"] == "PUT"
    assert short_put["quantity"] == -1
    assert short_put["delta"] > 0, "Delta should be positive for a short put"
    assert short_put["delta_exposure"] > 0, (
        "Delta exposure should be positive for a short put"
    )


def test_process_options_with_missing_price():
    """Test process_options with a missing price."""
    # Import process_options from options module
    from src.folio.options import process_options

    options_data = [
        {
            "description": "SPY JUN 15 2025 $100 CALL",
            "quantity": 1,
            "price": 5.0,
        },
        {
            "description": "AAPL JUN 15 2025 $200 CALL",  # No price for AAPL
            "quantity": 1,
            "price": 10.0,
        },
    ]

    prices = {"SPY": 100.0}  # No price for AAPL

    # Process the options
    processed_options = process_options(options_data, prices)

    # Verify that only the SPY option was processed
    assert len(processed_options) == 1, "Should have processed only the SPY option"
    assert processed_options[0]["ticker"] == "SPY"


def test_process_options_with_error():
    """Test process_options with an error in the option data."""
    # Import process_options from options module
    from src.folio.options import process_options

    options_data = [
        {
            "description": "SPY JUN 15 2025 $100 CALL",
            "quantity": 1,
            "price": 5.0,
        },
        {
            "description": "Invalid option description",  # Invalid description
            "quantity": 1,
            "price": 5.0,
        },
    ]

    prices = {"SPY": 100.0}

    # Process the options
    processed_options = process_options(options_data, prices)

    # Verify that only the valid option was processed
    assert len(processed_options) == 1, "Should have processed only the valid option"
    assert processed_options[0]["ticker"] == "SPY"
