"""
Portfolio processing service.

This module provides high-level functions for portfolio processing, including:
- Processing raw portfolio holdings into a structured portfolio
- Grouping and filtering positions by various criteria
- Calculating portfolio summary metrics
- Computing exposure metrics for risk analysis

Key functions:
- process_portfolio: Convert raw portfolio data into a structured portfolio
- create_portfolio_summary: Generate summary metrics for a portfolio
- group_positions_by_ticker: Group positions by underlying ticker
- get_portfolio_exposures: Calculate exposures for a portfolio
"""

import logging
import re
from datetime import date
from typing import Literal, cast

import pandas as pd

from ..calculations import (
    calculate_beta_adjusted_exposure,
    calculate_option_delta,
    calculate_option_exposure,
    calculate_portfolio_metrics,
    calculate_stock_exposure,
    create_value_breakdowns,
)
from ..data.stock import stockdata
from ..domain import (
    CashPosition,
    OptionPosition,
    Portfolio,
    PortfolioGroup,
    PortfolioHolding,
    PortfolioSummary,
    Position,
    StockPosition,
    UnknownPosition,
)

# Set up logging
logger = logging.getLogger(__name__)


# Helper functions for working with positions


def group_positions_by_ticker(positions: list[Position]) -> dict[str, list[Position]]:
    """
    Group positions by ticker symbol.

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


def get_positions_by_ticker(positions: list[Position], ticker: str) -> list[Position]:
    """
    Get all positions for a specific ticker.

    Args:
        positions: List of positions to search
        ticker: Ticker symbol to match

    Returns:
        List of positions with the specified ticker
    """
    return [p for p in positions if p.ticker == ticker]


def get_stock_position_by_ticker(
    positions: list[Position], ticker: str
) -> StockPosition | None:
    """
    Get the stock position for a specific ticker.

    Args:
        positions: List of positions to search
        ticker: Ticker symbol to match

    Returns:
        StockPosition if found, None otherwise
    """
    for p in positions:
        if p.position_type == "stock" and p.ticker == ticker:
            return cast(StockPosition, p)
    return None


def get_option_positions_by_ticker(
    positions: list[Position], ticker: str
) -> list[OptionPosition]:
    """
    Get all option positions for a specific ticker.

    Args:
        positions: List of positions to search
        ticker: Ticker symbol to match

    Returns:
        List of option positions with the specified ticker
    """
    return [
        cast(OptionPosition, p)
        for p in positions
        if p.position_type == "option" and p.ticker == ticker
    ]


def get_positions_by_type(
    positions: list[Position],
    position_type: Literal["stock", "option", "cash", "unknown"],
) -> list[Position]:
    """
    Get all positions of a specific type.

    Args:
        positions: List of positions to search
        position_type: Type of positions to return

    Returns:
        List of positions with the specified type
    """
    return [p for p in positions if p.position_type == position_type]


# For backward compatibility during migration
def create_portfolio_groups_from_positions(
    positions: list[Position],
) -> list[PortfolioGroup]:
    """
    Create portfolio groups from a list of positions.

    This function is provided for backward compatibility during migration.
    New code should use the helper functions above instead.

    Args:
        positions: List of positions to group

    Returns:
        List of portfolio groups
    """
    # Group positions by ticker
    grouped = group_positions_by_ticker(positions)
    groups = []

    for ticker, ticker_positions in grouped.items():
        # Find stock position
        stock_position = None
        for p in ticker_positions:
            if p.position_type == "stock":
                stock_position = cast(StockPosition, p)
                break

        # Find option positions
        option_positions = [
            cast(OptionPosition, p)
            for p in ticker_positions
            if p.position_type == "option"
        ]

        # Create group
        group = PortfolioGroup(
            ticker=ticker,
            stock_position=stock_position,
            option_positions=option_positions,
        )
        groups.append(group)

    return groups


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
    2. Identifying stock and option positions
    3. Identifying unknown/invalid positions
    4. Creating a portfolio object with all positions

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()
        update_prices: Whether to update prices from market data (default: True)

    Returns:
        Processed portfolio with all positions
    """
    logger.debug("Processing portfolio with %d holdings", len(holdings))

    # Extract pending activity value
    pending_activity_value = _get_pending_activity(holdings)

    # Filter out pending activity from holdings
    filtered_holdings = [h for h in holdings if not _is_pending_activity(h.symbol)]

    # Process holdings into positions
    positions = []

    for holding in filtered_holdings:
        # Check for cash-like positions
        if stockdata.is_cash_like(holding.symbol, holding.description):
            # Convert to CashPosition
            cash_position = CashPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
                raw_data=holding.__dict__,
            )
            positions.append(cash_position)
            logger.debug(f"Identified cash-like position: {holding.symbol}")

        # Check for option positions
        elif _is_valid_option_symbol(holding.symbol, holding.description):
            # Extract option data
            try:
                option_data = _extract_option_data(holding)
                if option_data:
                    ticker, strike, expiry, option_type, quantity = option_data
                    option_position = OptionPosition(
                        ticker=ticker,
                        quantity=quantity,
                        price=holding.price,
                        strike=strike,
                        expiry=expiry,
                        option_type=option_type,
                        cost_basis=holding.cost_basis_total,
                        raw_data=holding.__dict__,
                    )
                    positions.append(option_position)
                    logger.debug(f"Identified option position: {holding.symbol}")
            except Exception as e:
                # If we can't parse the option data, treat it as an unknown position
                logger.warning(f"Could not parse option data for {holding.symbol}: {e}")
                unknown_position = UnknownPosition(
                    ticker=holding.symbol,
                    quantity=holding.quantity,
                    price=holding.price,
                    description=holding.description,
                    cost_basis=holding.cost_basis_total,
                    raw_data=holding.__dict__,
                )
                positions.append(unknown_position)

        # Check for stock positions
        elif stockdata.is_valid_stock_symbol(holding.symbol):
            stock_position = StockPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
                raw_data=holding.__dict__,
            )
            positions.append(stock_position)
            logger.debug(f"Identified stock position: {holding.symbol}")

        # Unknown positions
        else:
            unknown_position = UnknownPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                description=holding.description,
                cost_basis=holding.cost_basis_total,
                raw_data=holding.__dict__,
            )
            positions.append(unknown_position)
            logger.debug(f"Identified unknown position: {holding.symbol}")

    # For backward compatibility during migration
    # We don't use the groups directly, but we create them for logging purposes
    _ = create_portfolio_groups_from_positions(positions)

    # Create and return the portfolio
    portfolio = Portfolio(
        positions=positions,
        pending_activity_value=pending_activity_value,
    )

    # Log portfolio statistics
    stock_positions = [p for p in positions if p.position_type == "stock"]
    option_positions = [p for p in positions if p.position_type == "option"]
    cash_positions = [p for p in positions if p.position_type == "cash"]
    unknown_positions = [p for p in positions if p.position_type == "unknown"]

    logger.debug(
        f"Portfolio processing complete: {len(positions)} positions "
        f"({len(stock_positions)} stocks, {len(option_positions)} options, "
        f"{len(cash_positions)} cash, {len(unknown_positions)} unknown)"
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
            # Create portfolio group with just the options
            group = PortfolioGroup(
                ticker=ticker,
                stock_position=None,
                option_positions=option_positions,
            )
            groups.append(group)
            logger.debug(
                f"Created orphaned option group for {ticker} with {len(option_positions)} options"
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
    - Unknown value
    - Pending activity value
    - Net market exposure
    - Portfolio beta

    Args:
        portfolio: The portfolio to summarize

    Returns:
        Portfolio summary with calculated metrics
    """
    logger.debug("Creating portfolio summary")

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
        # Skip NaN values
        position_value = position.market_value
        if pd.isna(position_value):
            logger.warning(f"Skipping position {position.ticker} with NaN market value")
            continue

        # Process based on position type
        if position.position_type == "stock":
            stock = cast(StockPosition, position)
            # Get beta for exposure calculation
            beta = 1.0
            try:
                beta = stockdata.get_beta(stock.ticker)
            except Exception as e:
                logger.warning(f"Could not get beta for {stock.ticker}: {e}")

            # Calculate exposures using the calculation module
            market_exposure = calculate_stock_exposure(stock.quantity, stock.price)
            beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)

            if stock.quantity > 0:
                long_stocks["value"] += market_exposure
                long_stocks["beta_adjusted"] += beta_adjusted
            else:
                short_stocks["value"] += market_exposure  # Already negative
                short_stocks["beta_adjusted"] += beta_adjusted  # Already negative

        elif position.position_type == "option":
            option = cast(OptionPosition, position)
            # Get underlying price and beta
            beta = 1.0
            try:
                underlying_price = stockdata.get_price(option.ticker)
                beta = stockdata.get_beta(option.ticker)
            except Exception as e:
                logger.warning(f"Could not get market data for {option.ticker}: {e}")
                # Fallback to using a reasonable proxy for underlying price
                underlying_price = option.strike  # Using strike as fallback

            # Calculate option exposures using the calculation module
            delta = calculate_option_delta(
                option_type=option.option_type,
                strike=option.strike,
                expiry=option.expiry,
                underlying_price=underlying_price,
            )
            market_exposure = calculate_option_exposure(
                quantity=option.quantity, underlying_price=underlying_price, delta=delta
            )
            beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)

            if market_exposure > 0:
                long_options["value"] += position_value
                long_options["beta_adjusted"] += beta_adjusted
                long_options["delta_exposure"] += market_exposure
            else:
                short_options["value"] += position_value
                short_options["beta_adjusted"] += beta_adjusted
                short_options["delta_exposure"] += market_exposure

        elif position.position_type == "cash":
            cash_value += position_value

        else:  # unknown
            unknown_value += position_value
            logger.debug(f"Unknown position type for {position.ticker}")

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

    # Calculate total value
    total_value = (
        abs(long_stocks["value"])
        + abs(short_stocks["value"])
        + abs(long_options["value"])
        + abs(short_options["value"])
        + cash_value
        + unknown_value
        + portfolio.pending_activity_value
    )

    # Cash percentage calculation removed (not in PortfolioSummary yet)

    # Create and return the portfolio summary
    summary = PortfolioSummary(
        total_value=total_value,
        stock_value=abs(long_stocks["value"]) + abs(short_stocks["value"]),
        option_value=abs(long_options["value"]) + abs(short_options["value"]),
        cash_value=cash_value,
        unknown_value=unknown_value,
        pending_activity_value=portfolio.pending_activity_value,
        net_market_exposure=net_market_exposure,
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
            exposures["short_stock_exposure"] += abs(market_exposure)

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

        # Calculate option exposures using the calculation modules
        delta = calculate_option_delta(
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=underlying_price,
        )
        market_exposure = calculate_option_exposure(
            quantity=position.quantity, underlying_price=underlying_price, delta=delta
        )
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        exposures["beta_adjusted_exposure"] += beta_adjusted

        if market_exposure > 0:
            exposures["long_option_exposure"] += market_exposure
        else:
            exposures["short_option_exposure"] += abs(market_exposure)

    # Calculate net market exposure
    exposures["net_market_exposure"] = (
        exposures["long_stock_exposure"]
        - exposures["short_stock_exposure"]
        + exposures["long_option_exposure"]
        - exposures["short_option_exposure"]
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
        "PENDING",
        "UNSETTLED",
    ]

    return any(pattern in symbol_upper for pattern in pending_patterns)


def _get_pending_activity(holdings: list[PortfolioHolding]) -> float:
    """
    Extract pending activity value from portfolio holdings.

    This function identifies and calculates the total value of pending activity
    in the portfolio (e.g., unsettled trades, dividends, etc.).

    The function checks for pending activity by:
    1. Looking for holdings with "PENDING ACTIVITY" or similar in the symbol
    2. Checking the value in the holding

    In the old implementation, multiple columns were checked for the pending activity value
    because the column containing the value could vary between CSV files. In the new
    implementation, this is handled during CSV parsing, and the value is already
    stored in the holding.value field.

    Args:
        holdings: List of portfolio holdings

    Returns:
        Total value of pending activity
    """
    logger.debug("Extracting pending activity value")

    pending_activity_value = 0.0

    # Find holdings that represent pending activity
    pending_holdings = [h for h in holdings if _is_pending_activity(h.symbol)]

    if not pending_holdings:
        logger.debug("No pending activity found")
        return 0.0

    # Sum up the values of all pending activity holdings
    for holding in pending_holdings:
        if holding.value != 0:
            pending_activity_value += holding.value
            logger.debug(
                f"Found pending activity: {holding.symbol} with value {holding.value}"
            )

    # If we found pending activity holdings but all had zero value, log a warning
    if pending_holdings and pending_activity_value == 0:
        logger.warning(
            f"Found {len(pending_holdings)} pending activity holdings, but all had zero value"
        )

    logger.debug(f"Total pending activity value: {pending_activity_value}")
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
