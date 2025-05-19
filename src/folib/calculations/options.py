"""
Pure functions for option pricing and Greeks calculations.

This module provides functions for option pricing and Greeks calculations using QuantLib.
All functions follow functional programming principles with no side effects or state.
"""

import datetime
import logging
import warnings
from typing import Literal

# Import QuantLib and suppress SWIG-related DeprecationWarnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import QuantLib as ql

# Configure logger with more context
logger = logging.getLogger(__name__)

# Constants
OptionType = Literal["CALL", "PUT"]
DEFAULT_VOLATILITY = 0.3
DEFAULT_RISK_FREE_RATE = 0.05
OPTION_STYLE = "AMERICAN"  # All options are American-style by default


def _log_calculation_error(func_name: str, error: Exception, **kwargs) -> None:
    """
    Helper function to log option calculation errors in a structured way.
    Logs both the error and the input parameters that caused it.
    """
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(
        "Option calculation error: func=%s, error='%s', params={%s}",
        func_name,
        str(error),
        params,
        exc_info=True,
    )


def _log_calculation_warning(func_name: str, message: str, **kwargs) -> None:
    """
    Helper function to log option calculation warnings in a structured way.
    Logs both the warning message and the relevant parameters.
    """
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.warning(
        "Option calculation warning: func=%s, message='%s', params={%s}",
        func_name,
        message,
        params,
    )


def _calculate_intrinsic_value(
    option_type: OptionType, underlying_price: float, strike: float
) -> float:
    """Calculate the intrinsic value of an option.

    For a call option: max(0, underlying_price - strike)
    For a put option: max(0, strike - underlying_price)

    Args:
        option_type: "CALL" or "PUT"
        underlying_price: Current price of the underlying asset
        strike: Strike price of the option

    Returns:
        float: The intrinsic value of the option
    """
    if option_type == "CALL":
        return max(0.0, underlying_price - strike)
    else:  # PUT
        return max(0.0, strike - underlying_price)


def validate_option_inputs(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
) -> None:
    """Validate inputs for option calculations."""
    if option_type not in {"CALL", "PUT"}:
        raise ValueError(f"Invalid option_type: {option_type}. Must be 'CALL' or 'PUT'")
    if strike <= 0:
        raise ValueError(f"Invalid strike price: {strike}. Must be positive")
    if underlying_price <= 0:
        raise ValueError(
            f"Invalid underlying price: {underlying_price}. Must be positive"
        )
    if expiry < datetime.date.today():
        logger.warning(
            f"Option expiry {expiry} is in the past. Using fallback values for calculations."
        )


def calculate_option_price(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    volatility: float = DEFAULT_VOLATILITY,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> float:
    """Calculate option price using QuantLib with American-style options.

    This function handles several edge cases:
    1. For expired options (expiry < today), returns 0.0
    2. For options expiring today, returns intrinsic value:
       - For calls: max(0, underlying_price - strike)
       - For puts: max(0, strike - underlying_price)
    3. For valid options, uses QuantLib's binomial tree model

    Time values are handled in the local timezone. For options expiring today,
    the calculation uses the entire day (until market close).

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Option expiration date
        underlying_price: Current price of underlying
        volatility: Option volatility, default 0.3 (30%)
        risk_free_rate: Risk-free rate, default 0.05 (5%)

    Returns:
        Option price:
        - For expired options: 0.0
        - For options expiring today: intrinsic value
        - Otherwise: full Black-Scholes price using binomial tree

    Raises:
        ValueError: If inputs are fundamentally invalid (strike <= 0, etc)
    """
    validate_option_inputs(option_type, strike, expiry, underlying_price)
    if volatility <= 0:
        raise ValueError(f"Invalid volatility: {volatility}. Must be positive")
    if risk_free_rate < 0:
        raise ValueError(
            f"Invalid risk-free rate: {risk_free_rate}. Must be non-negative"
        )

    # Set up QuantLib date objects
    calculation_date = ql.Date().todaysDate()
    ql.Settings.instance().evaluationDate = calculation_date

    expiry_ql = ql.Date(expiry.day, expiry.month, expiry.year)
    if expiry_ql <= calculation_date:
        # For options expiring today, return intrinsic value
        _log_calculation_warning(
            "calculate_option_price",
            "Option expires today, returning intrinsic value",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
        )
        return _calculate_intrinsic_value(option_type, underlying_price, strike)

    try:
        # Set up the option
        payoff = ql.PlainVanillaPayoff(
            ql.Option.Call if option_type == "CALL" else ql.Option.Put, strike
        )
        exercise = ql.AmericanExercise(calculation_date, expiry_ql)
        option = ql.VanillaOption(payoff, exercise)

        # Set up the pricing environment
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
        riskfree_handle = ql.YieldTermStructureHandle(
            ql.FlatForward(calculation_date, risk_free_rate, ql.Actual365Fixed())
        )
        dividend_handle = ql.YieldTermStructureHandle(
            ql.FlatForward(calculation_date, 0.0, ql.Actual365Fixed())
        )
        volatility_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(
                calculation_date,
                ql.UnitedStates(ql.UnitedStates.NYSE),
                volatility,
                ql.Actual365Fixed(),
            )
        )

        # Create the pricing engine
        process = ql.BlackScholesMertonProcess(
            spot_handle, dividend_handle, riskfree_handle, volatility_handle
        )
        steps = 100
        engine = ql.BinomialVanillaEngine(process, "crr", steps)
        option.setPricingEngine(engine)

        price = option.NPV()
        logger.debug(
            "Option price calculated: price=%.4f, type=%s, strike=%.2f, underlying=%.2f, vol=%.3f",
            price,
            option_type,
            strike,
            underlying_price,
            volatility,
        )
        return price

    except Exception as e:
        _log_calculation_error(
            "calculate_option_price",
            e,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )
        # Calculate intrinsic value as fallback
        intrinsic = _calculate_intrinsic_value(option_type, underlying_price, strike)
        _log_calculation_warning(
            "calculate_option_price",
            f"Using fallback price {intrinsic}",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
        )
        return intrinsic


def calculate_option_delta(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    option_price: float,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> float:
    """Calculate American option delta using QuantLib's Binomial Tree engine.

    Edge cases are handled as follows:
    1. For expired options (expiry < today): returns 0.0
    2. For options expiring today: calculates delta but warns about potential instability
    3. If QuantLib calculation fails: uses fallback deltas:
       - Calls: ~0.5 if near the money, decreasing to ~0.1 for OTM
       - Puts: ~-0.5 if near the money, decreasing to ~-0.1 for OTM

    Implied volatility is calculated from the market price. If IV calculation fails,
    uses DEFAULT_VOLATILITY (0.3).

    Note: All calculations use local timezone. For options expiring today,
    calculations assume they expire at market close.

    Args:
        option_type: "CALL" or "PUT".
        strike: Option strike price.
        expiry: Option expiration date
        underlying_price: Current price of the underlying asset.
        option_price: Market price of the option.
        risk_free_rate: Risk-free interest rate.

    Returns:
        The calculated option delta. Range depends on option type:
        - For calls: value between 0 and 1
        - For puts: value between -1 and 0
        For expired options: returns 0.0

    Raises:
        ValueError: If inputs are invalid (option_price <= 0, etc).
    """
    # Validate inputs
    validate_option_inputs(option_type, strike, expiry, underlying_price)
    if option_price <= 0:
        raise ValueError(f"Invalid option price: {option_price}. Must be positive")

    # Calculate implied volatility from option price
    try:
        volatility = calculate_implied_volatility(
            option_type, strike, expiry, underlying_price, option_price, risk_free_rate
        )
    except Exception as e:
        _log_calculation_warning(
            "calculate_option_delta",
            "Failed to calculate implied volatility, using default",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            option_price=option_price,
            error=str(e),
        )
        volatility = DEFAULT_VOLATILITY

    # --- 1. Setup Dates ---
    calculation_date = ql.Date().todaysDate()
    ql.Settings.instance().evaluationDate = calculation_date

    expiry_ql = ql.Date(expiry.day, expiry.month, expiry.year)
    if expiry_ql <= calculation_date:
        _log_calculation_warning(
            "calculate_option_delta",
            "Option is expired or near expiry, returning 0.0",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
        )
        return 0.0

    try:
        # Set up the option
        ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
        payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
        exercise = ql.AmericanExercise(calculation_date, expiry_ql)
        option = ql.VanillaOption(payoff, exercise)

        # --- 3. Setup Market Data Handles ---
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
        riskfree_curve_handle = ql.YieldTermStructureHandle(
            ql.FlatForward(calculation_date, risk_free_rate, ql.Actual365Fixed())
        )
        dividend_curve_handle = ql.YieldTermStructureHandle(
            ql.FlatForward(calculation_date, 0.0, ql.Actual365Fixed())
        )
        volatility_curve_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(
                calculation_date, ql.TARGET(), volatility, ql.Actual365Fixed()
            )
        )

        # --- 4. Create Stochastic Process ---
        process = ql.BlackScholesMertonProcess(
            spot_handle,
            dividend_curve_handle,
            riskfree_curve_handle,
            volatility_curve_handle,
        )

        # --- 5. Setup Pricing Engine ---
        steps = 101  # Number of steps in the binomial tree
        engine = ql.BinomialVanillaEngine(process, "crr", steps)
        option.setPricingEngine(engine)

        # --- 6. Calculate Delta ---
        delta = option.delta()
        logger.debug(
            "Option delta calculated: delta=%.4f, type=%s, strike=%.2f, underlying=%.2f, vol=%.3f",
            delta,
            option_type,
            strike,
            underlying_price,
            volatility,
        )
        return delta

    except Exception as e:
        _log_calculation_error(
            "calculate_option_delta",
            e,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )
        # Return reasonable default delta based on moneyness
        if option_type == "CALL":
            default_delta = 0.5 if underlying_price > strike else 0.1
        else:  # PUT
            default_delta = -0.5 if underlying_price < strike else -0.1

        _log_calculation_warning(
            "calculate_option_delta",
            f"Using fallback delta {default_delta}",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            delta=default_delta,
        )
        return default_delta


def categorize_option_by_delta(delta: float) -> str:
    """Categorize an option as 'long' or 'short' based on its delta.

    This follows the convention in the old implementation (src/folio/portfolio_value.py):
    - Positive delta (long calls, short puts) => Long position
    - Negative delta (short calls, long puts) => Short position

    Args:
        delta: Option delta value between -1.0 and 1.0

    Returns:
        'long' for positive delta, 'short' for negative delta
    """
    # In the old implementation, options are categorized based on the sign of delta
    # This is critical for matching the old implementation's behavior
    return "long" if delta >= 0 else "short"


def calculate_implied_volatility(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    option_price: float,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> float:
    """Calculate implied volatility using QuantLib.

    Edge cases are handled as follows:
    1. For expired options (expiry < today):
       Returns DEFAULT_VOLATILITY with a warning
    2. For options expiring today:
       Calculates IV but warns that result may be unreliable
    3. If calculation fails (e.g., no valid solution):
       Returns DEFAULT_VOLATILITY and logs a warning

    The calculation uses a binary search between 0.1% and 500% volatility.
    Local timezone is used for all date/time calculations.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Option expiration date
        underlying_price: Current price of underlying
        option_price: Market price of the option
        risk_free_rate: Risk-free rate, default 0.05 (5%)

    Returns:
        Implied volatility as a decimal (e.g., 0.3 for 30% volatility)
        Falls back to DEFAULT_VOLATILITY (0.3) if calculation fails

    Raises:
        ValueError: If inputs are fundamentally invalid (option_price <= 0, etc)
    """
    validate_option_inputs(option_type, strike, expiry, underlying_price)
    if option_price <= 0:
        raise ValueError(f"Invalid option price: {option_price}. Must be positive")

    # Set up QuantLib date objects
    calculation_date = ql.Date().todaysDate()
    ql.Settings.instance().evaluationDate = calculation_date
    expiry_ql = ql.Date(expiry.day, expiry.month, expiry.year)

    if expiry_ql < calculation_date:
        _log_calculation_warning(
            "calculate_implied_volatility",
            f"Option is expired, using default volatility: {DEFAULT_VOLATILITY:.3f}",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )
        return DEFAULT_VOLATILITY

    # Set up the option
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)

    try:
        vol = option.impliedVolatility(
            option_price,
            ql.BlackScholesMertonProcess(
                ql.QuoteHandle(ql.SimpleQuote(underlying_price)),
                ql.YieldTermStructureHandle(
                    ql.FlatForward(calculation_date, 0.0, ql.Actual365Fixed())
                ),
                ql.YieldTermStructureHandle(
                    ql.FlatForward(
                        calculation_date, risk_free_rate, ql.Actual365Fixed()
                    )
                ),
                ql.BlackVolTermStructureHandle(
                    ql.BlackConstantVol(
                        calculation_date,
                        ql.UnitedStates(ql.UnitedStates.NYSE),
                        DEFAULT_VOLATILITY,
                        ql.Actual365Fixed(),
                    )
                ),
            ),
            1.0e-6,  # accuracy
            100,  # max evaluations
            0.001,  # min vol
            5.0,  # max vol
        )
        if expiry_ql == calculation_date:
            _log_calculation_warning(
                "calculate_implied_volatility",
                f"Option expires today, implied volatility may be unreliable: {vol:.6f}",
                option_type=option_type,
                strike=strike,
                expiry=expiry,
                underlying_price=underlying_price,
                option_price=option_price,
                volatility=vol,
            )

        logger.debug(
            "Implied volatility calculated: vol=%.4f, type=%s, strike=%.2f, underlying=%.2f, price=%.2f",
            vol,
            option_type,
            strike,
            underlying_price,
            option_price,
        )
        return vol

    except RuntimeError as e:
        _log_calculation_error(
            "calculate_implied_volatility",
            e,
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )

        _log_calculation_warning(
            "calculate_implied_volatility",
            f"Using fallback volatility {DEFAULT_VOLATILITY}",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )
        return DEFAULT_VOLATILITY
