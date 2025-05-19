"""Tests for option pricing and Greeks calculations."""

import datetime
from unittest.mock import patch

import pytest

from src.folib.calculations.options import (
    calculate_implied_volatility,
    calculate_option_delta,
    calculate_option_price,
    OptionCalculationError, # Import the custom exception
    MIN_VOLATILITY,
    STANDARD_CALC_MAX_VOL,
    DEFAULT_VOLATILITY
)

# Common calculation date for tests to ensure reproducibility
CALC_DATE = datetime.date(2024, 1, 16)

def test_call_option_price():
    """Test call option price calculation."""
    expiry = datetime.date(2026, 1, 1)
    price = calculate_option_price(
        option_type="CALL",
        strike=100.0,
        expiry_py=expiry,
        underlying_price=100.0,
        calculation_date_py=CALC_DATE,
        volatility=0.3,
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    assert price > 0
    # Option can't be worth more than underlying (for American call without dividends, this is true)
    # but for European or with dividends, this might not hold strictly.
    # For a standard call, price should be less than underlying.
    assert price < 100.0


def test_put_option_price():
    """Test put option price calculation."""
    expiry = datetime.date(2026, 1, 1)
    price = calculate_option_price(
        option_type="PUT",
        strike=100.0,
        expiry_py=expiry,
        underlying_price=100.0,
        calculation_date_py=CALC_DATE,
        volatility=0.3,
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    assert price > 0
    # Option can't be worth more than strike price
    assert price < 100.0


def test_call_option_delta():
    """Test call option delta calculation."""
    expiry = datetime.date(2026, 1, 1)
    delta = calculate_option_delta(
        option_type="CALL",
        strike=100.0,
        expiry_py=expiry,
        underlying_price=100.0,
        calculation_date_py=CALC_DATE,
        volatility=0.3,
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    assert 0 <= delta <= 1.0  # Call delta between 0 and 1


def test_put_option_delta():
    """Test put option delta calculation."""
    expiry = datetime.date(2026, 1, 1)
    delta = calculate_option_delta(
        option_type="PUT",
        strike=100.0,
        expiry_py=expiry,
        underlying_price=100.0,
        calculation_date_py=CALC_DATE,
        volatility=0.3,
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    assert -1.0 <= delta <= 0  # Put delta between -1 and 0


def test_implied_volatility_standard_case():
    """Test implied volatility calculation for a standard case."""
    expiry = datetime.date(2026, 1, 1)
    known_vol = 0.3
    # Need to provide all new args, including calculation_date_py
    price = calculate_option_price(
        option_type="CALL",
        strike=100.0,
        expiry_py=expiry,
        underlying_price=100.0,
        calculation_date_py=CALC_DATE, # Use fixed calc date
        volatility=known_vol,
        risk_free_rate=0.05,
        dividend_yield=0.0
    )

    implied_vol = calculate_implied_volatility(
        option_type="CALL",
        strike_price=100.0,
        expiration_date=expiry,
        underlying_price=100.0,
        option_price=price,
        calculation_date_py=CALC_DATE, # Use fixed calc date
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    # Increased tolerance slightly due to potential numerical precision differences
    # with the more complex IV logic and multiple QL calls.
    assert abs(implied_vol - known_vol) < 0.01


def test_option_price_at_expiry():
    """Test option price calculation at expiry."""
    # For at expiry, calculation_date_py should be the same as expiry_py
    at_expiry_date = datetime.date(2024, 1, 16)

    # Deep in the money call
    price_call = calculate_option_price(
        option_type="CALL",
        strike=90.0,
        expiry_py=at_expiry_date,
        underlying_price=100.0,
        calculation_date_py=at_expiry_date,
        volatility=0.3, # Volatility doesn't matter at expiry for price
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    assert abs(price_call - 10.0) < 0.0001  # Should be intrinsic value

    # Deep out of the money put
    price_put = calculate_option_price(
        option_type="PUT",
        strike=90.0,
        expiry_py=at_expiry_date,
        underlying_price=100.0,
        calculation_date_py=at_expiry_date,
        volatility=0.3,
        risk_free_rate=0.05,
        dividend_yield=0.0
    )
    assert abs(price_put - 0.0) < 0.0001  # Should be zero


def test_invalid_inputs_errors():
    """Test error handling for invalid inputs raises OptionCalculationError."""
    expiry = datetime.date(2026, 1, 1)
    calc_date = datetime.date(2024, 1, 1) # Ensure calc_date is before expiry

    with pytest.raises(OptionCalculationError, match="Invalid option_type"):
        calculate_option_price( # Test with calculate_option_price, adaptable to others
            option_type="INVALID",  # type: ignore
            strike=100.0,
            expiry_py=expiry,
            underlying_price=100.0,
            calculation_date_py=calc_date,
            volatility=0.2,
        )

    with pytest.raises(OptionCalculationError, match="Invalid strike price"):
        calculate_option_delta(
            option_type="CALL",
            strike=-100.0,
            expiry_py=expiry,
            underlying_price=100.0,
            calculation_date_py=calc_date,
            volatility=0.2,
        )
    
    with pytest.raises(OptionCalculationError, match="Invalid option price.*non-negative"):
        calculate_implied_volatility(
            option_type="CALL",
            strike_price=100.0,
            expiration_date=expiry,
            underlying_price=100.0,
            option_price=-1.0,
            calculation_date_py=calc_date,
        )

    with pytest.raises(OptionCalculationError, match="cannot be zero for unexpired option"):
        calculate_implied_volatility(
            option_type="CALL",
            strike_price=100.0,
            expiration_date=expiry, # Unexpired
            underlying_price=100.0,
            option_price=0.0, # Zero price for unexpired
            calculation_date_py=calc_date,
        )
    
    with pytest.raises(OptionCalculationError, match="Expiry date .* cannot be before calculation date"):
        calculate_implied_volatility(
            option_type="CALL",
            strike_price=100.0,
            expiration_date=datetime.date(2023,12,31), # Expired relative to CALC_DATE
            underlying_price=100.0,
            option_price=1.0,
            calculation_date_py=CALC_DATE, # CALC_DATE is 2024-01-16
        )

# --- New Tests for Implied Volatility Logic ---

def test_implied_volatility_deep_itm_low_iv_scenario():
    """Test IV for deep ITM call option with low time value (User's Scenario)."""
    # strike=50.0, underlying=92.46, option_price=43.3, expiry='2026-01-16'
    # calculation_date='2024-01-16'
    # Intrinsic value: 92.46 - 50.0 = 42.46
    # Option price: 43.3
    # Time value: 43.3 - 42.46 = 0.84
    # (Time value / option_price) = 0.84 / 43.3 = 0.01939... which is < 0.02
    # This should trigger the first attempt (deep ITM) and likely result in MIN_VOLATILITY
    # if QuantLib struggles with such a low time value relative to price.
    
    iv = calculate_implied_volatility(
        option_type="CALL",
        strike_price=50.0,
        expiration_date=datetime.date(2026, 1, 16),
        underlying_price=92.46,
        option_price=43.3,
        calculation_date_py=CALC_DATE, # 2024-01-16
        risk_free_rate=0.05,
        dividend_yield=0.0,
    )
    # The logic for "root not bracketed" when f[a] and f[b] are positive (for deep ITM)
    # returns MIN_VOLATILITY.
    assert iv == MIN_VOLATILITY, f"Expected MIN_VOLATILITY, got {iv}"


def test_implied_volatility_arbitrage_condition():
    """Test IV calculation when option_price < intrinsic_value."""
    expiry = datetime.date(2026, 1, 1)
    with pytest.raises(OptionCalculationError, match="less than its intrinsic value"):
        calculate_implied_volatility(
            option_type="CALL",
            strike_price=50.0,
            expiration_date=expiry,
            underlying_price=60.0,  # Intrinsic value = 10.0
            option_price=9.0,       # Price < Intrinsic
            calculation_date_py=CALC_DATE,
            risk_free_rate=0.05,
            dividend_yield=0.0,
        )

def test_implied_volatility_exact_intrinsic_value():
    """Test IV calculation when option_price == intrinsic_value (unexpired)."""
    expiry = datetime.date(2026, 1, 1) # Unexpired
    iv = calculate_implied_volatility(
        option_type="CALL",
        strike_price=50.0,
        expiration_date=expiry,
        underlying_price=60.0,  # Intrinsic value = 10.0
        option_price=10.0,      # Price == Intrinsic
        calculation_date_py=CALC_DATE,
        risk_free_rate=0.05,
        dividend_yield=0.0,
    )
    assert iv == MIN_VOLATILITY

def test_implied_volatility_at_expiry_exact_intrinsic():
    """Test IV for an option at expiry where price equals intrinsic value."""
    iv = calculate_implied_volatility(
        option_type="CALL",
        strike_price=100.0,
        expiration_date=CALC_DATE, # At expiry
        underlying_price=105.0,   # Intrinsic = 5.0
        option_price=5.0,
        calculation_date_py=CALC_DATE,
        risk_free_rate=0.05,
        dividend_yield=0.0,
    )
    assert iv == MIN_VOLATILITY

def test_implied_volatility_at_expiry_mispriced():
    """Test IV for an option at expiry where price NOT equals intrinsic value."""
    iv = calculate_implied_volatility(
        option_type="CALL",
        strike_price=100.0,
        expiration_date=CALC_DATE, # At expiry
        underlying_price=105.0,   # Intrinsic = 5.0
        option_price=6.0,         # Mispriced
        calculation_date_py=CALC_DATE,
        risk_free_rate=0.05,
        dividend_yield=0.0,
    )
    assert iv == DEFAULT_VOLATILITY # Falls back to DEFAULT_VOLATILITY

# Testing the high IV capping is tricky as it depends on QuantLib's internal solver's
# behavior and the specific error message parsing.
# A more direct way to test the capping logic path is to mock _parse_ql_root_not_bracketed_error.
@patch('src.folib.calculations.options._parse_ql_root_not_bracketed_error')
def test_implied_volatility_high_iv_capping(mock_parse_error):
    """Test IV calculation is capped at STANDARD_CALC_MAX_VOL if QL error suggests very high IV."""
    
    # Configure the mock to simulate QuantLib's f[min_vol] and f[max_vol] both being negative,
    # which indicates the true IV is likely > STANDARD_CALC_MAX_VOL.
    # This mock will be invoked during the second (standard) IV calculation attempt.
    mock_parse_error.return_value = (-0.5, -0.1) # Both negative -> suggests IV > max_vol search range

    expiry = datetime.date(2024, 1, 21) # Short DTE, e.g., 5 days from CALC_DATE
    strike = 100.0
    underlying = 101.0
    # Price it relatively high for an OTM option to suggest high IV.
    # The actual price here is less important than tricking the logic via the mock.
    # We need a price that is > intrinsic value to pass initial checks.
    option_price_high_iv_suggested = 2.0 # Intrinsic is 1.0 for call

    iv = calculate_implied_volatility(
        option_type="CALL",
        strike_price=strike,
        expiration_date=expiry,
        underlying_price=underlying,
        option_price=option_price_high_iv_suggested,
        calculation_date_py=CALC_DATE, # 2024-01-16
        risk_free_rate=0.05,
        dividend_yield=0.0,
    )
    
    assert iv == STANDARD_CALC_MAX_VOL
    mock_parse_error.assert_called_once() # Ensure our mock was actually used as expected.

@patch('src.folib.calculations.options._parse_ql_root_not_bracketed_error')
def test_implied_volatility_low_iv_floor_from_standard_error(mock_parse_error):
    """Test IV calculation hits MIN_VOLATILITY if QL error suggests very low IV during standard."""
    mock_parse_error.return_value = (0.1, 0.05) # Both positive -> suggests IV < min_vol search range

    expiry = datetime.date(2025, 1, 16) 
    strike = 100.0
    underlying = 100.0
    # Price it very close to intrinsic to suggest low IV.
    option_price_low_iv_suggested = 0.1 # Intrinsic is 0.0 for ATM call

    iv = calculate_implied_volatility(
        option_type="CALL",
        strike_price=strike,
        expiration_date=expiry,
        underlying_price=underlying,
        option_price=option_price_low_iv_suggested,
        calculation_date_py=CALC_DATE, 
        risk_free_rate=0.05,
        dividend_yield=0.0,
    )
    
    assert iv == MIN_VOLATILITY
    mock_parse_error.assert_called_once()

def test_calculate_option_delta_at_expiry():
    """Test delta calculation for options at expiry."""
    expiry_date = CALC_DATE # Option expires on calculation date

    # ITM Call
    delta_itm_call = calculate_option_delta("CALL", 90, expiry_date, 100, CALC_DATE, 0.2)
    assert delta_itm_call == 1.0

    # OTM Call
    delta_otm_call = calculate_option_delta("CALL", 110, expiry_date, 100, CALC_DATE, 0.2)
    assert delta_otm_call == 0.0

    # ITM Put
    delta_itm_put = calculate_option_delta("PUT", 110, expiry_date, 100, CALC_DATE, 0.2)
    assert delta_itm_put == -1.0

    # OTM Put
    delta_otm_put = calculate_option_delta("PUT", 90, expiry_date, 100, CALC_DATE, 0.2)
    assert delta_otm_put == 0.0

def test_calculate_option_delta_low_volatility_approximations():
    """Test delta approximations for very low volatility."""
    expiry = datetime.date(2025, 1, 16)
    low_vol = 0.00001 # Extremely low volatility, below MIN_VOL_FOR_DELTA_CALC (0.001)

    # Near the money call - should use heuristic
    delta_ntm_call = calculate_option_delta("CALL", 100, expiry, 100.1, CALC_DATE, low_vol)
    assert delta_ntm_call == 0.5

    # Deep ITM call
    delta_ditm_call = calculate_option_delta("CALL", 80, expiry, 100, CALC_DATE, low_vol) # 100 > 80 * 1.1 (88)
    assert delta_ditm_call == 1.0

    # Deep OTM call
    delta_dotm_call = calculate_option_delta("CALL", 120, expiry, 100, CALC_DATE, low_vol) # 100 < 120 * 0.9 (108)
    assert delta_dotm_call == 0.0

    # Near the money put - should use heuristic
    delta_ntm_put = calculate_option_delta("PUT", 100, expiry, 99.9, CALC_DATE, low_vol)
    assert delta_ntm_put == -0.5
    
    # Deep ITM put
    delta_ditm_put = calculate_option_delta("PUT", 120, expiry, 100, CALC_DATE, low_vol) # 100 < 120 * 0.9 (108)
    assert delta_ditm_put == -1.0

    # Deep OTM put
    delta_dotm_put = calculate_option_delta("PUT", 80, expiry, 100, CALC_DATE, low_vol) # 100 > 80 * 1.1 (88)
    assert delta_dotm_put == 0.0
