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
DEFAULT_VOLATILITY = 0.3
DEFAULT_RISK_FREE_RATE = 0.05
OPTION_STYLE = "AMERICAN"  # All options are American-style by default


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
        raise ValueError(f"Invalid expiry date: {expiry}. Must be in the future")


def calculate_option_price(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    volatility: float = DEFAULT_VOLATILITY,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> float:
    """Calculate option price using QuantLib with American-style options.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Option expiration date
        underlying_price: Current price of underlying
        volatility: Option volatility, default 0.3 (30%)
        risk_free_rate: Risk-free rate, default 0.05 (5%)

    Returns:
        Option price calculated using binomial tree model

    Raises:
        ValueError: If any inputs are invalid
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
        expiry_ql = calculation_date + 1

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
            ql.UnitedStates(
                ql.UnitedStates.NYSE
            ),  # Use NYSE calendar to match old implementation
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

    return option.NPV()


def calculate_option_delta(
    option_type: OptionType,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    option_price: float,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> float:
    """
    Calculate American option delta using QuantLib's Binomial Tree engine.

    Args:
        option_type: "CALL" or "PUT".
        strike: Option strike price.
        expiry: Option expiration date (datetime.date object).
        underlying_price: Current price of the underlying asset.
        option_price: Market price of the option.
        risk_free_rate: Risk-free interest rate.

    Returns:
        The calculated option delta.
        - For calls: positive value between 0 and 1
        - For puts: negative value between -1 and 0

    Raises:
        RuntimeError: If QuantLib encounters an error during calculation.
        ValueError: If inputs are fundamentally invalid (e.g., expiry in the past).
    """
    # Validate inputs
    validate_option_inputs(option_type, strike, expiry, underlying_price)
    if option_price <= 0:
        raise ValueError(f"Invalid option price: {option_price}. Must be positive")

    # Calculate implied volatility from option price
    volatility = calculate_implied_volatility(
        option_type, strike, expiry, underlying_price, option_price, risk_free_rate
    )

    # --- 1. Setup Dates ---
    calculation_date = ql.Date().todaysDate()
    ql.Settings.instance().evaluationDate = calculation_date

    # Handle expiry date
    expiry_ql = ql.Date(expiry.day, expiry.month, expiry.year)
    if expiry_ql <= calculation_date:
        logger.warning(
            f"Option expiry {expiry} is in the past. Using next day for calculation."
        )
        expiry_ql = calculation_date + 1

    # --- 2. Define Option ---
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)

    # --- 3. Setup Market Data Handles ---
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
    # FlatForward creates a simple yield term structure (curve)
    riskfree_curve_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date, risk_free_rate, ql.Actual365Fixed())
    )
    # Assuming no dividends for simplicity
    dividend_curve_handle = ql.YieldTermStructureHandle(
        ql.FlatForward(calculation_date, 0.0, ql.Actual365Fixed())
    )
    # Flat volatility term structure
    volatility_curve_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            calculation_date, ql.TARGET(), volatility, ql.Actual365Fixed()
        )
    )

    # --- 4. Create Stochastic Process ---
    # Black-Scholes-Merton process describes how the underlying price evolves
    process = ql.BlackScholesMertonProcess(
        spot_handle,
        dividend_curve_handle,
        riskfree_curve_handle,
        volatility_curve_handle,
    )

    # --- 5. Setup Pricing Engine ---
    # Using Binomial Tree (Cox-Ross-Rubinstein) engine, suitable for American options
    steps = 101  # Number of steps in the binomial tree
    engine = ql.BinomialVanillaEngine(process, "crr", steps)
    option.setPricingEngine(engine)

    # --- 6. Calculate Delta ---
    try:
        delta = option.delta()
    except Exception as e:
        # Catch potential QuantLib calculation errors
        raise RuntimeError(f"QuantLib calculation failed: {e}") from e

    logger.debug(
        f"Option delta for {option_type} {strike} (underlying: {underlying_price}): "
        f"delta={delta:.4f}"
    )

    return delta


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

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Option expiration date
        underlying_price: Current price of underlying
        option_price: Market price of the option
        risk_free_rate: Risk-free rate, default 0.05 (5%)

    Returns:
        Implied volatility that produces the given option_price

    Raises:
        ValueError: If inputs are fundamentally invalid (e.g., expiry in the past).
    """
    validate_option_inputs(option_type, strike, expiry, underlying_price)
    if option_price <= 0:
        raise ValueError(f"Invalid option price: {option_price}. Must be positive")

    # Set up QuantLib date objects
    calculation_date = ql.Date().todaysDate()
    ql.Settings.instance().evaluationDate = calculation_date
    expiry_ql = ql.Date(expiry.day, expiry.month, expiry.year)
    if expiry_ql <= calculation_date:
        raise ValueError(f"Invalid expiry date: {expiry}. Must be in the future")

    # Set up the option
    ql_option_type = ql.Option.Call if option_type == "CALL" else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(ql_option_type, strike)
    exercise = ql.AmericanExercise(calculation_date, expiry_ql)
    option = ql.VanillaOption(payoff, exercise)

    # Use QuantLib's built-in implied volatility solver
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
        return vol
    except RuntimeError as e:
        # Log all relevant option parameters for debugging
        logger.error(
            f"Implied volatility calculation failed for option: "
            f"type={option_type}, strike={strike}, expiry={expiry}, "
            f"underlying_price={underlying_price}, option_price={option_price}, "
            f"risk_free_rate={risk_free_rate}. Error: {e}"
        )
        # Re-raise the error for now (fail fast, but with context)
        raise
