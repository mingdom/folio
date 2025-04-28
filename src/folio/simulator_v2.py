"""
Portfolio simulator v2 module.

This module provides enhanced functionality for simulating portfolio performance
under different market scenarios using atomic, composable functions for accurate
pricing and valuation.
"""

import datetime
from typing import Any

from .data_model import OptionPosition, PortfolioGroup, StockPosition
from .logger import logger
from .marketdata import get_stock_price
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


def simulate_stock_position(
    position: StockPosition,
    new_price: float,
) -> dict[str, Any]:
    """
    Simulate a stock position with a new price.

    Args:
        position: Stock position to simulate
        new_price: New price of the underlying

    Returns:
        Dictionary with simulation results
    """
    # Calculate original value
    original_value = calculate_stock_value(position.quantity, position.price)

    # Calculate new value
    new_value = calculate_stock_value(position.quantity, new_price)

    # Calculate P&L
    pnl = calculate_stock_pnl(position.quantity, position.price, new_price)

    # Calculate P&L percentage
    pnl_percent = (pnl / original_value) * 100 if original_value else 0

    return {
        "ticker": position.ticker,
        "position_type": "stock",
        "original_price": position.price,
        "new_price": new_price,
        "original_value": original_value,
        "new_value": new_value,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
    }


def simulate_option_position(
    position: OptionPosition,
    new_underlying_price: float,
    current_underlying_price: float,  # Required parameter, no default value
) -> dict[str, Any]:
    """
    Simulate an option position with a new underlying price.

    Args:
        position: Option position to simulate
        new_underlying_price: New price of the underlying
        current_underlying_price: Current price of the underlying

    Returns:
        Dictionary with simulation results
    """
    # Calculate original value
    original_value = position.market_value

    # Convert expiry string to date if needed
    if isinstance(position.expiry, str):
        expiry_date = datetime.datetime.strptime(position.expiry, "%Y-%m-%d").date()
    else:
        expiry_date = position.expiry

    # Import from options module
    from .options import OptionContract, calculate_bs_price

    # Create a contract for the current option
    option_contract = OptionContract(
        underlying=position.ticker,
        expiry=expiry_date
        if isinstance(expiry_date, datetime.datetime)
        else datetime.datetime.combine(expiry_date, datetime.datetime.min.time()),
        strike=position.strike,
        option_type=position.option_type,
        quantity=position.quantity,
        current_price=position.price,
        description=f"{position.ticker} {position.option_type} {position.strike}",
    )

    # Calculate new value using the options module
    implied_volatility = getattr(position, "implied_volatility", 0.3)
    new_price = calculate_bs_price(
        option_contract,
        new_underlying_price,
        risk_free_rate=0.05,
        volatility=implied_volatility,
    )

    # Calculate new value (price per contract * quantity * 100 shares per contract)
    new_value = new_price * position.quantity * 100

    # Calculate P&L
    pnl = new_value - original_value

    # Calculate P&L percentage
    pnl_percent = (pnl / original_value) * 100 if original_value else 0

    return {
        "ticker": position.ticker,
        "position_type": "option",
        "option_type": position.option_type,
        "strike": position.strike,
        "expiry": position.expiry,
        "original_underlying_price": current_underlying_price,
        "new_underlying_price": new_underlying_price,
        "original_value": original_value,
        "new_value": new_value,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
    }


def simulate_position_group(
    position_group: PortfolioGroup,
    spy_change: float,
    stock_price: float,
) -> dict[str, Any]:
    """
    Simulate a position group with a given SPY change.

    Args:
        position_group: Position group to simulate
        spy_change: SPY price change as a decimal
        stock_price: Current stock price for the ticker

    Returns:
        Dictionary with simulation results
    """
    # Validate position group
    if not position_group.stock_position and not position_group.option_positions:
        raise ValueError(
            f"Cannot simulate empty position group for {position_group.ticker}"
        )

    # Validate stock price
    if stock_price <= 0:
        raise ValueError(
            f"Invalid stock price ({stock_price}) for {position_group.ticker}"
        )

    # Calculate price adjustment based on beta
    beta = position_group.beta
    price_adjustment = calculate_price_adjustment(spy_change, beta)

    # Calculate new underlying price
    new_price = calculate_underlying_price(stock_price, price_adjustment)

    # Initialize results
    position_results = []
    total_original_value = 0
    total_new_value = 0
    total_pnl = 0

    # Simulate stock position
    if position_group.stock_position:
        stock_result = simulate_stock_position(position_group.stock_position, new_price)
        position_results.append(stock_result)
        total_original_value += stock_result["original_value"]
        total_new_value += stock_result["new_value"]
        total_pnl += stock_result["pnl"]

    # Simulate option positions
    if position_group.option_positions:
        for option in position_group.option_positions:
            option_result = simulate_option_position(
                option, new_price, current_underlying_price=stock_price
            )
            position_results.append(option_result)
            total_original_value += option_result["original_value"]
            total_new_value += option_result["new_value"]
            total_pnl += option_result["pnl"]

    # Calculate group-level metrics
    if total_original_value == 0:
        raise ValueError(
            f"Total original value is zero for {position_group.ticker}, "
            "cannot calculate P&L percentage"
        )

    pnl_percent = (total_pnl / total_original_value) * 100

    return {
        "ticker": position_group.ticker,
        "beta": beta,
        "current_price": stock_price,  # Keep the key name for backward compatibility
        "new_price": new_price,
        "original_value": total_original_value,
        "new_value": total_new_value,
        "pnl": total_pnl,
        "pnl_percent": pnl_percent,
        "positions": position_results,
    }


def simulate_portfolio(
    portfolio_groups: list[PortfolioGroup],
    spy_changes: list[float],
    cash_value: float = 0.0,
) -> dict[str, Any]:
    """
    Simulate portfolio performance across different SPY price changes.

    This function calculates portfolio values at different SPY changes and
    uses the 0% SPY change scenario as the baseline for P&L calculations.
    This ensures that P&L is always zero at 0% SPY change, providing a
    consistent reference point.

    Note: Pending activity value is not included in the simulation to avoid
    artificial inflation of portfolio values.

    Args:
        portfolio_groups: Portfolio groups to simulate
        spy_changes: List of SPY price change percentages as decimals
        cash_value: Value of cash positions

    Returns:
        Dictionary with simulation results including:
        - spy_changes: The input SPY changes
        - portfolio_values: Portfolio values at each SPY change
        - portfolio_pnls: P&L values relative to the 0% baseline
        - portfolio_pnl_percents: P&L percentages relative to the 0% baseline
        - portfolio_pnl_vs_original_percents: P&L percentages relative to the original portfolio value
        - current_portfolio_value: The baseline portfolio value (at 0% SPY change)
        - original_portfolio_value: The original portfolio value (before simulation)
        - position_results: Detailed results for each position group
    """
    if not portfolio_groups:
        logger.warning("Cannot simulate an empty portfolio")
        return {
            "spy_changes": spy_changes,
            "portfolio_values": [cash_value] * len(spy_changes),
            "portfolio_pnls": [0.0] * len(spy_changes),
            "portfolio_pnl_percents": [0.0] * len(spy_changes),
            "portfolio_pnl_vs_original_percents": [0.0] * len(spy_changes),
            "current_portfolio_value": cash_value,
            "original_portfolio_value": cash_value,
            "position_results": {},
        }

    # Initialize results containers
    portfolio_values = []
    position_results = {group.ticker: [] for group in portfolio_groups}

    # We'll set a default original portfolio value that will be overridden
    # by the CLI with the actual portfolio value from the portfolio summary
    original_portfolio_value = cash_value
    for group in portfolio_groups:
        if group.stock_position:
            original_portfolio_value += group.stock_position.market_value
        for option in group.option_positions:
            original_portfolio_value += option.market_value

    # Find the index of 0% SPY change to use as baseline
    # If 0% is not in the list, we'll calculate baseline values separately
    zero_index = None
    for i, change in enumerate(spy_changes):
        if abs(change) < 0.001:  # Close to 0%
            zero_index = i
            break

    # Simulate for each SPY change
    for spy_change in spy_changes:
        portfolio_value = (
            cash_value  # Note: pending_activity_value is excluded from simulation
        )

        # Simulate each position group
        for group in portfolio_groups:
            stock_price = get_stock_price(group.ticker)
            group_result = simulate_position_group(group, spy_change, stock_price)
            portfolio_value += group_result["new_value"]
            position_results[group.ticker].append(group_result)

        # Store portfolio-level results
        portfolio_values.append(portfolio_value)

    baseline_value = portfolio_values[zero_index]

    # Calculate P&L values relative to the baseline
    portfolio_pnls = [value - baseline_value for value in portfolio_values]

    # Calculate P&L percentages (relative to baseline value)
    portfolio_pnl_percents = [
        (pnl / baseline_value) * 100 if baseline_value else 0 for pnl in portfolio_pnls
    ]

    # Calculate P&L percentages relative to original portfolio value
    # We need to calculate the percentage change relative to the original portfolio value
    portfolio_pnl_vs_original_percents = [
        (pnl / original_portfolio_value) * 100 if original_portfolio_value else 0
        for pnl in portfolio_pnls
    ]

    # For consistency with the rest of the codebase, include current_portfolio_value
    # This is the baseline value we calculated
    current_portfolio_value = baseline_value

    return {
        "spy_changes": spy_changes,
        "portfolio_values": portfolio_values,
        "portfolio_pnls": portfolio_pnls,
        "portfolio_pnl_percents": portfolio_pnl_percents,
        "portfolio_pnl_vs_original_percents": portfolio_pnl_vs_original_percents,
        "current_portfolio_value": current_portfolio_value,
        "original_portfolio_value": original_portfolio_value,
        "position_results": position_results,
    }
