"""
Tests for options.py
"""

import datetime

import pytest

from src.folio.options import (
    OptionContract,
    calculate_black_scholes_delta,
    calculate_bs_price,
    calculate_implied_volatility,
    parse_option_description,
)


def create_test_option(
    option_type="CALL",
    days_to_expiry=30,
    strike=100,
    underlying_price=100,
):
    """Create a test option position."""
    expiry = datetime.datetime.now() + datetime.timedelta(days=days_to_expiry)
    return OptionContract(
        underlying="TEST",
        expiry=expiry,
        strike=strike,
        option_type=option_type,
        quantity=1,
        current_price=5.0,
        description=f"TEST {expiry.strftime('%b').upper()} {expiry.day} {expiry.year} ${strike} {option_type}",
    )


def test_calculate_black_scholes_delta():
    """Test delta calculation."""
    # ATM call should have delta around 0.5
    call_option = create_test_option(option_type="CALL", strike=100)
    delta = calculate_black_scholes_delta(call_option, 100, volatility=0.3)
    assert 0.45 < delta < 0.55

    # ATM put should have delta around -0.5
    put_option = create_test_option(option_type="PUT", strike=100)
    delta = calculate_black_scholes_delta(put_option, 100, volatility=0.3)
    assert -0.55 < delta < -0.45

    # ITM call should have delta > 0.5
    itm_call = create_test_option(option_type="CALL", strike=90)
    delta = calculate_black_scholes_delta(itm_call, 100, volatility=0.3)
    assert delta > 0.5

    # OTM call should have delta < 0.5
    otm_call = create_test_option(option_type="CALL", strike=110)
    delta = calculate_black_scholes_delta(otm_call, 100, volatility=0.3)
    assert delta < 0.5


def test_calculate_bs_price():
    """Test price calculation."""
    # ATM call with 30 days to expiry
    call_option = create_test_option(option_type="CALL", strike=100, days_to_expiry=30)
    price = calculate_bs_price(call_option, 100, volatility=0.3)
    assert 3 < price < 6  # Reasonable range for ATM call

    # Deep ITM call should be worth close to intrinsic value
    deep_itm_call = create_test_option(option_type="CALL", strike=80, days_to_expiry=30)
    price = calculate_bs_price(deep_itm_call, 100, volatility=0.3)
    assert 19 < price < 22  # Intrinsic value is 20, plus some time value

    # Deep OTM call should be worth very little
    deep_otm_call = create_test_option(
        option_type="CALL", strike=150, days_to_expiry=30
    )
    price = calculate_bs_price(deep_otm_call, 100, volatility=0.3)
    assert price < 1  # Very little value


def test_calculate_implied_volatility():
    """Test implied volatility calculation."""
    # Create an option with known parameters
    option = create_test_option(option_type="CALL", strike=100, days_to_expiry=30)

    # Calculate price with known volatility
    known_vol = 0.3
    price = calculate_bs_price(option, 100, volatility=known_vol)

    # Calculate implied volatility from that price
    implied_vol = calculate_implied_volatility(option, 100, price)

    # Should recover the original volatility
    assert abs(implied_vol - known_vol) < 0.01


def test_parse_option_description():
    """Test option description parsing."""
    description = "AAPL JAN 15 2023 $150 CALL"
    result = parse_option_description(description)

    assert result["underlying"] == "AAPL"
    assert result["expiry"] == datetime.datetime(2023, 1, 15)
    assert result["strike"] == 150
    assert result["option_type"] == "CALL"

    # Test invalid format
    with pytest.raises(ValueError):
        parse_option_description("AAPL CALL")

    # Test invalid strike
    with pytest.raises(ValueError):
        parse_option_description("AAPL JAN 15 2023 150 CALL")

    # Test invalid month
    with pytest.raises(ValueError):
        parse_option_description("AAPL FOO 15 2023 $150 CALL")
