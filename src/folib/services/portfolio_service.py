"""
Portfolio processing service.

This module provides high-level functions for portfolio processing, including:
- Processing raw portfolio holdings into a structured portfolio
- Creating portfolio groups that combine related positions
- Calculating portfolio summary metrics
- Computing exposure metrics for risk analysis

Important Implementation Notes:
---------------------
1. CSV Structure Handling:
   - Supports varying CSV formats with different column structures
   - Handles duplicate columns in CSV headers (e.g. 'Type' appearing twice)
   - Processes 'Pending Activity' entries with flexible value location
   - Supports both normal and quoted currency values

2. Data Processing Flow:
   - Holdings are first parsed from CSV by the loader module
   - Holdings are then categorized into different position types
   - Related positions are grouped (e.g. stocks with their options)
   - Portfolio summary and exposure metrics are calculated
   - Special handling for cash-like positions (e.g. SPAXX, FMPXX)

3. Key Features:
   - Uses immutable data structures for thread safety
   - Separates data loading from business logic
   - Provides clear interfaces between components
   - Follows functional programming principles where possible

Old Codebase References:
------------------------
- src/folio/portfolio.py: Original process_portfolio_data function
- src/folio/portfolio_value.py: Portfolio value and metric calculations
- src/folio/data_model.py: Original Position, PortfolioGroup, and PortfolioSummary classes
"""

import logging
import re
from datetime import date

import pandas as pd

from ..data.loader import clean_currency_value
from ..data.stock import stockdata
from ..domain import (
    OptionPosition,
    Portfolio,
    PortfolioHolding,
    PortfolioSummary,
    Position,
    StockPosition,
)

# Set up logging
logger = logging.getLogger(__name__)


def process_portfolio(
    holdings: list[PortfolioHolding],
    # update_prices parameter is reserved for future implementation
    # where we'll update prices from market data
    update_prices: bool = True,  # noqa: ARG001
) -> Portfolio:
    """
    Process raw portfolio holdings into a structured portfolio.

    Processing Steps:
    1. Identify cash-like positions (SPAXX, FMPXX, etc.)
    2. Identify unknown/invalid positions
    3. Process pending activity entries
       - Handles multiple CSV formats
       - Checks various columns for pending activity value
       - Validates only one pending activity entry exists
    4. Group related positions (stocks with their options)
    5. Create portfolio object with all positions

    CSV Structure Handling:
    - Supports varying column structures in input CSVs
    - Handles pending activity values in different columns
    - Processes cash positions with special symbols

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()
        update_prices: Whether to update prices from market data (default: True)
                      Reserved for future implementation.

    Returns:
        Portfolio: Structured portfolio with categorized positions and groups

    Raises:
        ValueError: If multiple pending activity entries are found
    """
    logger.debug("Processing portfolio with %d holdings", len(holdings))

    # Separate different types of holdings
    non_cash_holdings = []
    cash_positions = []
    unknown_positions = []
    pending_activity_value = 0.0
    pending_activity_found = False

    for holding in holdings:
        # Check for pending activity
        if _is_pending_activity(holding.symbol):
            if pending_activity_found:
                raise ValueError(
                    f"Multiple pending activity holdings found: {holding.symbol}"
                )
            pending_activity_value = get_pending_activity(holding)
            pending_activity_found = True
            logger.debug(
                f"Identified pending activity: {holding.symbol} with value {pending_activity_value}"
            )
            continue

        # Check for cash-like positions
        if stockdata.is_cash_like(holding.symbol, holding.description):
            # Convert to CashPosition for cash-like holdings
            from ..domain import CashPosition

            cash_position = CashPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            cash_positions.append(cash_position)
            logger.debug(f"Identified cash-like position: {holding.symbol}")
        # Check for option positions - look for option-related terms in description
        elif (
            "CALL" in holding.description.upper()
            or "PUT" in holding.description.upper()
            or holding.symbol.strip().startswith(
                "-"
            )  # Fidelity option symbols start with hyphen
        ):
            # Options will be processed later
            non_cash_holdings.append(holding)
            logger.debug(f"Identified option position: {holding.symbol}")
        elif stockdata.is_valid_stock_symbol(holding.symbol):
            logger.debug(f"Identified stock position: {holding.symbol}")
            non_cash_holdings.append(holding)
        # Check for unknown/invalid positions
        else:
            # Convert to UnknownPosition
            from ..domain import UnknownPosition

            unknown_position = UnknownPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                description=holding.description,
                cost_basis=holding.cost_basis_total,
            )
            unknown_positions.append(unknown_position)
            logger.info(f"Identified unknown position: {holding.symbol}")

    # Process non-cash, non-unknown holdings directly
    positions = []

    # Process stock positions
    for holding in non_cash_holdings:
        # Check if this is a stock (not an option)
        if (
            "CALL" not in holding.description.upper()
            and "PUT" not in holding.description.upper()
            and not holding.symbol.strip().startswith("-")
        ):
            # Create stock position
            stock_position = StockPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            positions.append(stock_position)
            logger.debug(f"Created stock position for {holding.symbol}")

    # Process option positions
    for holding in non_cash_holdings:
        # Check if this is an option
        if (
            "CALL" in holding.description.upper()
            or "PUT" in holding.description.upper()
            or holding.symbol.strip().startswith("-")
        ):
            try:
                # Extract option data from description
                description = holding.description

                # Try to extract data from the description (e.g., "AMZN MAY 16 2025 $190 CALL")
                match = re.search(
                    r"([A-Z]+)\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})\s+(\d{4})\s+\$(\d+(?:\.\d+)?)\s+(CALL|PUT)",
                    description,
                    re.IGNORECASE,
                )

                if match:
                    ticker = match.group(1)
                    month_str = match.group(2).upper()
                    day = int(match.group(3))
                    year = int(match.group(4))
                    strike = float(match.group(5))
                    option_type = match.group(6).upper()
                    quantity = holding.quantity

                    # Convert month string to month number
                    month_map = {
                        "JAN": 1,
                        "FEB": 2,
                        "MAR": 3,
                        "APR": 4,
                        "MAY": 5,
                        "JUN": 6,
                        "JUL": 7,
                        "AUG": 8,
                        "SEP": 9,
                        "OCT": 10,
                        "NOV": 11,
                        "DEC": 12,
                    }
                    month = month_map[month_str]

                    # Create expiry date
                    expiry = date(year, month, day)

                    # Create option position
                    option_position = OptionPosition(
                        ticker=ticker,
                        quantity=quantity,
                        strike=strike,
                        expiry=expiry,
                        option_type=option_type,
                        price=holding.price,
                        cost_basis=holding.cost_basis_total,
                    )
                    positions.append(option_position)
                    logger.debug(f"Created option position for {holding.symbol}")
                else:
                    logger.warning(
                        f"Could not parse option data from description: {description}"
                    )
            except Exception as e:
                logger.warning(
                    f"Could not create option position for {holding.symbol}: {e}"
                )

    # Add cash and unknown positions
    positions.extend(cash_positions)
    positions.extend(unknown_positions)

    # Create and return the portfolio
    portfolio = Portfolio(
        positions=positions,
        pending_activity_value=pending_activity_value,
    )

    logger.debug(
        f"Portfolio processing complete: {len(positions)} positions ({len(cash_positions)} cash, {len(unknown_positions)} unknown)"
    )
    return portfolio


# create_portfolio_groups function has been removed as part of the migration to the new data model.
# Use group_positions_by_ticker() instead.


def create_portfolio_summary(portfolio: Portfolio) -> PortfolioSummary:
    """
    Create summary metrics for the portfolio including values and exposures.

    Summary Calculation:
    1. Calculate position values by type (stock, option, cash)
    2. Process pending activity values
    3. Calculate exposure metrics
    4. Compute portfolio beta and market exposure

    Special Handling:
    - Treats certain symbols as cash (SPAXX, FMPXX, etc.)
    - Handles NaN values in cash positions
    - Processes both positive and negative pending activity
    - Calculates beta-adjusted exposures

    Args:
        portfolio: Portfolio to summarize

    Returns:
        PortfolioSummary: Summary metrics including values and exposures
    """
    logger.debug("Creating portfolio summary")

    # Import calculation functions
    from ..calculations.exposure import (
        calculate_beta_adjusted_exposure,
        calculate_option_exposure,
        calculate_stock_exposure,
    )
    from ..calculations.options import (
        calculate_option_delta,
        categorize_option_by_delta,
    )

    # Initialize exposure breakdowns
    long_stocks = {"value": 0.0, "beta_adjusted": 0.0}
    short_stocks = {"value": 0.0, "beta_adjusted": 0.0}  # Will contain negative values
    long_options = {"value": 0.0, "beta_adjusted": 0.0, "delta_exposure": 0.0}
    short_options = {
        "value": 0.0,
        "beta_adjusted": 0.0,
        "delta_exposure": 0.0,
    }  # Will contain negative values

    # Initialize other metrics
    cash_value = 0.0
    unknown_value = 0.0

    # Process positions by type
    for position in portfolio.positions:
        # Handle NaN values for cash positions
        position_value = position.market_value
        if pd.isna(position_value):
            if position.position_type == "cash":
                # For cash positions with NaN value, try to get the value from the CSV file
                # This is a workaround for SPAXX** and similar cash positions
                logger.warning(
                    f"Cash position {position.ticker} has NaN market value, setting to 0"
                )
                position_value = 0.0
            else:
                logger.warning(
                    f"Skipping position {position.ticker} with NaN market value"
                )
                continue

        # Process based on position type
        if position.position_type == "stock":
            # Check if this is a cash-like position (e.g., money market fund)
            # In the old implementation, positions like FMPXX and FZDXX are treated as cash
            if stockdata.is_cash_like(
                position.ticker, getattr(position, "description", "")
            ):
                logger.debug(
                    f"Treating {position.ticker} as cash position in summary calculation"
                )
                cash_value += position_value
                continue

            # Get beta for exposure calculation
            beta = 1.0
            try:
                beta = stockdata.get_beta(position.ticker)
            except Exception as e:
                logger.warning(f"Could not get beta for {position.ticker}: {e}")

            # In the old implementation, stock values are based on market_value, not calculated exposure
            # This is a key difference that affects the total stock value calculation
            position_value = position.market_value

            # Calculate beta-adjusted exposure for reporting
            market_exposure = calculate_stock_exposure(
                position.quantity, position.price
            )
            beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)

            if position.quantity > 0:
                # Use market_value for value calculation, not calculated exposure
                long_stocks["value"] += position_value
                long_stocks["beta_adjusted"] += beta_adjusted
            else:
                # Use market_value for value calculation, not calculated exposure
                short_stocks["value"] += position_value  # Already negative
                short_stocks["beta_adjusted"] += beta_adjusted  # Already negative

        elif position.position_type == "option":
            # Get underlying price and beta
            beta = 1.0
            try:
                underlying_price = stockdata.get_price(position.ticker)
                beta = stockdata.get_beta(position.ticker)
            except Exception as e:
                logger.warning(f"Could not get market data for {position.ticker}: {e}")
                # Fallback to using a reasonable proxy for underlying price
                underlying_price = position.strike  # Using strike as fallback

            # Calculate option exposures using the calculation module with fallback
            delta = calculate_option_delta(
                option_type=position.option_type,
                strike=position.strike,
                expiry=position.expiry,
                underlying_price=underlying_price,
                volatility=None,  # Use default volatility
            )
            logger.debug(
                f"Option delta for {position.ticker} {position.option_type} {position.strike}: {delta}"
            )
            # Use underlying price for exposure calculation, not option price
            market_exposure = calculate_option_exposure(
                quantity=position.quantity,
                underlying_price=underlying_price,  # Use underlying price, not option price
                delta=delta,
            )
            logger.debug(
                f"Option exposure for {position.ticker} {position.option_type} {position.strike}: {market_exposure} (delta: {delta}, underlying: {underlying_price})"
            )
            beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)

            # In the old implementation (src/folio/portfolio_value.py), options are categorized
            # based on delta exposure, not quantity or market value:
            # - Positive delta exposure (long calls, short puts) => Long position
            # - Negative delta exposure (short calls, long puts) => Short position
            option_category = categorize_option_by_delta(delta)

            if (
                option_category == "long"
            ):  # Positive delta = Long position (regardless of quantity)
                # For long positions with positive delta (long calls, short puts)
                # or short positions with negative delta (short puts)
                long_options["value"] += position_value
                long_options["beta_adjusted"] += beta_adjusted
                # Store the actual market_exposure value with its sign
                # This preserves the sign semantics which are important
                long_options["delta_exposure"] += market_exposure
                logger.debug(
                    f"Categorized as LONG option exposure: {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {market_exposure})"
                )
            else:  # option_category == "short" - Negative delta = Short position (regardless of quantity)
                # For long positions with negative delta (long puts)
                # or short positions with positive delta (short calls)
                # In the old implementation, short option values are stored as negative values
                # This is critical for matching the old implementation's behavior
                short_options["value"] += (
                    position_value  # Store as is (already negative for short positions)
                )
                short_options["beta_adjusted"] += (
                    beta_adjusted  # Already negative from market_exposure
                )
                # Store the actual market_exposure value with its sign
                # For short options, this should already be negative
                # If it's not, we'll negate it to ensure it's stored as negative
                if market_exposure > 0:
                    # If somehow the market_exposure is positive for a short option,
                    # we'll negate it to ensure it's stored as negative
                    short_options["delta_exposure"] += -market_exposure
                    logger.debug(
                        f"Categorized as SHORT option exposure (negated positive exposure): {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {-market_exposure})"
                    )
                else:
                    # If market_exposure is already negative, use it as is
                    short_options["delta_exposure"] += market_exposure
                    logger.debug(
                        f"Categorized as SHORT option exposure: {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {market_exposure})"
                    )

        elif position.position_type == "cash":
            cash_value += position_value

        else:  # unknown
            unknown_value += position_value
            logger.debug(f"Unknown position type for {position.ticker}")

    # Calculate value breakdowns (moved from calculations/portfolio.py)
    # Calculate long value (positive exposure)
    long_value = long_stocks["value"]

    # Calculate short value (negative exposure)
    short_value = short_stocks["value"]

    # Calculate options value (both long and short)
    long_options["value"] + short_options["value"]

    # Calculate net market exposure (moved from calculations/portfolio.py)
    net_market_exposure = long_value - short_value

    # We don't need to calculate short percentage anymore
    # The percentage calculations are now done by dividing by total portfolio value

    # Calculate total value - in the old implementation, the total value is calculated as:
    # stock_value + option_value + cash_value + pending_activity_value
    # where stock_value and option_value preserve the sign of the positions
    total_value = (
        long_stocks["value"]  # Positive value
        + short_stocks["value"]  # Negative value
        + long_options["value"]  # Positive value
        + short_options["value"]  # Negative value
        + cash_value
        + unknown_value
    )

    # Handle NaN or None values in pending_activity_value
    pending_activity = portfolio.pending_activity_value
    if pending_activity is None or pd.isna(pending_activity):
        pending_activity = 0.0
    else:
        total_value += pending_activity

    # Create and return the portfolio summary
    # In the old implementation, stock_value is calculated as the sum of all stock position market values
    # (with short positions having negative market values)
    # Option_value is calculated as long_options["value"] + short_options["value"]
    # (with short_options["value"] being negative)

    # In the old implementation, net_market_exposure is calculated from the exposure breakdowns
    # which use delta exposure for options, not market value
    # We need to use the same approach to match the old implementation

    # Calculate exposures using the get_portfolio_exposures function
    exposures = get_portfolio_exposures(portfolio)

    # Get the net market exposure from the exposures calculation
    net_market_exposure = exposures["net_market_exposure"]

    # Get the beta-adjusted exposure from the exposures calculation
    beta_adjusted_exposure = exposures["beta_adjusted_exposure"]

    # Calculate net exposure percentage
    net_exposure_pct = (net_market_exposure / total_value) if total_value > 0 else 0.0

    summary = PortfolioSummary(
        total_value=total_value,
        stock_value=long_stocks["value"]
        + short_stocks["value"],  # Sum of all stock values, preserving sign
        option_value=long_options["value"]
        + short_options["value"],  # Note: short_options["value"] is negative
        cash_value=cash_value,
        unknown_value=unknown_value,
        pending_activity_value=pending_activity,  # Use the fixed pending_activity value
        net_market_exposure=net_market_exposure,
        net_exposure_pct=net_exposure_pct,
        beta_adjusted_exposure=beta_adjusted_exposure,
    )

    logger.debug("Portfolio summary created successfully")
    return summary


def get_portfolio_exposures(portfolio: Portfolio) -> dict:
    """
    Calculate exposure metrics for a portfolio.

    This function calculates various exposure metrics for the portfolio, including:
    - Long stock exposure
    - Short stock exposure
    - Long option exposure
    - Short option exposure
    - Net market exposure
    - Beta-adjusted exposure
    - Total value (for percentage calculations)

    Args:
        portfolio: The portfolio to analyze

    Returns:
        Dictionary with exposure metrics
    """
    logger.debug("Calculating portfolio exposures")

    # Import calculation functions
    from ..calculations.exposure import (
        calculate_beta_adjusted_exposure,
        calculate_option_exposure,
        calculate_stock_exposure,
    )
    from ..calculations.options import calculate_option_delta

    # Calculate total portfolio value for percentage calculations
    # This is needed for the CLI to calculate percentages correctly
    total_value = sum(p.market_value for p in portfolio.positions)

    # Add pending activity value if available
    if portfolio.pending_activity_value is not None and not pd.isna(
        portfolio.pending_activity_value
    ):
        total_value += portfolio.pending_activity_value

    # Initialize exposure metrics
    exposures = {
        "long_stock_exposure": 0.0,
        "short_stock_exposure": 0.0,
        "long_option_exposure": 0.0,
        "short_option_exposure": 0.0,
        "net_market_exposure": 0.0,
        "beta_adjusted_exposure": 0.0,
        "total_value": total_value,  # Add total value for percentage calculations
    }

    # Process stock positions
    for position in portfolio.stock_positions:
        # Skip cash-like positions (e.g., money market funds)
        if stockdata.is_cash_like(
            position.ticker, getattr(position, "description", "")
        ):
            logger.debug(
                f"Skipping cash-like position {position.ticker} in exposure calculation"
            )
            continue

        # Calculate stock exposure using the calculation module
        market_exposure = calculate_stock_exposure(position.quantity, position.price)

        # Get beta for exposure calculation
        try:
            beta = stockdata.get_beta(position.ticker)
        except Exception as e:
            logger.warning(f"Could not calculate beta for {position.ticker}: {e}")
            beta = 1.0  # Use beta of 1.0 as fallback

        # Calculate beta-adjusted exposure
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        exposures["beta_adjusted_exposure"] += beta_adjusted

        if market_exposure > 0:
            exposures["long_stock_exposure"] += market_exposure
        else:
            # Store short exposure with its negative sign
            exposures["short_stock_exposure"] += market_exposure

    # Process option positions
    for position in portfolio.option_positions:
        # Get underlying price and beta
        try:
            underlying_price = stockdata.get_price(position.ticker)
            beta = stockdata.get_beta(position.ticker)
        except Exception as e:
            logger.warning(f"Could not get market data for {position.ticker}: {e}")
            # Fallback to using strike as proxy for underlying price
            underlying_price = position.strike
            beta = 1.0  # Use beta of 1.0 as fallback

        # Calculate option exposures using the calculation modules with fallback
        delta = calculate_option_delta(
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=underlying_price,
            volatility=None,  # Use default volatility
        )
        logger.debug(
            f"Exposure calculation - Option delta for {position.ticker} {position.option_type} {position.strike}: {delta}"
        )
        # Use underlying price for exposure calculation, not option price
        market_exposure = calculate_option_exposure(
            quantity=position.quantity,
            underlying_price=underlying_price,  # Use underlying price, not option price
            delta=delta,
        )
        logger.debug(
            f"Portfolio exposure - Option exposure for {position.ticker} {position.option_type} {position.strike}: {market_exposure} (delta: {delta}, underlying: {underlying_price})"
        )
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        exposures["beta_adjusted_exposure"] += beta_adjusted

        # Instead of categorizing options and using abs(), we'll directly use the sign of the exposure
        # This is more aligned with the principle of storing values with their natural signs
        if market_exposure > 0:
            # Positive exposure contributes to long exposure
            exposures["long_option_exposure"] += market_exposure
            logger.debug(
                f"Added to LONG option exposure: {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {market_exposure})"
            )
        else:
            # Negative exposure contributes to short exposure (stored as negative)
            exposures["short_option_exposure"] += market_exposure
            logger.debug(
                f"Added to SHORT option exposure: {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {market_exposure})"
            )

    # Calculate net market exposure by simply adding all exposures
    # Since short exposures are stored with negative signs, we can just add them
    exposures["net_market_exposure"] = (
        exposures["long_stock_exposure"]
        + exposures["short_stock_exposure"]  # Already negative
        + exposures["long_option_exposure"]
        + exposures["short_option_exposure"]  # Already negative
    )

    logger.debug(f"Portfolio exposures calculated: {exposures}")
    return exposures


# Helper functions


def _is_pending_activity(symbol: str) -> bool:
    """
    Check if a symbol represents pending activity.

    Args:
        symbol: The symbol to check

    Returns:
        True if the symbol represents pending activity, False otherwise
    """
    if not symbol:
        return False

    # Convert to uppercase for case-insensitive matching
    symbol_upper = symbol.upper()

    # Check for common pending activity patterns
    pending_patterns = [
        "PENDING ACTIVITY",
    ]

    return any(pattern in symbol_upper for pattern in pending_patterns)


def get_pending_activity(holding: PortfolioHolding) -> float:
    """
    Extract pending activity value from a portfolio holding.

    CSV Column Priority:
    1. Current Value column (parsed during CSV loading)
    2. Last Price Change column
    3. Today's Gain/Loss Dollar column
    4. Last Price column

    Args:
        holding: Portfolio holding representing pending activity

    Returns:
        float: Pending activity value (positive=incoming, negative=outgoing)

    Raises:
        ValueError: If holding has no raw data
        AssertionError: If holding is not pending activity
    """
    logger.warning(f"Extracting pending activity value from holding: {holding}")

    pending_activity_value = 0.0

    assert _is_pending_activity(holding.symbol), "How did we get here!?"

    if not holding.raw_data:
        raise ValueError(f"Pending activity holding has no raw data: {holding}")

    # If value is 0, try to extract from raw_data if available
    if holding.raw_data:
        for key, value in holding.raw_data.items():
            if pd.notna(value) and isinstance(value, str) and "$" in value:
                logger.debug(f"Found pending activity value in {key} column: {value}")
                pending_activity_value = clean_currency_value(value)

    logger.debug(f"Found pending activity value: {pending_activity_value}")
    return pending_activity_value


# These functions have been removed as part of the migration to the new data model:
# - _is_valid_option_symbol
# - _is_option_description
# - _extract_option_data


def get_positions_by_type(
    positions: list[Position], position_type: str
) -> list[Position]:
    """
    Get positions of a specific type.

    Args:
        positions: List of positions
        position_type: Type of position to filter for (e.g., 'stock', 'option', 'cash')

    Returns:
        List of positions of the specified type
    """
    return [p for p in positions if p.position_type == position_type]


def filter_positions_by_criteria(
    positions: list[Position], criteria: dict[str, str]
) -> list[Position]:
    """
    Filter positions based on criteria.

    Args:
        positions: List of positions to filter
        criteria: Dictionary of filter criteria
            - type: Position type (stock, option, cash, unknown)
            - symbol: Ticker symbol (exact match)
            - min_value: Minimum position value
            - max_value: Maximum position value

    Returns:
        Filtered list of positions
    """
    filtered_positions = positions

    # Apply filters
    for key, value in criteria.items():
        if key == "type":
            filtered_positions = [
                p for p in filtered_positions if p.position_type == value.lower()
            ]
        elif key == "symbol":
            filtered_positions = [
                p for p in filtered_positions if p.ticker.upper() == value.upper()
            ]
        elif key == "min_value":
            try:
                min_value = float(value)
                # Don't use abs() - respect the sign of market_value
                # This means min_value will filter based on the actual value, not the magnitude
                filtered_positions = [
                    p for p in filtered_positions if p.market_value >= min_value
                ]
            except ValueError:
                logger.warning(f"Invalid min_value: {value}. Skipping filter.")
        elif key == "max_value":
            try:
                max_value = float(value)
                # Don't use abs() - respect the sign of market_value
                # This means max_value will filter based on the actual value, not the magnitude
                filtered_positions = [
                    p for p in filtered_positions if p.market_value <= max_value
                ]
            except ValueError:
                logger.warning(f"Invalid max_value: {value}. Skipping filter.")

    return filtered_positions


def sort_positions(
    positions: list[Position], sort_by: str = "value", sort_direction: str = "desc"
) -> list[Position]:
    """
    Sort positions by the specified criteria.

    Args:
        positions: List of positions to sort
        sort_by: Attribute to sort by (value, symbol, type)
        sort_direction: Sort direction (asc or desc)

    Returns:
        Sorted list of positions
    """
    # Define sorting key functions
    sort_keys = {
        "value": lambda p: p.market_value,  # Don't use abs() - respect the sign
        "symbol": lambda p: p.ticker.upper(),
        "type": lambda p: p.position_type,
    }

    # Get the sorting key function
    sort_key = sort_keys.get(sort_by.lower(), sort_keys["value"])

    # Sort the positions
    sorted_positions = sorted(positions, key=sort_key)

    # Reverse if descending
    if sort_direction.lower() == "desc":
        sorted_positions.reverse()

    return sorted_positions


def group_positions_by_ticker(positions: list[Position]) -> dict[str, list[Position]]:
    """
    Group positions by ticker symbol.

    This function organizes a list of positions into a dictionary where the keys are
    ticker symbols and the values are lists of positions with that ticker.

    Args:
        positions: List of positions to group

    Returns:
        Dictionary mapping ticker symbols to lists of positions
    """
    grouped = {}
    for position in positions:
        if position.ticker not in grouped:
            grouped[position.ticker] = []
        grouped[position.ticker].append(position)
    return grouped


# create_portfolio_groups_from_positions function has been removed as part of the migration to the new data model.
# Use group_positions_by_ticker() instead.
