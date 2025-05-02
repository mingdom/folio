"""
Portfolio processing service.

This module provides high-level functions for portfolio processing, including:
- Processing raw portfolio holdings into a structured portfolio
- Creating portfolio groups that combine related positions
- Calculating portfolio summary metrics
- Computing exposure metrics for risk analysis

Migration Plan Notes:
---------------------
This module is part of Phase 1 of the folib migration plan, focusing on Portfolio Loading E2E.
It replaces the portfolio processing functionality in src/folio/portfolio.py with a cleaner,
more maintainable design that separates data processing from data loading.

Key differences from the old implementation:
- Uses immutable data structures for thread safety and predictability
- Separates portfolio processing from CSV loading
- Provides clear interfaces between components
- Uses composition over inheritance
- Follows functional programming principles where possible

Old Codebase References:
------------------------
- src/folio/portfolio.py: Contains the original process_portfolio_data function
- src/folio/portfolio_value.py: Contains functions for calculating portfolio values and metrics
- src/folio/data_model.py: Contains the original Position, PortfolioGroup, and PortfolioSummary classes

Potential Issues:
----------------
- The old codebase mixed data loading with business logic
- The old implementation used mutable classes, while the new design uses immutable dataclasses
- Some field types have changed (e.g., expiry is now a date object instead of a string)
- The old implementation had many computed properties that are now moved to utility functions
"""

import logging
import re
from datetime import date
from typing import Literal

import pandas as pd

from ..data.loader import clean_currency_value
from ..data.stock import stockdata
from ..domain import (
    OptionPosition,
    Portfolio,
    PortfolioGroup,
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

    This function transforms raw portfolio holdings into a structured portfolio by:
    1. Identifying cash-like positions
    2. Identifying unknown/invalid positions
    3. Grouping related positions (stocks with their options)
    4. Creating a portfolio object with groups, cash positions, and unknown positions

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()
        market_oracle: Market data oracle for fetching prices and other market data
        update_prices: Whether to update prices from market data (default: True)

    Returns:
        Processed portfolio with structured groups, cash positions, and unknown positions
    """
    logger.debug("Processing portfolio with %d holdings", len(holdings))

    # Extract pending activity value using the enhanced public function
    pending_activity_value = get_pending_activity(holdings)

    # Filter out pending activity from holdings
    filtered_holdings = [h for h in holdings if not _is_pending_activity(h.symbol)]

    # Separate cash-like positions and unknown positions
    non_cash_holdings = []
    cash_positions = []
    unknown_positions = []

    for holding in filtered_holdings:
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
        # Check for option positions
        elif _is_valid_option_symbol(holding.symbol, holding.description):
            # Options will be processed in create_portfolio_groups
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

    # Create portfolio groups from non-cash, non-unknown holdings
    groups = create_portfolio_groups(non_cash_holdings)
    logger.debug(f"Created {len(groups)} portfolio groups")

    # Create positions list from groups
    positions = []
    for group in groups:
        if group.stock_position:
            positions.append(group.stock_position)
        positions.extend(group.option_positions)

    # Add cash and unknown positions
    positions.extend(cash_positions)
    positions.extend(unknown_positions)

    # Create and return the portfolio
    portfolio = Portfolio(
        positions=positions,
        pending_activity_value=pending_activity_value,
    )

    logger.debug(
        f"Portfolio processing complete: {len(groups)} groups, {len(cash_positions)} cash positions, {len(unknown_positions)} unknown positions"
    )
    return portfolio


def create_portfolio_groups(holdings: list[PortfolioHolding]) -> list[PortfolioGroup]:
    """
    TODO: this logic is overly complicated. Maybe PortfolioGroup is a concept. Or we should be able to do everything in 1 pass.
    Create portfolio groups from holdings.

    This function groups related positions (stocks and their options) into PortfolioGroup objects.
    It identifies options based on their description patterns and matches them to their underlying stocks.

    Args:
        holdings: List of portfolio holdings (excluding cash-like positions)
        market_oracle: Market data oracle for fetching prices and other market data

    Returns:
        List of portfolio groups, each containing a stock position and its related option positions
    """
    logger.debug("Creating portfolio groups from %d holdings", len(holdings))

    # Separate stock and option holdings
    stock_holdings = {}
    option_holdings = []

    for holding in holdings:
        # Check if this is an option using our option symbol validation
        if _is_valid_option_symbol(holding.symbol, holding.description):
            option_holdings.append(holding)
            logger.debug(f"Identified option: {holding.symbol}")
        else:
            # This is a stock
            stock_holdings[holding.symbol] = holding
            logger.debug(f"Identified stock: {holding.symbol}")

    # First, extract option data for all options
    option_data_map = {}
    for i, option_holding in enumerate(option_holdings):
        option_data = _extract_option_data(option_holding)
        if option_data:
            ticker, strike, expiry, option_type, quantity = option_data
            option_data_map[i] = {
                "ticker": ticker,
                "strike": strike,
                "expiry": expiry,
                "option_type": option_type,
                "quantity": quantity,
                "holding": option_holding,
            }
        else:
            logger.warning(f"Could not parse option data for: {option_holding.symbol}")

    # Create a map of ticker -> options
    ticker_to_options = {}
    for i, data in option_data_map.items():
        ticker = data["ticker"]
        if ticker not in ticker_to_options:
            ticker_to_options[ticker] = []
        ticker_to_options[ticker].append((i, data))

    # Create groups
    groups = []
    processed_option_indices = set()

    # First, process stocks and their related options
    for symbol, stock_holding in stock_holdings.items():
        # Create stock position
        stock_position = StockPosition(
            ticker=stock_holding.symbol,
            quantity=stock_holding.quantity,
            price=stock_holding.price,
            cost_basis=stock_holding.cost_basis_total,
        )

        # Find related options
        option_positions = []

        # Check if we have options for this stock
        if symbol in ticker_to_options:
            for i, data in ticker_to_options[symbol]:
                if i in processed_option_indices:
                    continue

                # Create option position
                option_position = OptionPosition(
                    ticker=data["ticker"],
                    quantity=data["quantity"],
                    strike=data["strike"],
                    expiry=data["expiry"],
                    option_type=data["option_type"],
                    price=data["holding"].price,
                    cost_basis=data["holding"].cost_basis_total,
                )

                option_positions.append(option_position)
                processed_option_indices.add(i)
                logger.debug(
                    f"Added option for {symbol}: {data['option_type']} {data['strike']} {data['expiry']}"
                )

        # Create portfolio group
        group = PortfolioGroup(
            ticker=symbol,
            stock_position=stock_position,
            option_positions=option_positions,
        )
        groups.append(group)

    # Process orphaned options (options without a matching stock position)
    for ticker, options in ticker_to_options.items():
        # Skip if we already have a stock for this ticker
        if ticker in stock_holdings:
            continue

        option_positions = []
        for i, data in options:
            if i in processed_option_indices:
                continue

            # Create option position
            option_position = OptionPosition(
                ticker=data["ticker"],
                quantity=data["quantity"],
                strike=data["strike"],
                expiry=data["expiry"],
                option_type=data["option_type"],
                price=data["holding"].price,
                cost_basis=data["holding"].cost_basis_total,
            )

            option_positions.append(option_position)
            processed_option_indices.add(i)

        if option_positions:
            # In the old implementation, a placeholder stock position with quantity 0 is created
            # for options without a matching stock position. This is important for matching
            # the old implementation's behavior.
            stock_position = StockPosition(
                ticker=ticker,
                quantity=0,
                price=0.0,
                cost_basis=0.0,
            )

            # Create portfolio group with the placeholder stock position and the options
            group = PortfolioGroup(
                ticker=ticker,
                stock_position=stock_position,
                option_positions=option_positions,
            )
            groups.append(group)
            logger.debug(
                f"Created orphaned option group for {ticker} with placeholder stock position and {len(option_positions)} options"
            )

    logger.debug(f"Created {len(groups)} portfolio groups")
    return groups


def create_portfolio_summary(portfolio: Portfolio) -> PortfolioSummary:
    """
    Create a summary of portfolio metrics.

    This function calculates summary metrics for the portfolio, including:
    - Total value
    - Stock value
    - Option value
    - Cash value
    - Unknown position value
    - Pending activity value
    - Net market exposure
    - Portfolio beta

    Args:
        portfolio: The portfolio to summarize

    Returns:
        Portfolio summary with calculated metrics
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
                long_options["delta_exposure"] += abs(
                    market_exposure
                )  # Use absolute value for delta exposure
                logger.debug(
                    f"Categorized as LONG option exposure: {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {abs(market_exposure)})"
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
                # In the old implementation, short_options["delta_exposure"] is stored as a negative value
                # But we need to make sure it's negative regardless of the market_exposure sign
                short_options["delta_exposure"] += -abs(
                    market_exposure
                )  # Store as negative value
                logger.debug(
                    f"Categorized as SHORT option exposure: {position.ticker} {position.option_type} {position.strike} (delta: {delta}, exposure: {-abs(market_exposure)})"
                )

        elif position.position_type == "cash":
            cash_value += position_value

        else:  # unknown
            unknown_value += position_value
            logger.debug(f"Unknown position type for {position.ticker}")

    # Import portfolio calculation functions
    from ..calculations.portfolio import (
        calculate_portfolio_metrics,
        create_value_breakdowns,
    )

    # Create exposure breakdowns using portfolio_value module
    long_value, short_value, options_value = create_value_breakdowns(
        long_stocks=long_stocks,
        short_stocks=short_stocks,
        long_options=long_options,
        short_options=short_options,
    )

    # Calculate portfolio metrics
    net_market_exposure, portfolio_beta, short_percentage = calculate_portfolio_metrics(
        long_value=long_value, short_value=short_value
    )

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
    old_style_net_exposure = exposures["net_market_exposure"]

    summary = PortfolioSummary(
        total_value=total_value,
        stock_value=long_stocks["value"]
        + short_stocks["value"],  # Sum of all stock values, preserving sign
        option_value=long_options["value"]
        + short_options["value"],  # Note: short_options["value"] is negative
        cash_value=cash_value,
        unknown_value=unknown_value,
        pending_activity_value=pending_activity,  # Use the fixed pending_activity value
        net_market_exposure=old_style_net_exposure,  # Use the exposure-based calculation
        portfolio_beta=portfolio_beta,
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

    # Initialize exposure metrics
    exposures = {
        "long_stock_exposure": 0.0,
        "short_stock_exposure": 0.0,
        "long_option_exposure": 0.0,
        "short_option_exposure": 0.0,
        "net_market_exposure": 0.0,
        "beta_adjusted_exposure": 0.0,
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


def get_pending_activity(holdings: list[PortfolioHolding]) -> float:
    """
    Extract pending activity value from portfolio holdings.

    This function identifies and calculates the total value of pending activity
    in the portfolio by examining holdings with "Pending Activity" in their symbol.

    It checks multiple columns in the raw data to handle different CSV formats:
    1. First tries the value already parsed during CSV loading (Current Value column)
    2. If that's zero, checks Last Price Change column
    3. If that's not available, checks Today's Gain/Loss Dollar column
    4. If that's not available, checks Last Price column

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()

    Returns:
        Total value of pending activity (positive for incoming funds, negative for outgoing)
    """
    logger.debug("Extracting pending activity value")

    pending_activity_value = 0.0

    # Find holdings that represent pending activity
    pending_holdings = [h for h in holdings if _is_pending_activity(h.symbol)]

    if not pending_holdings:
        raise ValueError("No pending activity found in portfolio holdings")

    if len(pending_holdings) > 1:
        raise ValueError(
            f"Multiple pending activity holdings found: {[h.symbol for h in pending_holdings]}"
        )

    logger.warning(f"Found {pending_holdings} pending activity holdings")
    holding = pending_holdings[0]

    if not holding.raw_data:
        raise ValueError(f"Pending activity holding has no raw data: {holding}")

    # If value is 0, try to extract from raw_data if available
    if holding.raw_data:
        for key, value in holding.raw_data.items():
            if pd.notna(value) and isinstance(value, str) and "$" in value:
                logger.debug(f"Found pending activity value in {key} column: {value}")
                pending_activity_value = clean_currency_value(value)

    logger.warning(f"Found pending activity value: {pending_activity_value}")
    return pending_activity_value


def _is_valid_option_symbol(symbol: str, description: str = "") -> bool:
    """
    Check if a symbol is a valid option symbol in Fidelity's format.

    Fidelity option symbols typically:
    - Start with a hyphen
    - Are followed by the underlying ticker
    - Have a date code (YYMMDD)
    - Have option type (C/P)
    - End with the strike price

    Args:
        symbol: The symbol to check
        description: Optional description to check for option-related terms

    Returns:
        True if the symbol appears to be a valid option symbol
    """
    if not symbol:
        return False

    # Check if symbol starts with a hyphen (Fidelity format for options)
    if symbol.strip().startswith("-"):
        # Fidelity option symbols start with a hyphen
        return True

    # Also check description for option-related terms
    if description:
        return _is_option_description(description)

    return False


def _is_option_description(description: str) -> bool:
    """
    Determine if a description is for an option.

    Args:
        description: The description to check

    Returns:
        True if the description is for an option, False otherwise
    """
    option_patterns = [
        r"\b(CALL|PUT)\b",
        r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2}\s+\d{4}\b",
        r"\$\d+(\.\d+)?\s+(CALL|PUT)\b",
    ]

    for pattern in option_patterns:
        if re.search(pattern, description, re.IGNORECASE):
            return True

    return False


def _extract_option_data(
    option_holding: PortfolioHolding,
) -> tuple[str, float, date, Literal["CALL", "PUT"], float] | None:
    """
    Extract option data from a holding.

    Args:
        option_holding: The option holding
        underlying_ticker: The underlying ticker (if known)

    Returns:
        Tuple of (ticker, strike, expiry, option_type, quantity) or None if parsing fails
    """
    description = option_holding.description
    symbol = option_holding.symbol.strip()
    quantity = option_holding.quantity

    # Try to extract data from the description (e.g., "AMZN MAY 16 2025 $190 CALL")
    match = re.search(
        r"([A-Z]+)\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})\s+(\d{4})\s+\$(\d+(?:\.\d+)?)\s+(CALL|PUT)",
        description,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(f"Could not parse option data for: {symbol} - {description}")

    ticker = match.group(1)
    month_str = match.group(2).upper()
    day = int(match.group(3))
    year = int(match.group(4))
    strike = float(match.group(5))
    option_type = match.group(6).upper()

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
    return ticker, strike, expiry, option_type, quantity


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
                filtered_positions = [
                    p for p in filtered_positions if abs(p.market_value) >= min_value
                ]
            except ValueError:
                logger.warning(f"Invalid min_value: {value}. Skipping filter.")
        elif key == "max_value":
            try:
                max_value = float(value)
                filtered_positions = [
                    p for p in filtered_positions if abs(p.market_value) <= max_value
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
        "value": lambda p: abs(p.market_value),
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


def create_portfolio_groups_from_positions(
    positions: list[Position],
) -> list[PortfolioGroup]:
    """
    Create portfolio groups from a list of positions.

    This function groups related positions (stocks and their options) into PortfolioGroup objects.
    It's similar to create_portfolio_groups but works with Position objects instead of PortfolioHolding objects.

    Args:
        positions: List of positions (StockPosition, OptionPosition, etc.)

    Returns:
        List of portfolio groups, each containing a stock position and its related option positions
    """
    logger.debug("Creating portfolio groups from %d positions", len(positions))

    # Separate positions by type
    stock_positions = get_positions_by_type(positions, "stock")
    option_positions = get_positions_by_type(positions, "option")

    # Create a map of ticker -> stock position
    ticker_to_stock = {p.ticker: p for p in stock_positions}

    # Create a map of ticker -> option positions
    ticker_to_options = {}
    for option in option_positions:
        ticker = option.ticker
        if ticker not in ticker_to_options:
            ticker_to_options[ticker] = []
        ticker_to_options[ticker].append(option)

    # Create groups
    groups = []

    # First, process stocks and their related options
    for ticker, stock_position in ticker_to_stock.items():
        # Find related options
        option_positions = ticker_to_options.get(ticker, [])

        # Create portfolio group
        group = PortfolioGroup(
            ticker=ticker,
            stock_position=stock_position,
            option_positions=option_positions,
        )
        groups.append(group)
        logger.debug(
            f"Created portfolio group for {ticker} with {len(option_positions)} options"
        )

    # Process orphaned options (options without a matching stock position)
    for ticker, options in ticker_to_options.items():
        # Skip if we already have a stock for this ticker
        if ticker in ticker_to_stock:
            continue

        # Create a placeholder stock position with quantity 0
        from ..domain import StockPosition

        stock_position = StockPosition(
            ticker=ticker,
            quantity=0,
            price=0.0,
            cost_basis=0.0,
        )

        # Create portfolio group with the placeholder stock position and the options
        group = PortfolioGroup(
            ticker=ticker,
            stock_position=stock_position,
            option_positions=options,
        )
        groups.append(group)
        logger.debug(
            f"Created orphaned option group for {ticker} with placeholder stock position and {len(options)} options"
        )

    logger.debug(f"Created {len(groups)} portfolio groups from positions")
    return groups
