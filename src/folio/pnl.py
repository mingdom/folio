"""
P&L calculation functions for positions and strategies.

This module provides functions to calculate profit and loss (P&L) for
individual positions and groups of positions (strategies) across a range
of underlying prices. It supports both stock and option positions.
"""

import datetime
from typing import Any

import numpy as np

from .data_model import OptionPosition, StockPosition
from .logger import logger
from .options import OptionContract, calculate_black_scholes_delta, calculate_bs_price


def calculate_position_pnl(
    position: StockPosition | OptionPosition,
    price_range: tuple[float, float] | None = None,
    num_points: int = 50,
    evaluation_date: datetime.datetime | None = None,  # noqa: ARG001 - kept for API compatibility
    use_cost_basis: bool = False,
) -> dict[str, Any]:
    """
    Calculate P&L for a single position across a range of underlying prices.

    Args:
        position: The position to calculate P&L for
        price_range: Optional tuple of (min_price, max_price). If None, auto-calculated.
        num_points: Number of price points to calculate
        evaluation_date: Date to evaluate P&L at. If None, uses current date.
        use_cost_basis: If True, use cost_basis as entry price. If False, use current price.

    Returns:
        Dictionary with price points and corresponding P&L values
    """
    # Determine price range if not provided
    if price_range is None:
        current_price = getattr(position, "price", 100)
        price_range = determine_price_range([position], current_price)

    min_price, max_price = price_range
    price_points = np.linspace(min_price, max_price, num_points)

    # Calculate P&L for each price point
    pnl_values = []

    for price in price_points:
        if isinstance(position, StockPosition):
            # For stock positions, P&L is linear
            if use_cost_basis:
                # Use cost_basis as entry price (for historical P&L tracking)
                entry_price = getattr(position, "cost_basis", position.price)
            else:
                # Use current price as entry price (for future P&L projections)
                entry_price = position.price
            pnl = (price - entry_price) * position.quantity
        elif isinstance(position, OptionPosition):
            # For option positions, calculate using QuantLib
            # Convert expiry string to datetime if needed
            if isinstance(position.expiry, str):
                try:
                    expiry_date = datetime.datetime.strptime(
                        position.expiry, "%Y-%m-%d"
                    )
                except ValueError:
                    logger.warning(f"Invalid expiry date format: {position.expiry}")
                    pnl = 0
                    continue
            else:
                expiry_date = position.expiry

            option_contract = OptionContract(
                underlying=position.ticker,  # Use ticker as underlying
                expiry=expiry_date,
                strike=position.strike,
                option_type=position.option_type,
                quantity=position.quantity,
                current_price=position.price,  # Use price attribute
                cost_basis=getattr(
                    position, "cost_basis", position.price
                ),  # Use cost_basis if available
                description=f"{position.ticker} {position.option_type} {position.strike}",  # Create description
            )

            # Calculate theoretical price at the given underlying price
            try:
                # Call calculate_bs_price without evaluation_date parameter
                theo_price = calculate_bs_price(
                    option_contract,
                    underlying_price=price,
                )

                # P&L = (current theoretical value - entry price) * quantity * 100
                # Each option contract controls 100 shares
                if use_cost_basis:
                    # Use cost_basis as entry price (for historical P&L tracking)
                    entry_price = getattr(position, "cost_basis", position.price)
                else:
                    # Use current price as entry price (for future P&L projections)
                    entry_price = position.price
                contract_multiplier = 100  # Standard contract size for equity options
                pnl = (
                    (theo_price - entry_price) * position.quantity * contract_multiplier
                )
            except Exception as e:
                logger.warning(
                    f"Error calculating option price for {position.ticker} {position.option_type} {position.strike}: {e}"
                )
                pnl = 0
        else:
            # Unsupported position type
            logger.warning(f"Unsupported position type: {type(position)}")
            pnl = 0

        pnl_values.append(pnl)

    return {
        "price_points": price_points.tolist(),
        "pnl_values": pnl_values,
        "position": position.to_dict() if hasattr(position, "to_dict") else {},
    }


def calculate_strategy_pnl(
    positions: list[StockPosition | OptionPosition],
    price_range: tuple[float, float] | None = None,
    num_points: int = 50,
    evaluation_date: datetime.datetime | None = None,
    use_cost_basis: bool = False,
) -> dict[str, Any]:
    """
    Calculate P&L for a group of positions (strategy) across a range of underlying prices.

    Args:
        positions: List of positions in the strategy
        price_range: Optional tuple of (min_price, max_price). If None, auto-calculated.
        num_points: Number of price points to calculate
        evaluation_date: Date to evaluate P&L at. If None, uses current date.
        use_cost_basis: If True, use cost_basis as entry price. If False, use current price.

    Returns:
        Dictionary with price points and corresponding P&L values
    """
    if not positions:
        return {"price_points": [], "pnl_values": [], "positions": []}

    # Ensure all positions have the same ticker
    tickers = set(p.ticker for p in positions)
    if len(tickers) > 1:
        logger.warning(f"Multiple tickers found in position group: {tickers}")

    # Determine price range if not provided
    if price_range is None:
        current_price = next(
            (getattr(p, "price", None) for p in positions if hasattr(p, "price")),
            100,
        )
        price_range = determine_price_range(positions, current_price)

    min_price, max_price = price_range
    price_points = np.linspace(min_price, max_price, num_points)

    # Calculate P&L for each position at each price point
    position_pnls = []
    for position in positions:
        position_pnl = calculate_position_pnl(
            position,
            price_range=(min_price, max_price),
            num_points=num_points,
            evaluation_date=evaluation_date,
            use_cost_basis=use_cost_basis,
        )
        position_pnls.append(position_pnl)

    # Combine P&L values for all positions
    # This is the most accurate way to calculate combined P&L
    combined_pnl = np.zeros(num_points)
    for pos_pnl in position_pnls:
        combined_pnl += np.array(pos_pnl["pnl_values"])

    # Create position summaries for the response
    position_summaries = [position.to_dict() for position in positions]

    return {
        "price_points": price_points.tolist(),
        "pnl_values": combined_pnl.tolist(),
        "individual_pnls": position_pnls,
        "positions": position_summaries,
    }


def determine_price_range(
    positions: list[StockPosition | OptionPosition],
    current_price: float,
    width_factor: float = 0.3,
) -> tuple[float, float]:
    """
    Determine an appropriate price range for P&L visualization.

    Args:
        positions: List of positions to consider
        current_price: Current price of the underlying
        width_factor: Factor to determine width of price range (0.3 = ±30%)

    Returns:
        Tuple of (min_price, max_price)
    """
    # Start with default range based on current price
    min_price = current_price * (1 - width_factor)
    max_price = current_price * (1 + width_factor)

    # Adjust range to include all option strikes
    for position in positions:
        if hasattr(position, "strike") and position.strike is not None:
            # Ensure we include the strike price with some margin
            strike = position.strike
            min_price = min(min_price, strike * 0.8)
            max_price = max(max_price, strike * 1.2)

    # Ensure min_price is never exactly zero to avoid division issues
    min_price = max(min_price, 0.0001)  # Use a small positive number instead of zero

    return (min_price, max_price)


def calculate_breakeven_points(pnl_data: dict[str, Any]) -> list[float]:
    """
    Calculate breakeven points from P&L data.

    Args:
        pnl_data: P&L data from calculate_strategy_pnl

    Returns:
        List of price points where P&L crosses zero
    """
    price_points = np.array(pnl_data["price_points"])
    pnl_values = np.array(pnl_data["pnl_values"])

    # Find where P&L crosses zero
    breakeven_points = []
    for i in range(1, len(pnl_values)):
        # If P&L changes sign between adjacent points
        if (pnl_values[i - 1] * pnl_values[i] <= 0) and (
            pnl_values[i - 1] != 0 or pnl_values[i] != 0
        ):
            # Linear interpolation to find the exact breakeven point
            if pnl_values[i] - pnl_values[i - 1] != 0:  # Avoid division by zero
                t = -pnl_values[i - 1] / (pnl_values[i] - pnl_values[i - 1])
                breakeven = price_points[i - 1] + t * (
                    price_points[i] - price_points[i - 1]
                )
                breakeven_points.append(breakeven)

    return breakeven_points


def analyze_asymptotic_behavior(positions: list) -> dict[str, bool]:
    """
    Analyze whether profit/loss is unbounded as price approaches extreme values.

    Uses the effective delta at very high and very low prices to determine
    if the P&L is bounded or unbounded in either direction.

    Args:
        positions: List of stock and option positions

    Returns:
        Dict with unbounded_profit and unbounded_loss flags
    """
    # Check if this is a SPY position for debugging
    is_spy_position = any(p.get("ticker", "") == "SPY" for p in positions)
    if is_spy_position:
        logger.info(f"SPY position detected with {len(positions)} positions")
        for i, pos in enumerate(positions):
            logger.info(
                f"Position {i}: {pos.get('ticker')} {pos.get('position_type')} {pos.get('option_type', '')} {pos.get('quantity')}"
            )

    # Use fixed extreme price points to approximate infinity and near-zero
    # This removes dependency on current_price and provides consistent behavior
    high_price = 1_000_000  # $1 million per share
    low_price = 0.0001  # A tenth of a cent per share - small but not zero to avoid division issues

    # Calculate the total "effective delta" at these extreme prices
    high_price_delta = 0
    low_price_delta = 0

    # For debugging, track individual position deltas
    position_deltas = []

    for position in positions:
        # For options, use their delta calculation
        if position.get("position_type") == "option":
            # Create an OptionContract for delta calculation
            # Parse expiry date from string format (assuming YYYY-MM-DD)
            expiry_str = position.get("expiration", "2025-01-01")
            if isinstance(expiry_str, str):
                try:
                    year, month, day = map(int, expiry_str.split("-"))
                    expiry = datetime.datetime(year, month, day)
                except (ValueError, AttributeError):
                    # Default to 1 year from now if parsing fails
                    expiry = datetime.datetime.now() + datetime.timedelta(days=365)
            elif isinstance(expiry_str, datetime.date):
                expiry = datetime.datetime.combine(
                    expiry_str, datetime.datetime.min.time()
                )
            else:
                # Default to 1 year from now
                expiry = datetime.datetime.now() + datetime.timedelta(days=365)

            option_contract = OptionContract(
                underlying=position.get("ticker", ""),
                expiry=expiry,
                strike=position.get("strike", 0),
                option_type=position.get("option_type", "CALL"),
                quantity=position.get("quantity", 0),
                current_price=position.get("price", 0),
                cost_basis=position.get("cost_basis", 0),
                description=position.get("description", ""),
            )

            # Get option type and quantity for delta calculation
            option_type = position.get("option_type", "")
            quantity = position.get("quantity", 0)

            # Calculate delta at extreme prices
            try:
                delta_at_high_price = calculate_black_scholes_delta(
                    option_contract, high_price
                )
                delta_at_low_price = calculate_black_scholes_delta(
                    option_contract, low_price
                )

                # Scale by position size (100 shares per contract)
                contract_multiplier = 100
                position_high_delta = (
                    delta_at_high_price * quantity * contract_multiplier
                )
                position_low_delta = delta_at_low_price * quantity * contract_multiplier
                high_price_delta += position_high_delta
                low_price_delta += position_low_delta

                # Track individual position deltas for debugging
                position_deltas.append({
                    "type": "option",
                    "option_type": position.get("option_type", ""),
                    "strike": position.get("strike", 0),
                    "quantity": quantity,
                    "high_delta": position_high_delta,
                    "low_delta": position_low_delta,
                })
            except Exception:
                # If delta calculation fails, use simplified approach based on option type
                if option_type == "CALL":
                    # For calls: delta approaches 1 at high prices, 0 at low prices
                    position_high_delta = 1 * quantity * 100
                    position_low_delta = 0
                    high_price_delta += position_high_delta
                    # No contribution at low prices (delta approaches 0)

                    # Track individual position deltas for debugging
                    position_deltas.append({
                        "type": "option (fallback)",
                        "option_type": "CALL",
                        "strike": position.get("strike", 0),
                        "quantity": quantity,
                        "high_delta": position_high_delta,
                        "low_delta": position_low_delta,
                    })
                elif option_type == "PUT":
                    # For puts: delta approaches 0 at high prices, -1 at low prices
                    position_high_delta = 0
                    position_low_delta = -1 * quantity * 100
                    low_price_delta += position_low_delta
                    # No contribution at high prices (delta approaches 0)

                    # Track individual position deltas for debugging
                    position_deltas.append({
                        "type": "option (fallback)",
                        "option_type": "PUT",
                        "strike": position.get("strike", 0),
                        "quantity": quantity,
                        "high_delta": position_high_delta,
                        "low_delta": position_low_delta,
                    })

        # For stocks, delta is always 1 (or -1 for short positions)
        elif position.get("position_type") == "stock":
            quantity = position.get("quantity", 0)
            position_high_delta = quantity
            position_low_delta = quantity
            high_price_delta += position_high_delta
            low_price_delta += position_low_delta

            # Track individual position deltas for debugging
            position_deltas.append({
                "type": "stock",
                "ticker": position.get("ticker", ""),
                "quantity": quantity,
                "high_delta": position_high_delta,
                "low_delta": position_low_delta,
            })

        # Skip unknown position types
        else:
            continue

    # Threshold for considering delta significant
    delta_threshold = 2.0  # Higher threshold to avoid false positives

    # Log delta values and position details for debugging
    logger.info(
        f"Delta values: high_price_delta={high_price_delta}, low_price_delta={low_price_delta}"
    )
    logger.info(f"Using delta_threshold={delta_threshold}")

    # Log individual position deltas
    logger.info("Individual position deltas:")
    for pos in position_deltas:
        logger.info(
            f"  {pos['type']} {pos.get('option_type', '')} {pos.get('strike', '')} qty={pos['quantity']}: high_delta={pos['high_delta']:.2f}, low_delta={pos['low_delta']:.2f}"
        )

    # Determine unbounded profit/loss based on delta
    unbounded_profit_high = high_price_delta > delta_threshold
    unbounded_loss_high = high_price_delta < -delta_threshold
    unbounded_profit_low = low_price_delta < -delta_threshold
    unbounded_loss_low = low_price_delta > delta_threshold

    # Log the final determination
    logger.info(
        f"Final determination: unbounded_profit_high={unbounded_profit_high}, unbounded_loss_high={unbounded_loss_high}, unbounded_profit_low={unbounded_profit_low}, unbounded_loss_low={unbounded_loss_low}"
    )

    return {
        "unbounded_profit_high": unbounded_profit_high,
        "unbounded_loss_high": unbounded_loss_high,
        "unbounded_profit_low": unbounded_profit_low,
        "unbounded_loss_low": unbounded_loss_low,
    }


def determine_boundedness(pnl_data: dict[str, Any]) -> tuple[bool, bool]:
    """
    Determine if profit/loss is unbounded based on position data.

    Args:
        pnl_data: P&L data from calculate_strategy_pnl containing positions

    Returns:
        Tuple of (unbounded_profit, unbounded_loss) flags

    Raises:
        ValueError: If positions data is not available in pnl_data
    """
    # Validate input - positions data must be available
    if "positions" not in pnl_data:
        logger.warning("No position data available for asymptotic analysis")
        raise ValueError("Position data is required for boundedness determination")

    # Log SPY positions for debugging
    is_spy = any(p.get("ticker", "") == "SPY" for p in pnl_data["positions"])
    if is_spy:
        logger.info(
            f"SPY position detected with {len(pnl_data['positions'])} positions"
        )

    # Get asymptotic behavior
    results = analyze_asymptotic_behavior(pnl_data["positions"])

    # Combine high/low results
    unbounded_profit = (
        results["unbounded_profit_high"] or results["unbounded_profit_low"]
    )
    unbounded_loss = results["unbounded_loss_high"] or results["unbounded_loss_low"]

    if is_spy:
        logger.info(f"SPY asymptotic results: {results}")
        logger.info(
            f"Final SPY determination: profit={unbounded_profit}, loss={unbounded_loss}"
        )

    return unbounded_profit, unbounded_loss


def calculate_max_profit_loss(pnl_data: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate maximum profit and loss from P&L data.

    Args:
        pnl_data: P&L data from calculate_strategy_pnl

    Returns:
        Dictionary with max_profit, max_loss, and their corresponding prices,
        plus flags indicating if profit or loss might be unbounded
    """
    # Log that we're calculating max profit/loss
    logger.info("Calculating max profit/loss")
    logger.info(f"pnl_data keys: {pnl_data.keys()}")

    price_points = pnl_data["price_points"]
    pnl_values = pnl_data["pnl_values"]

    if not pnl_values:
        return {
            "max_profit": 0,
            "max_profit_price": 0,
            "max_loss": 0,
            "max_loss_price": 0,
            "unbounded_profit": False,
            "unbounded_loss": False,
        }

    # Find max profit and its price
    max_profit = max(pnl_values)
    max_profit_idx = pnl_values.index(max_profit)
    max_profit_price = price_points[max_profit_idx]

    # Find max loss and its price
    max_loss = min(pnl_values)
    max_loss_idx = pnl_values.index(max_loss)
    max_loss_price = price_points[max_loss_idx]

    # Initialize unbounded flags
    unbounded_profit = False
    unbounded_loss = False

    # Determine if profit/loss is unbounded
    try:
        unbounded_profit, unbounded_loss = determine_boundedness(pnl_data)
    except ValueError:
        # Fallback to edge detection if no position data
        logger.warning("Falling back to edge detection for boundedness determination")
        # Profit is unbounded if max profit is at edge of price range
        unbounded_profit = (
            max_profit_idx == 0 or max_profit_idx == len(price_points) - 1
        )
        # Loss is unbounded if max loss is at edge of price range
        unbounded_loss = max_loss_idx == 0 or max_loss_idx == len(price_points) - 1

    return {
        "max_profit": max_profit,
        "max_profit_price": max_profit_price,
        "max_loss": max_loss,
        "max_loss_price": max_loss_price,
        "unbounded_profit": unbounded_profit,
        "unbounded_loss": unbounded_loss,
    }


def summarize_strategy_pnl(
    pnl_data: dict[str, Any], current_price: float
) -> dict[str, Any]:
    """
    Generate a summary of the P&L data for a strategy.

    Args:
        pnl_data: P&L data from calculate_strategy_pnl
        current_price: Current price of the underlying

    Returns:
        Dictionary with summary information
    """
    # Calculate breakeven points
    breakeven_points = calculate_breakeven_points(pnl_data)

    # Calculate max profit/loss
    max_pl = calculate_max_profit_loss(pnl_data)

    # Calculate P&L at current price
    price_points = np.array(pnl_data["price_points"])

    # Recalculate P&L values by summing individual position P&Ls for accuracy
    if "individual_pnls" in pnl_data:
        recalculated_pnl = np.zeros(len(price_points))
        for pos_pnl in pnl_data["individual_pnls"]:
            recalculated_pnl += np.array(pos_pnl["pnl_values"])
        # Update the pnl_data with recalculated values
        pnl_data["pnl_values"] = recalculated_pnl.tolist()
        pnl_values = recalculated_pnl
    else:
        pnl_values = np.array(pnl_data["pnl_values"])

    # Calculate P&L at current price by summing individual position P&Ls
    if len(price_points) > 0:
        closest_idx = np.abs(price_points - current_price).argmin()

        # Calculate current P&L by summing individual position P&Ls
        if "individual_pnls" in pnl_data:
            current_pnl = 0
            for pos_pnl in pnl_data["individual_pnls"]:
                current_pnl += pos_pnl["pnl_values"][closest_idx]

            # Update the pnl_data with the correct current P&L
            pnl_data["pnl_values"][closest_idx] = current_pnl
        else:
            current_pnl = pnl_values[closest_idx]
    else:
        current_pnl = 0

    # pnl_values is already recalculated above

    # Determine profitable price ranges
    profitable_ranges = []
    in_profitable_range = False
    range_start = None

    for i, (price, pnl) in enumerate(zip(price_points, pnl_values, strict=False)):
        if pnl > 0 and not in_profitable_range:
            # Start of a profitable range
            in_profitable_range = True
            range_start = price
        elif (pnl <= 0 or i == len(pnl_values) - 1) and in_profitable_range:
            # End of a profitable range
            in_profitable_range = False
            range_end = price
            profitable_ranges.append((range_start, range_end))

    return {
        "breakeven_points": breakeven_points,
        "max_profit": max_pl["max_profit"],
        "max_profit_price": max_pl["max_profit_price"],
        "max_loss": max_pl["max_loss"],
        "max_loss_price": max_pl["max_loss_price"],
        "unbounded_profit": max_pl.get("unbounded_profit", False),
        "unbounded_loss": max_pl.get("unbounded_loss", False),
        "current_pnl": current_pnl,
        "profitable_ranges": profitable_ranges,
    }
