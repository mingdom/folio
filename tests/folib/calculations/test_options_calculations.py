"""Tests for option pricing and Greeks calculations."""

import datetime

import pytest

from src.folib.calculations.options import (
    calculate_implied_volatility,
    calculate_option_delta,
    calculate_option_price,
)


def test_call_option_price():
    """Test call option price calculation."""
    expiry = datetime.date(2026, 1, 1)  # Future date to avoid expiry issues
    price = calculate_option_price(
        option_type="CALL",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        volatility=0.3,
        risk_free_rate=0.05,
    )
    assert price > 0
    assert price < 100.0  # Option can't be worth more than underlying


def test_put_option_price():
    """Test put option price calculation."""
    expiry = datetime.date(2026, 1, 1)
    price = calculate_option_price(
        option_type="PUT",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        volatility=0.3,
        risk_free_rate=0.05,
    )
    assert price > 0
    assert price < 100.0


def test_call_option_delta():
    """Test call option delta calculation."""
    expiry = datetime.date(2026, 1, 1)
    # First calculate the option price with known volatility
    known_vol = 0.3
    price = calculate_option_price(
        option_type="CALL",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        volatility=known_vol,
        risk_free_rate=0.05,
    )
    delta = calculate_option_delta(
        option_type="CALL",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        option_price=price,
        risk_free_rate=0.05,
    )
    assert 0 <= delta <= 1.0  # Call delta between 0 and 1


def test_put_option_delta():
    """Test put option delta calculation."""
    expiry = datetime.date(2026, 1, 1)
    known_vol = 0.3
    price = calculate_option_price(
        option_type="PUT",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        volatility=known_vol,
        risk_free_rate=0.05,
    )
    delta = calculate_option_delta(
        option_type="PUT",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        option_price=price,
        risk_free_rate=0.05,
    )
    assert -1.0 <= delta <= 0  # Put delta between -1 and 0


def test_implied_volatility():
    """Test implied volatility calculation."""
    expiry = datetime.date(2026, 1, 1)

    # First get a price for a known volatility
    known_vol = 0.3
    price = calculate_option_price(
        option_type="CALL",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        volatility=known_vol,
    )

    # Then solve for implied vol using that price
    implied_vol = calculate_implied_volatility(
        option_type="CALL",
        strike=100.0,
        expiry=expiry,
        underlying_price=100.0,
        option_price=price,
    )

    assert abs(implied_vol - known_vol) < 0.001  # Should recover same volatility


def test_option_price_at_expiry():
    """Test option price calculation at expiry."""
    today = datetime.date.today()

    # Deep in the money call
    price = calculate_option_price(
        option_type="CALL",
        strike=90.0,
        expiry=today,
        underlying_price=100.0,
    )
    assert abs(price - 10.0) < 0.1  # Should be close to intrinsic value

    # Deep out of the money put
    price = calculate_option_price(
        option_type="PUT",
        strike=90.0,
        expiry=today,
        underlying_price=100.0,
    )
    assert price < 0.1  # Should be nearly worthless


def test_invalid_inputs():
    """Test error handling for invalid inputs."""
    expiry = datetime.date(2026, 1, 1)

    with pytest.raises(ValueError):
        calculate_option_price(
            option_type="INVALID",  # type: ignore
            strike=100.0,
            expiry=expiry,
            underlying_price=100.0,
        )

    with pytest.raises(ValueError):
        calculate_option_delta(
            option_type="CALL",
            strike=-100.0,  # Invalid negative strike
            expiry=expiry,
            underlying_price=100.0,
            option_price=1.0,  # Dummy positive price
        )

    with pytest.raises(ValueError):
        calculate_implied_volatility(
            option_type="CALL",
            strike=100.0,
            expiry=expiry,
            underlying_price=100.0,
            option_price=-1.0,  # Invalid negative price
        )


def test_expired_option():
    """Test handling of expired and today-expiry options."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Test expired option (yesterday)
    price = calculate_option_price(
        option_type="CALL",
        strike=100.0,
        expiry=yesterday,
        underlying_price=100.0,
    )
    assert price == 0.0  # Expired option should have zero price

    delta = calculate_option_delta(
        option_type="CALL",
        strike=100.0,
        expiry=yesterday,
        underlying_price=100.0,
        option_price=1.0,
    )
    assert delta == 0.0  # Expired option should have zero delta

    vol = calculate_implied_volatility(
        option_type="CALL",
        strike=100.0,
        expiry=yesterday,
        underlying_price=100.0,
        option_price=1.0,
    )
    assert vol == 0.3  # Expired option should return DEFAULT_VOLATILITY

    # Test today-expiring option (should be valid but may have warnings)
    price = calculate_option_price(
        option_type="CALL",
        strike=90.0,
        expiry=today,
        underlying_price=100.0,
    )
    assert abs(price - 10.0) < 0.1  # Should be close to intrinsic value

    delta = calculate_option_delta(
        option_type="CALL",
        strike=90.0,
        expiry=today,
        underlying_price=100.0,
        option_price=price,
    )
    assert 0.0 <= delta <= 1.0  # Should still have valid delta

    vol = calculate_implied_volatility(
        option_type="CALL",
        strike=90.0,
        expiry=today,
        underlying_price=100.0,
        option_price=price,
    )
    assert vol > 0.0  # Should be able to calculate meaningful vol for intrinsic value
