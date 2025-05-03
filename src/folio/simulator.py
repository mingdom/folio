"""Portfolio simulator module.

This module provides functionality for simulating portfolio performance
under different market scenarios, particularly changes in the SPY index.
"""

import numpy as np

from .data_model import PortfolioGroup
from .logger import logger
from .portfolio import recalculate_portfolio_with_prices
from .portfolio_value import calculate_position_value_with_price_change


def simulate_portfolio_with_spy_changes(
    portfolio_groups: list[PortfolioGroup],
    spy_changes: list[float] | None = None,
    cash_like_positions: list[dict] | None = None,
    pending_activity_value: float = 0.0,
) -> dict:
    """Simulate portfolio performance across different SPY price changes.

    Args:
        portfolio_groups: Portfolio groups to simulate
        spy_changes: List of SPY price change percentages (e.g., [-0.3, -0.25, ..., 0.25, 0.3])
                    If None, uses default range from -30% to +30% in 5% increments
        cash_like_positions: Cash-like positions
        pending_activity_value: Value of pending activity

    Returns:
        Dictionary with simulation results containing:
        - 'spy_changes': List of SPY change percentages
        - 'portfolio_values': List of portfolio values at each SPY change
        - 'portfolio_exposures': List of portfolio exposures at each SPY change
        - 'current_value': Current portfolio value (at 0% change)
        - 'current_exposure': Current portfolio exposure (at 0% change)
    """
    if not portfolio_groups:
        logger.warning("Cannot simulate an empty portfolio")
        return {
            "spy_changes": [],
            "portfolio_values": [],
            "portfolio_exposures": [],
            "current_value": 0.0,
            "current_exposure": 0.0,
        }

    # Use default SPY changes if none provided
    if spy_changes is None:
        spy_changes = np.arange(-0.30, 0.31, 0.05).tolist()

    # Initialize results
    portfolio_values = []
    portfolio_exposures = []

    # Initialize position-level tracking
    position_values = {}  # ticker -> list of values at each SPY change
    position_exposures = {}  # ticker -> list of exposures at each SPY change
    position_details = {}  # ticker -> details about the position

    # Initialize with all tickers in the portfolio
    for group in portfolio_groups:
        ticker = group.ticker
        position_values[ticker] = []
        position_exposures[ticker] = []

        # Store position details
        stock_value = group.stock_position.market_value if group.stock_position else 0
        option_value = (
            sum(op.market_value for op in group.option_positions)
            if group.option_positions
            else 0
        )
        total_value = stock_value + option_value

        position_details[ticker] = {
            "beta": group.beta,
            "initial_value": total_value,
            "has_stock": group.stock_position is not None,
            "has_options": len(group.option_positions) > 0
            if group.option_positions
            else False,
            "stock_quantity": group.stock_position.quantity
            if group.stock_position
            else 0,
            "stock_price": group.stock_position.price if group.stock_position else 0,
            "option_count": len(group.option_positions)
            if group.option_positions
            else 0,
        }

    # Get current portfolio value and exposure (at 0% change)
    current_value = 0.0
    current_exposure = 0.0
    zero_index = None

    # Simulate for each SPY change
    for i, spy_change in enumerate(spy_changes):
        # Store the index of 0% change
        if abs(spy_change) < 0.001:
            zero_index = i

        # Calculate price adjustments for each ticker based on its beta
        price_adjustments = {}
        for group in portfolio_groups:
            # Use the group's beta to calculate price adjustment
            beta = group.beta
            price_adjustment = 1.0 + (spy_change * beta)
            price_adjustments[group.ticker] = price_adjustment

        # Convert StockPosition objects to dictionaries if needed
        cash_like_dicts = []
        if cash_like_positions:
            for pos in cash_like_positions:
                if hasattr(pos, "to_dict"):
                    # It's a StockPosition object
                    cash_like_dicts.append({
                        "ticker": pos.ticker,
                        "quantity": pos.quantity,
                        "beta": pos.beta,
                        "market_value": pos.market_value,
                        "beta_adjusted_exposure": pos.beta_adjusted_exposure,
                        "price": pos.price,
                    })
                else:
                    # It's already a dictionary
                    cash_like_dicts.append(pos)

        # Recalculate portfolio with adjusted prices
        recalculated_groups, recalculated_summary = recalculate_portfolio_with_prices(
            portfolio_groups, price_adjustments, cash_like_dicts, pending_activity_value
        )

        # Store portfolio-level results
        portfolio_values.append(recalculated_summary.portfolio_estimate_value)
        portfolio_exposures.append(recalculated_summary.net_market_exposure)

        # Store position-level results
        for group in recalculated_groups:
            ticker = group.ticker

            # Calculate total position value
            stock_value = (
                group.stock_position.market_value if group.stock_position else 0
            )
            option_value = (
                sum(op.market_value for op in group.option_positions)
                if group.option_positions
                else 0
            )
            total_value = stock_value + option_value

            # Store values
            position_values[ticker].append(total_value)
            position_exposures[ticker].append(group.net_exposure)

            # Store additional details for the 0% change case
            if abs(spy_change) < 0.001:
                position_details[ticker].update({
                    "current_value": total_value,
                    "current_exposure": group.net_exposure,
                    "stock_value": stock_value,
                    "option_value": option_value,
                })

        # Store current values (at 0% change)
        if abs(spy_change) < 0.001:  # Close to 0%
            current_value = recalculated_summary.portfolio_estimate_value
            current_exposure = recalculated_summary.net_market_exposure

    # Calculate position-level changes
    position_changes = {}
    if zero_index is not None:
        for ticker, values in position_values.items():
            if len(values) > zero_index:
                base_value = values[zero_index]
                changes = [value - base_value for value in values]
                pct_changes = calculate_percentage_changes(values, base_value)

                position_changes[ticker] = {
                    "values": values,
                    "changes": changes,
                    "pct_changes": pct_changes,
                }

    return {
        "spy_changes": spy_changes,
        "portfolio_values": portfolio_values,
        "portfolio_exposures": portfolio_exposures,
        "current_value": current_value,
        "current_exposure": current_exposure,
        "position_values": position_values,
        "position_exposures": position_exposures,
        "position_details": position_details,
        "position_changes": position_changes,
    }


def calculate_percentage_changes(values: list[float], base_value: float) -> list[float]:
    """Calculate percentage changes relative to a base value.

    Args:
        values: List of values
        base_value: Base value to calculate percentage changes from

    Returns:
        List of percentage changes
    """
    if base_value == 0:
        return [0.0] * len(values)

    return [(value / base_value - 1.0) * 100.0 for value in values]


def generate_spy_changes(range_pct: float, steps: int) -> list[float]:
    """Generate a list of SPY changes for simulation.

    Args:
        range_pct: Range of SPY changes in percent (e.g., 20.0 for ±20%)
        steps: Number of steps in the simulation

    Returns:
        List of SPY changes as decimals (e.g., [-0.2, -0.1, 0.0, 0.1, 0.2])
    """
    # Calculate the step size
    step_size = (2 * range_pct) / (steps - 1) if steps > 1 else 0

    # Generate the SPY changes
    spy_changes = [-range_pct + i * step_size for i in range(steps)]

    # Ensure we have a zero point
    if 0.0 not in spy_changes and steps > 2:
        # Find the closest point to zero and replace it with zero
        closest_to_zero = min(spy_changes, key=abs)
        zero_index = spy_changes.index(closest_to_zero)
        spy_changes[zero_index] = 0.0

    # Convert to percentages
    spy_changes = [change / 100.0 for change in spy_changes]

    return spy_changes


def simulate_position_with_spy_changes(
    position_group: PortfolioGroup, spy_changes: list[float]
) -> dict:
    """Simulate a position with SPY changes.

    Args:
        position_group: PortfolioGroup to simulate
        spy_changes: List of SPY changes as decimals

    Returns:
        Dictionary with simulation results
    """

    ticker = position_group.ticker
    beta = position_group.beta
    current_value = position_group.net_exposure

    # Calculate position values at different SPY changes
    values = []
    for spy_change in spy_changes:
        # Calculate the price change for this position based on beta
        price_change = spy_change * beta

        # Calculate the new position value
        new_value = calculate_position_value_with_price_change(
            position_group, price_change
        )
        values.append(new_value)

    # Calculate changes from current value
    changes = [value - current_value for value in values]
    pct_changes = [
        (change / current_value) * 100 if current_value != 0 else 0
        for change in changes
    ]

    # Find min and max values
    min_value = min(values)
    max_value = max(values)
    min_index = values.index(min_value)
    max_index = values.index(max_value)
    min_spy_change = spy_changes[min_index] * 100  # Convert to percentage
    max_spy_change = spy_changes[max_index] * 100  # Convert to percentage

    # Create results dictionary
    results = {
        "ticker": ticker,
        "beta": beta,
        "current_value": current_value,
        "spy_changes": spy_changes,
        "values": values,
        "changes": changes,
        "pct_changes": pct_changes,
        "min_value": min_value,
        "max_value": max_value,
        "min_spy_change": min_spy_change,
        "max_spy_change": max_spy_change,
    }

    return results
