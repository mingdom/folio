"""
Portfolio simulator v2 module.

This module provides enhanced functionality for simulating portfolio performance
under different market scenarios using atomic, composable functions for accurate
pricing and valuation.
"""

import datetime

from .options import OptionContract, calculate_bs_price


def calculate_price_adjustment(spy_change: float, beta: float) -> float:
    """
    Calculate price adjustment factor based on SPY change and beta.

    Args:
        spy_change: SPY price change as a decimal (e.g., 0.05 for 5% increase)
        beta: Beta of the position

    Returns:
        Price adjustment factor (e.g., 1.05 for 5% increase)
    """
    return 1.0 + (spy_change * beta)


def calculate_underlying_price(current_price: float, adjustment_factor: float) -> float:
    """
    Calculate new underlying price based on current price and adjustment factor.

    Args:
        current_price: Current price of the underlying
        adjustment_factor: Price adjustment factor

    Returns:
        New underlying price
    """
    return current_price * adjustment_factor


def calculate_stock_value(quantity: float, price: float) -> float:
    """
    Calculate the market value of a stock position.

    Args:
        quantity: Number of shares
        price: Price per share

    Returns:
        Market value of the stock position
    """
    return quantity * price


def calculate_stock_pnl(
    quantity: float, entry_price: float, current_price: float
) -> float:
    """
    Calculate the profit/loss for a stock position.

    Args:
        quantity: Number of shares
        entry_price: Entry price per share
        current_price: Current price per share

    Returns:
        Profit/loss amount
    """
    return quantity * (current_price - entry_price)


def prepare_contract_for_pricing(
    option_type: str,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
) -> OptionContract:
    """
    Create an option contract and prepare it for pricing.

    This function handles the conversion between date and datetime
    and sets the underlying_price attribute.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Expiration date
        underlying_price: Price of the underlying asset

    Returns:
        An OptionContract object ready for pricing
    """
    # Convert date to datetime if needed
    if isinstance(expiry, datetime.date) and not isinstance(expiry, datetime.datetime):
        expiry_datetime = datetime.datetime.combine(
            expiry, datetime.datetime.min.time()
        )
    else:
        expiry_datetime = expiry

    # Create an option contract
    contract = OptionContract(
        underlying="TEMP",  # Temporary underlying ticker
        option_type=option_type,
        strike=strike,
        expiry=expiry_datetime,
        quantity=1,  # We'll handle quantity separately
        current_price=0.0,  # We'll calculate this
        description=f"TEMP {option_type} {strike}",
    )

    # Set the underlying price as an attribute
    contract.underlying_price = underlying_price

    return contract


def calculate_option_value(
    option_type: str,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    quantity: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate the theoretical value of an option using Black-Scholes.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Expiration date
        underlying_price: Price of the underlying asset
        quantity: Number of contracts
        volatility: Implied volatility (default: 0.3)
        risk_free_rate: Risk-free interest rate (default: 0.05)

    Returns:
        Theoretical value of the option position
    """
    # Prepare the contract for pricing
    contract = prepare_contract_for_pricing(
        option_type, strike, expiry, underlying_price
    )

    # Calculate option price using Black-Scholes
    option_price = calculate_bs_price(
        contract, underlying_price, risk_free_rate, volatility
    )

    # Calculate position value (each contract is for 100 shares)
    return option_price * quantity * 100


def calculate_option_pnl(
    option_type: str,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    quantity: float,
    entry_price: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate the profit/loss for an option position.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Expiration date
        underlying_price: Price of the underlying asset
        quantity: Number of contracts
        entry_price: Entry price per contract
        volatility: Implied volatility (default: 0.3)
        risk_free_rate: Risk-free interest rate (default: 0.05)

    Returns:
        Profit/loss amount
    """
    # Calculate current option value
    current_value = calculate_option_value(
        option_type,
        strike,
        expiry,
        underlying_price,
        quantity,
        volatility,
        risk_free_rate,
    )

    # Calculate entry value
    entry_value = entry_price * quantity * 100

    # Calculate P&L
    return current_value - entry_value
