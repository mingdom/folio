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

# Configure logger
logger = logging.getLogger(__name__)

OptionType = Literal["CALL", "PUT"]


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
    if expiry < calculation_date_py: # Use Python date for comparison
        raise OptionCalculationError(
            f"Invalid expiry date: {expiry}. Must be on or after calculation date {calculation_date_py}"
        )
    if option_price == 0 and time_to_expiry > 0: # Option price is 0 but not expired
        raise OptionCalculationError(
            f"Invalid option price: {option_price}. Cannot be zero for unexpired option."
        )
    if option_price < 0:
        raise OptionCalculationError(
            f"Invalid option price: {option_price}. Must be non-negative."
        )


# --- Constants for Implied Volatility Calculation ---
MIN_VOLATILITY = 0.0001  # 0.01% - Absolute minimum IV to return
DEFAULT_VOLATILITY = 0.3 # Default fallback ONLY for specific unresolvable scenarios (e.g. some at-expiry cases)
ACCEPTABLE_QL_MIN_VOL = 1.0e-7 # Min vol QL can handle without issues in some versions
DEEP_ITM_VOL_CEILING = 0.05    # 5% - Max vol to try for very deep ITM options in first pass
STANDARD_CALC_MIN_VOL = 0.001  # 0.1% - Min vol for standard calculation attempt
STANDARD_CALC_MAX_VOL = 5.0    # 500% - Max vol for standard calculation attempt
# NEAR_EXPIRY_DAYS_THRESHOLD still used for Delta/Greeks, not directly here for IV yet.
# MIN_VOLATILITY_TO_CALCULATE_DELTA also separate for greeks logic.


class OptionCalculationError(Exception):
    """Custom exception for errors during option calculations."""


def calculate_time_to_expiry(
    expiration_date: datetime.date, calculation_date: datetime.date
) -> float:
    """
    Calculate time to expiry in years. Returns 0 if calculation_date is on or after expiration.
    """
    if calculation_date >= expiration_date:
        return 0.0
    return (expiration_date - calculation_date).days / 365.0


def _parse_ql_root_not_bracketed_error(error_message: str) -> tuple[float | None, float | None]:
    """
    Rudimentary parser for QuantLib's "root not bracketed" error.
    Example: "root not bracketed: f[1e-07,0.05] -> [3.478656,3.428732]"
    Returns (value_at_min_vol, value_at_max_vol) from the error string.
    Returns (None, None) if parsing fails.
    """
    try:
        part = error_message.split(" -> ")[1]
        if part.startswith("[") and part.endswith("]"):
            values_str = part[1:-1].split(",")
            val_a = float(values_str[0])
            val_b = float(values_str[1])
            return val_a, val_b
        return None, None
    except Exception: # pylint: disable=broad-except
        logger.debug("Could not parse QL root not bracketed error details: %s", error_message)
        return None, None


def calculate_implied_volatility( # noqa: C901: function is too complex
    option_type: OptionType,
    strike_price: float,
    expiration_date: datetime.date,
    underlying_price: float,
    option_price: float,
    calculation_date_py: datetime.date, # Python datetime.date
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0, # Added dividend yield
) -> float:
    """
    Calculate American option implied volatility using QuantLib.

    Args:
        option_type: "CALL" or "PUT".
        strike_price: Option strike price.
        expiration_date: Option expiration date.
        underlying_price: Current price of the underlying asset.
        option_price: Market price of the option.
        calculation_date_py: The date for which calculation is performed.
        risk_free_rate: Risk-free interest rate.
        dividend_yield: Continuous dividend yield of the underlying.

    Returns:
        The calculated implied volatility.

    Raises:
        OptionCalculationError: If inputs are invalid or IV cannot be found.
    """
    time_to_expiry = calculate_time_to_expiry(expiration_date, calculation_date_py)

    validate_option_inputs( # Basic validation of option parameters
        option_type=option_type,
        strike=strike_price,
        expiry=expiration_date, # Python date
        underlying_price=underlying_price,
        option_price=option_price, # Pass option_price for validation
        calculation_date_py=calculation_date_py, # Python date
        time_to_expiry=time_to_expiry
    )


    # --- QuantLib Date Setup ---
    calculation_date_ql = ql.Date(calculation_date_py.day, calculation_date_py.month, calculation_date_py.year)
    ql.Settings.instance().evaluationDate = calculation_date_ql
    expiry_ql = ql.Date(expiration_date.day, expiration_date.month, expiration_date.year)

    # --- Intrinsic Value Calculation ---
    if option_type == "CALL":
        intrinsic_value = max(0.0, underlying_price - strike_price)
    else:  # PUT
        intrinsic_value = max(0.0, strike_price - underlying_price)

    # --- Handle Expired or At-Expiry Options ---
    if time_to_expiry == 0:
        if abs(option_price - intrinsic_value) < 0.0001: # Effectively option_price == intrinsic_value
            logger.debug(
                "Option at expiry and price equals intrinsic value. IV set to MIN_VOLATILITY (%s).", MIN_VOLATILITY
            )
            return MIN_VOLATILITY
        # If at expiry and option_price != intrinsic_value, this is an anomaly.
        # The plan mentions using DEFAULT_VOLATILITY for mispricing at expiry.
        # This part might need refinement based on how "mispricing at expiry" is strictly defined.
        # For now, if it's not matching intrinsic, it's problematic.
        logger.warning(
            "Option at expiry but price (%s) does not match intrinsic value (%s). "
            "This indicates potential mispricing or data error. Using DEFAULT_VOLATILITY.",
            option_price, intrinsic_value
        )
        return DEFAULT_VOLATILITY # Fallback for problematic at-expiry options

    # --- Arbitrage Check (Option price < intrinsic value) ---
    # Using a small tolerance for floating point comparisons
    if option_price < intrinsic_value - 0.0001:
        msg = (
            f"Option price {option_price} is less than its intrinsic value {intrinsic_value} "
            f"for {option_type} {strike_price} @ {underlying_price}. This is an arbitrage condition."
        )
        logger.error(msg)
        raise OptionCalculationError(msg)

    # --- Option price equals intrinsic value (but not expired) ---
    if abs(option_price - intrinsic_value) < 0.0001:
        logger.info(
            "Option price %s equals intrinsic value %s for unexpired option. "
            "Returning MIN_VOLATILITY = %s.",
            option_price, intrinsic_value, MIN_VOLATILITY
        )
        return MIN_VOLATILITY

    # --- Setup QuantLib Option Object ---
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike_price)
    exercise = ql.AmericanExercise(calculation_date_ql, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)

    # --- Setup Market Data Handles for Implied Volatility Calculation ---
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_curve_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date_ql, risk_free_rate, ql.Actual365Fixed())
    )
    dividend_curve_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date_ql, dividend_yield, ql.Actual365Fixed())
    )
    # Process is created *without* volatility for implied volatility calculation
    process = ql.BlackScholesMertonProcess(
        spot_handle, dividend_curve_handle, riskfree_curve_handle, ql.BlackVolTermStructureHandle() # Empty vol handle
    )

    # --- Implied Volatility Calculation Attempts ---
    time_value = option_price - intrinsic_value
    iv_result = None

    # First attempt: For deep ITM / low time value options
    # Condition: Time value is < 2% of option price OR absolute time value is < $0.05
    if (option_price > 0 and (time_value / option_price) < 0.02) or (time_value < 0.05):
        logger.debug("Attempting IV calculation with deep ITM parameters.")
        try:
            iv_result = option.impliedVolatility(
                option_price,
                process,
                1.0e-4,  # accuracy
                200,     # maxEvaluations
                ACCEPTABLE_QL_MIN_VOL,
                DEEP_ITM_VOL_CEILING
            )
            logger.info("IV calculated (deep ITM attempt): %s", iv_result)
            return max(MIN_VOLATILITY, iv_result) # Ensure it's not below MIN_VOLATILITY
        except RuntimeError as e:
            error_msg = str(e)
            logger.warning("Deep ITM IV calculation failed (attempt 1): %s", error_msg)
            if "root not bracketed" in error_msg:
                val_a, val_b = _parse_ql_root_not_bracketed_error(error_msg)
                # If f[min_vol] and f[max_vol] are both positive, it implies BS(vol) > option_price
                # for the entire range [min_vol, max_vol].
                # If option_price > intrinsic_value, this suggests true IV might be < min_vol.
                if val_a is not None and val_b is not None and val_a > 0 and val_b > 0:
                    logger.warning(
                        "Deep ITM 'root not bracketed' error suggests IV < %s. Returning MIN_VOLATILITY.",
                        ACCEPTABLE_QL_MIN_VOL
                    )
                    return MIN_VOLATILITY
                # otherwise, proceed to second attempt

    # Second attempt: Standard calculation range
    if iv_result is None: # Only if first attempt didn't yield a result or was skipped
        logger.debug("Attempting IV calculation with standard parameters.")
        try:
            iv_result = option.impliedVolatility(
                option_price,
                process,
                1.0e-4,  # accuracy
                200,     # maxEvaluations
                STANDARD_CALC_MIN_VOL,
                STANDARD_CALC_MAX_VOL
            )
            logger.info("IV calculated (standard attempt): %s", iv_result)
            return max(MIN_VOLATILITY, iv_result) # Ensure it's not below MIN_VOLATILITY
        except RuntimeError as e:
            error_msg = str(e)
            logger.error("Standard IV calculation failed (attempt 2): %s", error_msg)
            if "root not bracketed" in error_msg:
                val_a, val_b = _parse_ql_root_not_bracketed_error(error_msg)
                if val_a is not None and val_b is not None:
                    # If f[min_vol] and f[max_vol] are both positive, suggests IV < STANDARD_CALC_MIN_VOL
                    if val_a > 0 and val_b > 0:
                        logger.warning(
                            "Standard 'root not bracketed' error suggests IV < %s. Returning MIN_VOLATILITY.",
                             STANDARD_CALC_MIN_VOL
                        )
                        return MIN_VOLATILITY
                    # If f[min_vol] and f[max_vol] are both negative, suggests IV > STANDARD_CALC_MAX_VOL
                    # (BS(vol) - Price < 0  => BS(vol) < Price)
                    if val_a < 0 and val_b < 0:
                        logger.warning(
                            "Standard 'root not bracketed' error suggests IV > %s. Capping at STANDARD_CALC_MAX_VOL.",
                            STANDARD_CALC_MAX_VOL
                        )
                        return STANDARD_CALC_MAX_VOL # New fallback: cap at max vol
            # For other "root not bracketed" or any other RuntimeError
            raise OptionCalculationError(f"Failed to calculate implied volatility after all attempts: {error_msg}") from e

    # Should not be reached if logic is correct, but as a failsafe:
    logger.error("Implied volatility calculation reached unexpected end state. Raising error.")
    raise OptionCalculationError("Failed to determine implied volatility through defined paths.")


def calculate_option_price( # Existing function, ensure it uses python dates for interface
    option_type: OptionType,
    strike: float,
    expiry_py: datetime.date, # Python date
    underlying_price: float,
    calculation_date_py: datetime.date, # Python date
    volatility: float, # Made volatility non-optional
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0, # Added dividend yield
) -> float:
    """Calculate option price using QuantLib with American-style options.
    (Signature adjusted to match typical usage patterns after IV calc)
    """
    time_to_expiry = calculate_time_to_expiry(expiry_py, calculation_date_py)
    validate_option_inputs(
        option_type, strike, expiry_py, underlying_price, None, calculation_date_py, time_to_expiry
    ) # Option price None for this validation

    if volatility <= 0: # Check after basic validation
        # For price calculation, very low (but >0) volatility is theoretically possible.
        # However, if it's non-positive, it's an error.
        raise OptionCalculationError(f"Invalid volatility: {volatility}. Must be positive for price calculation.")
    if risk_free_rate < 0:
        raise OptionCalculationError(
            f"Invalid risk-free rate: {risk_free_rate}. Must be non-negative"
        )

    # Set up QuantLib date objects
    calculation_date_ql = ql.Date(calculation_date_py.day, calculation_date_py.month, calculation_date_py.year)
    ql.Settings.instance().evaluationDate = calculation_date_ql
    expiry_ql = ql.Date(expiry_py.day, expiry_py.month, expiry_py.year)

    if expiry_ql <= calculation_date_ql: # Option expired or at expiry
        # Return intrinsic value if at or past expiry
        if option_type == "CALL":
            return max(0.0, underlying_price - strike)
        return max(0.0, strike - underlying_price)


    payoff = ql.PlainVanillaPayoff(
        ql.Option.Call if option_type == "CALL" else ql.Option.Put, strike
    )
    exercise = ql.AmericanExercise(calculation_date_ql, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)

    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date_ql, risk_free_rate, ql.Actual365Fixed())
    )
    dividend_handle = ql.YieldTermStructureHandle( # Use dividend_yield
        ql.FlatForward(calculation_date_ql, dividend_yield, ql.Actual365Fixed())
    )
    volatility_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            calculation_date_ql,
            ql.UnitedStates(ql.UnitedStates.NYSE),
            volatility,
            ql.Actual365Fixed(),
        )
    )

    process = ql.BlackScholesMertonProcess(
        spot_handle, dividend_handle, riskfree_handle, volatility_handle
    )
    # Using a more standard number of steps for Binomial Engine
    steps = 101 # Consistent with delta calculation
    engine = ql.BinomialVanillaEngine(process, "crr", steps)
    option.setPricingEngine(engine)

    try:
        price = option.NPV()
    except Exception as e:
        logger.error("QuantLib NPV calculation failed: %s", e)
        raise OptionCalculationError(f"QuantLib price calculation failed: {e}") from e
    return price


def calculate_option_delta( # Signature uses python dates
    option_type: OptionType,
    strike: float,
    expiry_py: datetime.date, # Python date
    underlying_price: float,
    calculation_date_py: datetime.date, # Python date
    volatility: float, # Made volatility non-optional
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0, # Added dividend yield
) -> float:
    """
    Calculate American option delta using QuantLib's Binomial Tree engine.
    (Signature adjusted, volatility is now required)
    """
    time_to_expiry = calculate_time_to_expiry(expiry_py, calculation_date_py)
    validate_option_inputs( # Basic validation
        option_type, strike, expiry_py, underlying_price, None, calculation_date_py, time_to_expiry
    )

    # --- Handle Expired or At-Expiry Options ---
    if time_to_expiry == 0:
        if option_type == "CALL":
            return 1.0 if underlying_price > strike else 0.0
        # PUT
        return -1.0 if underlying_price < strike else 0.0

    # --- Low Volatility Approximations (as per previous PR logic for delta) ---
    # This threshold might need to be distinct from MIN_VOLATILITY used for IV.
    MIN_VOL_FOR_DELTA_CALC = 0.001 # Example: 0.1%
    if volatility < MIN_VOL_FOR_DELTA_CALC:
        logger.warning(
            "Volatility %s is very low (<%s) for %s %s. Using approximation for delta.",
            volatility, MIN_VOL_FOR_DELTA_CALC, option_type, strike
        )
        # Deep ITM/OTM approximation
        if option_type == "CALL":
            if underlying_price >= strike * 1.1:  # Deep ITM (e.g., 10% in the money)
                return 1.0
            if underlying_price <= strike * 0.9:  # Deep OTM
                return 0.0
            return 0.5 # Heuristic for near the money, low IV
        else:  # PUT
            if underlying_price <= strike * 0.9:  # Deep ITM
                return -1.0
            if underlying_price >= strike * 1.1:  # Deep OTM
                return 0.0
            return -0.5 # Heuristic

    # --- QuantLib Date Setup ---
    calculation_date_ql = ql.Date(calculation_date_py.day, calculation_date_py.month, calculation_date_py.year)
    ql.Settings.instance().evaluationDate = calculation_date_ql
    expiry_ql = ql.Date(expiry_py.day, expiry_py.month, expiry_py.year)


    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date_ql, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)

    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_curve_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date_ql, risk_free_rate, ql.Actual365Fixed())
    )
    dividend_curve_handle = ql.YieldTermStructureHandle( # Use dividend_yield
        ql.FlatForward(calculation_date_ql, dividend_yield, ql.Actual365Fixed())
    )
    volatility_curve_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            calculation_date_ql, ql.TARGET(), volatility, ql.Actual365Fixed() # TARGET calendar is more generic
        )
    )

    process = ql.BlackScholesMertonProcess(
        spot_handle,
        dividend_curve_handle,
        riskfree_curve_handle,
        volatility_curve_handle,
    )

    steps = 101
    engine = ql.BinomialVanillaEngine(process, "crr", steps)
    option.setPricingEngine(engine)

    try:
        delta = option.delta()
    except RuntimeError as e:
        logger.error("QuantLib delta calculation failed for %s %s: %s", option_type, strike, e)
        raise OptionCalculationError(f"QuantLib delta calculation failed: {e}") from e

    logger.debug(
        "Option delta for %s %s (underlying: %s, vol: %s, TTE: %s): delta=%.4f",
        option_type, strike, underlying_price, volatility, time_to_expiry, delta
    )
    return delta


# Placeholder for other Greeks - Gamma, Vega, Theta
# These would follow a similar pattern to calculate_option_delta,
# requiring volatility and calculation_date, and specific QuantLib calls.

def calculate_option_gamma(
    option_type: OptionType,
    strike: float,
    expiry_py: datetime.date,
    underlying_price: float,
    calculation_date_py: datetime.date,
    volatility: float,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0,
) -> float:
    time_to_expiry = calculate_time_to_expiry(expiry_py, calculation_date_py)
    if time_to_expiry == 0: return 0.0
    # Simplified: actual implementation would mirror delta's QL setup
    logger.debug("Gamma calculation placeholder for %s %s", option_type, strike)
    # Add similar low volatility handling as delta if needed
    MIN_VOL_FOR_GAMMA_CALC = 0.001
    if volatility < MIN_VOL_FOR_GAMMA_CALC:
        logger.warning("Low volatility %s for gamma calculation, returning 0.0", volatility)
        return 0.0

    calculation_date_ql = ql.Date(calculation_date_py.day, calculation_date_py.month, calculation_date_py.year)
    ql.Settings.instance().evaluationDate = calculation_date_ql
    expiry_ql = ql.Date(expiry_py.day, expiry_py.month, expiry_py.year)
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date_ql, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_curve_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date_ql, risk_free_rate, ql.Actual365Fixed()))
    dividend_curve_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date_ql, dividend_yield, ql.Actual365Fixed()))
    volatility_curve_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(calculation_date_ql, ql.TARGET(), volatility, ql.Actual365Fixed()))
    process = ql.BlackScholesMertonProcess(spot_handle, dividend_curve_handle, riskfree_curve_handle, volatility_curve_handle)
    engine = ql.BinomialVanillaEngine(process, "crr", 101)
    option.setPricingEngine(engine)
    try:
        return option.gamma()
    except RuntimeError as e:
        logger.error("QuantLib gamma calculation failed: %s", e)
        raise OptionCalculationError(f"QuantLib gamma calculation failed: {e}") from e


def calculate_option_vega(
    option_type: OptionType,
    strike: float,
    expiry_py: datetime.date,
    underlying_price: float,
    calculation_date_py: datetime.date,
    volatility: float,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0,
) -> float:
    time_to_expiry = calculate_time_to_expiry(expiry_py, calculation_date_py)
    if time_to_expiry == 0: return 0.0
    logger.debug("Vega calculation placeholder for %s %s", option_type, strike)
    MIN_VOL_FOR_VEGA_CALC = 0.001
    if volatility < MIN_VOL_FOR_VEGA_CALC:
        logger.warning("Low volatility %s for vega calculation, returning 0.0", volatility)
        return 0.0

    calculation_date_ql = ql.Date(calculation_date_py.day, calculation_date_py.month, calculation_date_py.year)
    ql.Settings.instance().evaluationDate = calculation_date_ql
    expiry_ql = ql.Date(expiry_py.day, expiry_py.month, expiry_py.year)
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date_ql, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_curve_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date_ql, risk_free_rate, ql.Actual365Fixed()))
    dividend_curve_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date_ql, dividend_yield, ql.Actual365Fixed()))
    volatility_curve_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(calculation_date_ql, ql.TARGET(), volatility, ql.Actual365Fixed()))
    process = ql.BlackScholesMertonProcess(spot_handle, dividend_curve_handle, riskfree_curve_handle, volatility_curve_handle)
    # For Vega, and other Greeks, AnalyticEuropeanEngine is often used if appropriate for the option type (European)
    # For American options, Binomial/FiniteDifferences are needed, but Analytic might be used for approximation
    # To be consistent with Delta, using Binomial. Some Greeks might not be directly available from all engines.
    engine = ql.BinomialVanillaEngine(process, "crr", 101) # Or AnalyticEuropeanEngine if European
    option.setPricingEngine(engine)
    try:
        # Vega is typically per 1% change in vol, so divide by 100 if QL returns it that way
        # QL's vega() is per 1.0 change in vol (i.e. 100%)
        return option.vega() / 100.0
    except RuntimeError as e:
        logger.error("QuantLib vega calculation failed: %s", e)
        raise OptionCalculationError(f"QuantLib vega calculation failed: {e}") from e


def calculate_option_theta(
    option_type: OptionType,
    strike: float,
    expiry_py: datetime.date,
    underlying_price: float,
    calculation_date_py: datetime.date,
    volatility: float,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0,
) -> float:
    time_to_expiry = calculate_time_to_expiry(expiry_py, calculation_date_py)
    if time_to_expiry == 0: return 0.0
    logger.debug("Theta calculation placeholder for %s %s", option_type, strike)
    MIN_VOL_FOR_THETA_CALC = 0.001
    if volatility < MIN_VOL_FOR_THETA_CALC:
        logger.warning("Low volatility %s for theta calculation, returning 0.0", volatility)
        return 0.0

    calculation_date_ql = ql.Date(calculation_date_py.day, calculation_date_py.month, calculation_date_py.year)
    ql.Settings.instance().evaluationDate = calculation_date_ql
    expiry_ql = ql.Date(expiry_py.day, expiry_py.month, expiry_py.year)
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date_ql, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    riskfree_curve_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date_ql, risk_free_rate, ql.Actual365Fixed()))
    dividend_curve_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date_ql, dividend_yield, ql.Actual365Fixed()))
    volatility_curve_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(calculation_date_ql, ql.TARGET(), volatility, ql.Actual365Fixed()))
    process = ql.BlackScholesMertonProcess(spot_handle, dividend_curve_handle, riskfree_curve_handle, volatility_curve_handle)
    engine = ql.BinomialVanillaEngine(process, "crr", 101)
    option.setPricingEngine(engine)
    try:
        # Theta is per day, so divide by 365 if QL returns annualized theta
        # QL's theta() is per year.
        return option.theta() / 365.0
    except RuntimeError as e:
        logger.error("QuantLib theta calculation failed: %s", e)
        raise OptionCalculationError(f"QuantLib theta calculation failed: {e}") from e


def validate_option_inputs( # Renamed to reflect it's used more broadly
    option_type: OptionType,
    strike: float,
    expiry: datetime.date, # Python date
    underlying_price: float,
    option_price: float | None, # Can be None if validating for price calc
    calculation_date_py: datetime.date, # Python date
    time_to_expiry: float
) -> None:
    """Validate inputs for option calculations."""
    if option_type not in {"CALL", "PUT"}:
        raise OptionCalculationError(f"Invalid option_type: {option_type}. Must be 'CALL' or 'PUT'")
    if strike <= 0:
        raise OptionCalculationError(f"Invalid strike price: {strike}. Must be positive")
    if underlying_price <= 0:
        raise OptionCalculationError(
            f"Invalid underlying price: {underlying_price}. Must be positive"
        )
    # Expiry check already incorporated by time_to_expiry logic generally
    # but explicit check against calculation_date is good.
    if expiry < calculation_date_py:
        # This case should ideally be caught by time_to_expiry == 0 earlier in most flows
        raise OptionCalculationError(
            f"Expiry date {expiry} cannot be before calculation date {calculation_date_py}."
        )

    if option_price is not None:
        if option_price < 0: # Price cannot be negative
            raise OptionCalculationError(
                f"Invalid option price: {option_price}. Must be non-negative."
            )
        # If option is expired (time_to_expiry == 0), option_price can be 0.
        # If not expired (time_to_expiry > 0), option_price generally shouldn't be 0.
        # This specific check (option_price == 0 and time_to_expiry > 0)
        # might be too strict as some very OTM options might have near-zero prices.
        # However, for IV calculation, a zero price for an unexpired option is problematic.
        if option_price == 0 and time_to_expiry > 0:
             logger.warning("Option price is 0 for an unexpired option. This may lead to IV calculation issues.")
             # Not raising error here, but IV calc will likely fail or return min/extreme if it proceeds.


# Removed categorize_option_by_delta as it's not directly used by calculations
# and can be implemented at a higher service level if needed based on conventions.
