"""
Portfolio processing and analytics service for Folib.

This module provides the core logic for transforming raw portfolio holdings into structured, analyzable objects and for computing key portfolio metrics. It is responsible for:

- Parsing and categorizing raw portfolio holdings (from CSV or other sources) into typed position objects (stocks, options, cash, unknown)
- Handling special cases such as cash-like positions and pending activity
- Creating and updating position objects with current market data as needed
- Calculating portfolio-level summaries, including total value, breakdowns by asset type, and pending activity
- Computing market exposures, beta-adjusted exposures, and option Greeks (using market price, not volatility)
- Optimizing performance by caching expensive calculations (e.g., option delta) within a processing run
- Providing helper utilities for grouping, sorting, and filtering positions

Design principles:
- All calculations fail fast on missing or invalid prices (no fallback volatility)
- Data models are immutable and separated from business logic
- All service and CLI consumers interact with this layer for portfolio analytics
- Modular, testable, and efficient code structure

Key functions:
- process_portfolio: Transform raw holdings into a structured Portfolio object
- create_portfolio_summary: Generate summary metrics for a portfolio
- get_portfolio_exposures: Calculate detailed exposure metrics for a portfolio
- group_positions_by_ticker: Group positions by underlying ticker symbol
- Additional helpers for value calculation, sorting, and filtering positions
"""

import logging
import re
from datetime import date

import pandas as pd

from src.folio.cash_detection import is_cash_or_short_term

from ..calculations.exposure import (
    calculate_beta_adjusted_exposure,
    calculate_option_exposure,
    calculate_stock_exposure,
)
from ..calculations.options import calculate_option_delta, categorize_option_by_delta
from ..data.loader import clean_currency_value
from ..data.utils import is_valid_stock_symbol
from ..domain import (
    CashPosition,
    OptionPosition,
    Portfolio,
    PortfolioHolding,
    PortfolioSummary,
    Position,
    StockPosition,
    UnknownPosition,
)
from ..services.ticker_service import ticker_service

logger = logging.getLogger(__name__)


class Exposures:
    LONG_STOCK = "long_stock_exposure"
    SHORT_STOCK = "short_stock_exposure"
    LONG_OPTION = "long_option_exposure"
    SHORT_OPTION = "short_option_exposure"
    LONG_STOCK_BETA_ADJ = "long_stock_beta_adjusted"
    SHORT_STOCK_BETA_ADJ = "short_stock_beta_adjusted"
    LONG_OPTION_BETA_ADJ = "long_option_beta_adjusted"
    SHORT_OPTION_BETA_ADJ = "short_option_beta_adjusted"
    NET_MARKET = "net_market_exposure"
    BETA_ADJ = "beta_adjusted_exposure"
    TOTAL_VALUE = "total_value"


def _create_cash_position(holding: PortfolioHolding) -> CashPosition:
    return CashPosition(
        ticker=holding.symbol,
        quantity=holding.quantity,
        price=holding.price,
        cost_basis=holding.cost_basis_total,
    )


def _create_unknown_position(holding: PortfolioHolding) -> UnknownPosition:
    return UnknownPosition(
        ticker=holding.symbol,
        quantity=holding.quantity,
        price=holding.price,
        description=holding.description,
        cost_basis=holding.cost_basis_total,
    )


def _categorize_holdings(
    holdings: list[PortfolioHolding],
) -> tuple[list[PortfolioHolding], list[CashPosition], list[UnknownPosition], float]:
    """
    Categorize holdings into different types and extract pending activity.

    Args:
        holdings: List of portfolio holdings

    Returns:
        Tuple containing:
        - non_cash_holdings: List of stock and option holdings
        - cash_positions: List of cash positions
        - unknown_positions: List of unknown positions
        - pending_activity_value: Value of pending activity

    Raises:
        ValueError: If multiple pending activity entries are found
    """
    non_cash_holdings = []
    cash_positions = []
    unknown_positions = []
    pending_activity_value = 0.0
    pending_activity_found = False

    for holding in holdings:
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
        if is_cash_or_short_term(holding.symbol, description=holding.description):
            cash_positions.append(_create_cash_position(holding))
            logger.debug(f"Identified cash-like position: {holding.symbol}")
        elif _is_option_holding(holding) or is_valid_stock_symbol(holding.symbol):
            non_cash_holdings.append(holding)
            logger.debug(
                f"Identified {'option' if _is_option_holding(holding) else 'stock'} position: {holding.symbol}"
            )
        else:
            unknown_positions.append(_create_unknown_position(holding))
            logger.debug(f"Identified unknown position: {holding.symbol}")

    return non_cash_holdings, cash_positions, unknown_positions, pending_activity_value


def _is_option_holding(holding: PortfolioHolding) -> bool:
    """
    Check if a holding represents an option position.

    Args:
        holding: Portfolio holding to check

    Returns:
        True if the holding is an option, False otherwise
    """
    return (
        "CALL" in holding.description.upper()
        or "PUT" in holding.description.upper()
        or holding.symbol.strip().startswith(
            "-"
        )  # Fidelity option symbols start with hyphen
    )


def _create_stock_positions(
    non_cash_holdings: list[PortfolioHolding],
) -> list[StockPosition]:
    """
    Create stock positions from non-cash holdings.

    Args:
        non_cash_holdings: List of non-cash holdings

    Returns:
        List of stock positions
    """
    stock_positions = []

    for holding in non_cash_holdings:
        if not _is_option_holding(holding):
            stock_position = StockPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            stock_positions.append(stock_position)
            logger.debug(f"Created stock position for {holding.symbol}")

    return stock_positions


def _create_option_positions(
    non_cash_holdings: list[PortfolioHolding],
    stock_tickers: set[str] | None = None,
) -> list[OptionPosition]:
    """
    Create option positions from non-cash holdings.

    Args:
        non_cash_holdings: List of non-cash holdings
        stock_tickers: Set of stock tickers for identifying unpaired options

    Returns:
        List of option positions with updated underlying prices for unpaired options
    """
    option_positions = []
    unpaired_count = 0

    # Filter for option holdings first
    option_holdings = [h for h in non_cash_holdings if _is_option_holding(h)]

    for holding in option_holdings:
        # Try to parse the option position, continue to next holding if it fails
        try:
            option_position = _parse_option_position(holding)
        except Exception as e:
            logger.warning(
                f"Could not create option position for {holding.symbol}: {e}"
            )
            continue

        # Skip if parsing returned None
        if not option_position:
            continue

        # Check if this is an unpaired option and update its price if needed
        if stock_tickers and option_position.ticker not in stock_tickers:
            unpaired_count += 1
            _update_unpaired_option_price(option_position)

        option_positions.append(option_position)
        logger.debug(f"Created option position for {holding.symbol}")

    if unpaired_count > 0:
        logger.debug(f"Updated {unpaired_count} unpaired options during creation")

    return option_positions


def _update_unpaired_option_price(option_position: OptionPosition) -> None:
    """
    Update the underlying price for an unpaired option.

    Args:
        option_position: The option position to update
    """
    try:
        underlying_price = ticker_service.get_price(option_position.ticker)
        if underlying_price <= 0:
            return

        # Set the underlying_price attribute
        object.__setattr__(
            option_position,
            "underlying_price",
            underlying_price,
        )
        logger.debug(
            f"Updated underlying price for unpaired option {option_position.ticker} to {underlying_price}"
        )
    except Exception as e:
        logger.error(
            f"Error updating underlying price for {option_position.ticker}: {e!s}"
        )


def _parse_option_position(holding: PortfolioHolding) -> OptionPosition | None:
    """
    Parse option data from a holding description and create an OptionPosition.

    Args:
        holding: Portfolio holding with option data

    Returns:
        OptionPosition object or None if parsing fails
    """
    try:
        description = holding.description
        symbol = holding.symbol.strip()  # Strip leading/trailing whitespace

        logger.debug(
            f"Parsing option position with symbol: '{symbol}' and description: '{description}'"
        )

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
            expiry = date(year, month, day)

            option_position = OptionPosition(
                ticker=ticker,
                quantity=quantity,
                strike=strike,
                expiry=expiry,
                option_type=option_type,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            logger.debug(
                f"Successfully parsed option position for {ticker} {option_type} {strike}"
            )
            return option_position
        else:
            logger.warning(
                f"Could not parse option data from description: '{description}' (symbol: '{symbol}')"
            )
            return None
    except Exception as e:
        logger.warning(
            f"Error parsing option position for symbol '{holding.symbol}': {e}"
        )
        return None


def _synchronize_option_underlying_prices(positions: list[Position]) -> list[Position]:
    """
    Ensure options use the same underlying price as their paired stocks.

    For each option, if there's a matching stock position (same ticker),
    create a new option position with the underlying_price set to match the stock's price.

    Args:
        positions: List of all positions

    Returns:
        Updated list of positions with synchronized underlying prices
    """
    if not isinstance(positions, list):
        raise TypeError("positions must be a list")
    if not positions:
        return []

    stock_prices = {
        p.ticker: p.price
        for p in positions
        if getattr(p, "position_type", None) == "stock"
    }

    # Value-based cache key: (ticker, strike, expiry, option_type)
    def _option_cache_key(pos):
        return (
            getattr(pos, "ticker", None),
            getattr(pos, "strike", None),
            getattr(pos, "expiry", None),
            getattr(pos, "option_type", None),
        )

    updated_positions = []
    for pos in positions:
        if getattr(pos, "position_type", None) != "option":
            updated_positions.append(pos)
            continue
        if pos.ticker not in stock_prices:
            updated_positions.append(pos)
            continue
        # Mutate in place to preserve object identity for cache linkage
        object.__setattr__(pos, "underlying_price", stock_prices[pos.ticker])
        updated_positions.append(pos)
    return updated_positions


def _update_all_prices(positions: list[Position]) -> list[Position]:
    """
    Update prices for all positions from market data.

    Args:
        positions: List of all positions

    Returns:
        List of updated positions with new prices

    Note:
        This function will update prices for all positions, including:
        - Stocks: Updates current price
        - Options: Updates underlying price
        - Other position types: Prices remain unchanged
    """
    updated_positions = []
    for position in positions:
        try:
            if isinstance(position, StockPosition):
                # Use the ticker service to get the current price
                current_price = ticker_service.get_price(position.ticker)
                if current_price > 0:
                    updated_position = StockPosition(
                        ticker=position.ticker,
                        quantity=position.quantity,
                        price=current_price,
                        cost_basis=position.cost_basis,
                        raw_data=position.raw_data,
                    )
                    updated_positions.append(updated_position)
                    logger.debug(
                        f"Updated price for {position.ticker} to {current_price}"
                    )
                else:
                    logger.warning(f"No valid price found for {position.ticker}")
                    updated_positions.append(position)
            elif isinstance(position, OptionPosition):
                # Use the ticker service to get the current price
                underlying_price = ticker_service.get_price(position.ticker)
                if underlying_price > 0:
                    # Create a new option position with the correct parameters
                    updated_position = OptionPosition(
                        ticker=position.ticker,
                        quantity=position.quantity,
                        price=position.price,  # Keep original price for options
                        cost_basis=position.cost_basis,
                        strike=position.strike,
                        expiry=position.expiry,
                        option_type=position.option_type,
                        raw_data=getattr(position, "raw_data", None),
                    )
                    # Set the underlying_price attribute
                    object.__setattr__(
                        updated_position, "underlying_price", underlying_price
                    )
                    updated_positions.append(updated_position)
                    logger.debug(
                        f"Updated underlying price for {position.ticker} to {underlying_price}"
                    )
                else:
                    logger.warning(
                        f"No valid underlying price found for {position.ticker}"
                    )
                    updated_positions.append(position)
            else:
                # For other position types (cash, unknown), keep original price
                updated_positions.append(position)
        except Exception as e:
            logger.error(f"Error updating price for {position.ticker}: {e!s}")
            updated_positions.append(position)

    return updated_positions


def process_portfolio(
    holdings_data: tuple[list[PortfolioHolding], set[str]],
    # Controls whether to update prices from market data
    # Default is False to minimize API calls
    # When False, uses raw CSV prices first and only updates prices for unpaired options
    update_prices: bool = False,
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
        holdings_data: Tuple containing:
                      - List of portfolio holdings from parse_portfolio_holdings()
                      - Set of stock tickers for option pairing
        update_prices: Whether to update prices from market data (default: False)
                      When False, only updates prices for unpaired options
                      to ensure accurate exposure calculations.

    Returns:
        Portfolio: Structured portfolio with categorized positions and groups

    Raises:
        ValueError: If multiple pending activity entries are found
    """
    # Unpack the holdings data
    holdings, stock_tickers = holdings_data

    logger.debug("Processing portfolio with %d holdings", len(holdings))

    # Categorize holdings into different types and extract pending activity
    non_cash_holdings, cash_positions, unknown_positions, pending_activity_value = (
        _categorize_holdings(holdings)
    )

    # Create positions from holdings
    positions = []

    # Process stock positions
    stock_positions = _create_stock_positions(non_cash_holdings)
    positions.extend(stock_positions)

    # Process option positions with stock tickers for unpaired option identification
    option_positions = _create_option_positions(non_cash_holdings, stock_tickers)
    positions.extend(option_positions)

    # Add cash and unknown positions
    positions.extend(cash_positions)
    positions.extend(unknown_positions)

    # Synchronize option underlying prices with paired stocks
    positions = _synchronize_option_underlying_prices(positions)

    # We no longer need to update unpaired options separately as they're updated during creation
    logger.debug("Using raw CSV prices with unpaired options updated during creation")

    # If update_prices flag is set, update all positions
    if update_prices:
        logger.info("Updating prices for all positions from market data")
        positions = _update_all_prices(positions)

    # Create the portfolio
    portfolio = Portfolio(
        positions=positions,
        pending_activity_value=pending_activity_value,
    )

    logger.debug(
        f"Portfolio processing complete: {len(positions)} positions ({len(cash_positions)} cash, {len(unknown_positions)} unknown)"
    )
    return portfolio


def _compute_option_deltas(option_positions: list[OptionPosition]) -> dict:
    """
    Compute all option deltas up front and return a value-based delta map.
    """
    delta_map = {}
    for position in option_positions:
        cache_key = (
            position.ticker,
            position.strike,
            position.expiry,
            position.option_type,
        )
        underlying_price = ticker_service.get_price(position.ticker)
        if underlying_price == 0:
            underlying_price = position.strike
        option_price = position.price
        if option_price is None or option_price <= 0:
            raise ValueError(
                f"Option market price must be positive, got {option_price}"
            )
        delta = calculate_option_delta(
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )
        delta_map[cache_key] = delta
    return delta_map


def _calculate_position_values(portfolio: Portfolio, delta_map: dict) -> dict:
    """
    Calculate value breakdowns for different position types, using a precomputed delta_map for options.
    """
    position_values = {
        "long_stocks": {"value": 0.0, "beta_adjusted": 0.0},
        "short_stocks": {"value": 0.0, "beta_adjusted": 0.0},
        "long_options": {"value": 0.0, "beta_adjusted": 0.0, "delta_exposure": 0.0},
        "short_options": {"value": 0.0, "beta_adjusted": 0.0, "delta_exposure": 0.0},
        "cash_value": 0.0,
        "unknown_value": 0.0,
    }
    for position in portfolio.positions:
        position_value = _get_safe_position_value(position)
        if position_value is None:
            continue
        if position.position_type == "stock":
            _process_stock_position(position, position_value, position_values)
        elif position.position_type == "option":
            _process_option_position_with_deltas(
                position, position_value, position_values, delta_map
            )
        elif position.position_type == "cash":
            position_values["cash_value"] += position_value
        elif position.position_type == "unknown":
            position_values["unknown_value"] += position_value
    return position_values


def _process_option_position_with_deltas(
    position: Position, position_value: float, position_values: dict, delta_map: dict
) -> None:
    """
    Process an option position and update the position values dictionary using a precomputed delta_map.
    """
    underlying_price, beta = _get_option_market_data(position)
    option_price = position.price
    if option_price is None or option_price <= 0:
        raise ValueError(f"Option market price must be positive, got {option_price}")
    cache_key = (
        position.ticker,
        position.strike,
        position.expiry,
        position.option_type,
    )
    delta = delta_map[cache_key]
    market_exposure = calculate_option_exposure(
        quantity=position.quantity,
        underlying_price=underlying_price,
        delta=delta,
    )
    beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
    option_category = categorize_option_by_delta(delta)
    if option_category == "long":
        position_values["long_options"]["value"] += position_value
        position_values["long_options"]["beta_adjusted"] += beta_adjusted
        position_values["long_options"]["delta_exposure"] += market_exposure
    else:
        position_values["short_options"]["value"] += position_value
        position_values["short_options"]["beta_adjusted"] += beta_adjusted
        position_values["short_options"]["delta_exposure"] += market_exposure


def get_portfolio_exposures(
    portfolio: Portfolio, delta_map: dict | None = None
) -> dict:
    """
    Calculate exposure metrics for a portfolio, using a precomputed delta_map for options.
    If delta_map is not provided, compute it internally (for backward compatibility).
    """
    if delta_map is None:
        option_positions = [
            p for p in portfolio.positions if p.position_type == "option"
        ]
        delta_map = _compute_option_deltas(option_positions)
    logger.debug("Calculating portfolio exposures")
    total_value = sum(p.market_value for p in portfolio.positions)
    if portfolio.pending_activity_value is not None and not pd.isna(
        portfolio.pending_activity_value
    ):
        total_value += portfolio.pending_activity_value
    exposures = {
        Exposures.LONG_STOCK: 0.0,
        Exposures.SHORT_STOCK: 0.0,
        Exposures.LONG_OPTION: 0.0,
        Exposures.SHORT_OPTION: 0.0,
        Exposures.LONG_STOCK_BETA_ADJ: 0.0,
        Exposures.SHORT_STOCK_BETA_ADJ: 0.0,
        Exposures.LONG_OPTION_BETA_ADJ: 0.0,
        Exposures.SHORT_OPTION_BETA_ADJ: 0.0,
        Exposures.NET_MARKET: 0.0,
        Exposures.BETA_ADJ: 0.0,
        Exposures.TOTAL_VALUE: total_value,
    }
    for position in portfolio.stock_positions:
        if is_cash_or_short_term(
            position.ticker, description=getattr(position, "description", "")
        ):
            continue
        market_exposure = calculate_stock_exposure(position.quantity, position.price)
        beta = ticker_service.get_beta(position.ticker)
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        exposures[Exposures.BETA_ADJ] += beta_adjusted
        if market_exposure > 0:
            exposures[Exposures.LONG_STOCK] += market_exposure
            exposures[Exposures.LONG_STOCK_BETA_ADJ] += beta_adjusted
        else:
            exposures[Exposures.SHORT_STOCK] += market_exposure
            exposures[Exposures.SHORT_STOCK_BETA_ADJ] += beta_adjusted
    for position in portfolio.option_positions:
        cache_key = (
            position.ticker,
            position.strike,
            position.expiry,
            position.option_type,
        )
        delta = delta_map[cache_key]
        underlying_price = ticker_service.get_price(position.ticker)
        if underlying_price == 0:
            underlying_price = position.strike
        market_exposure = calculate_option_exposure(
            quantity=position.quantity,
            underlying_price=underlying_price,
            delta=delta,
        )
        beta = ticker_service.get_beta(position.ticker)
        beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)
        exposures[Exposures.BETA_ADJ] += beta_adjusted
        if market_exposure > 0:
            exposures[Exposures.LONG_OPTION] += market_exposure
            exposures[Exposures.LONG_OPTION_BETA_ADJ] += beta_adjusted
        else:
            exposures[Exposures.SHORT_OPTION] += market_exposure
            exposures[Exposures.SHORT_OPTION_BETA_ADJ] += beta_adjusted
    exposures[Exposures.NET_MARKET] = (
        exposures[Exposures.LONG_STOCK]
        + exposures[Exposures.SHORT_STOCK]
        + exposures[Exposures.LONG_OPTION]
        + exposures[Exposures.SHORT_OPTION]
    )
    logger.debug(f"Portfolio exposures calculated: {exposures}")
    return exposures


def create_portfolio_summary(portfolio: Portfolio) -> PortfolioSummary:
    """
    Create a summary of portfolio metrics including values and exposures.

    This function aggregates position data to calculate key portfolio metrics:
    - Total value across all positions
    - Value breakdowns by position type (stock, option, cash)
    - Market exposure metrics
    - Beta-adjusted exposure

    Args:
        portfolio: The portfolio to summarize

    Returns:
        PortfolioSummary: A data object containing all summary metrics
    """
    logger.debug("Creating portfolio summary")

    # Precompute option deltas
    option_positions = [p for p in portfolio.positions if p.position_type == "option"]
    delta_map = _compute_option_deltas(option_positions)

    # Calculate position values by type
    position_values = _calculate_position_values(portfolio, delta_map)

    # Calculate total portfolio value
    total_value = _calculate_total_value(
        position_values, portfolio.pending_activity_value
    )

    # Calculate portfolio exposures
    exposures = get_portfolio_exposures(portfolio, delta_map)

    # Calculate net exposure percentage
    net_exposure_pct = _calculate_net_exposure_percentage(
        exposures["net_market_exposure"], total_value
    )

    # Create and return the portfolio summary
    summary = PortfolioSummary(
        total_value=total_value,
        stock_value=position_values["long_stocks"]["value"]
        + position_values["short_stocks"]["value"],
        option_value=position_values["long_options"]["value"]
        + position_values["short_options"]["value"],
        cash_value=position_values["cash_value"],
        unknown_value=position_values["unknown_value"],
        pending_activity_value=_get_pending_activity_value(
            portfolio.pending_activity_value
        ),
        net_market_exposure=exposures["net_market_exposure"],
        net_exposure_pct=net_exposure_pct,
        beta_adjusted_exposure=exposures["beta_adjusted_exposure"],
    )

    logger.debug("Portfolio summary created successfully")
    return summary


def _get_safe_position_value(position: Position) -> float:
    """
    Get position market value, handling NaN values for cash positions.

    Args:
        position: The position to get the value for

    Returns:
        The position's market value, or 0.0 for cash positions with NaN value,
        or None if the position should be skipped
    """
    position_value = position.market_value

    if pd.isna(position_value):
        if position.position_type == "cash":
            # For cash positions with NaN value, set to 0
            logger.warning(
                f"Cash position {position.ticker} has NaN market value, setting to 0"
            )
            return 0.0
        else:
            logger.warning(f"Skipping position {position.ticker} with NaN market value")
            return None

    return position_value


def _process_stock_position(
    position: Position, position_value: float, position_values: dict
) -> None:
    """
    Process a stock position and update the position values dictionary.

    Args:
        position: The stock position to process
        position_value: The position's market value
        position_values: Dictionary to update with the position's values
    """
    # Skip cash-like positions (e.g., money market funds)
    if is_cash_or_short_term(
        position.ticker, description=getattr(position, "description", "")
    ):
        position_values["cash_value"] += position_value
        logger.debug(f"Categorized as cash-like: {position.ticker}")
        return

    # Get beta for exposure calculation
    beta = _get_position_beta(position.ticker)

    # Calculate beta-adjusted exposure for reporting
    market_exposure = calculate_stock_exposure(position.quantity, position.price)
    beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)

    # Update the appropriate category based on position direction
    if position.quantity > 0:
        position_values["long_stocks"]["value"] += position_value
        position_values["long_stocks"]["beta_adjusted"] += beta_adjusted
    else:
        # Short values are stored as negative
        position_values["short_stocks"]["value"] += position_value
        position_values["short_stocks"]["beta_adjusted"] += beta_adjusted


def _process_option_position(
    position: Position, position_value: float, position_values: dict, delta_cache: dict
) -> None:
    """
    Process an option position and update the position values dictionary.
    Uses a delta_cache to avoid duplicate delta calculations.
    """
    # Get underlying price and beta
    underlying_price, beta = _get_option_market_data(position)

    # Use the option's market price (fail if not present or <= 0)
    option_price = position.price
    if option_price is None or option_price <= 0:
        raise ValueError(f"Option market price must be positive, got {option_price}")

    # Use value-based cache key
    cache_key = (
        position.ticker,
        position.strike,
        position.expiry,
        position.option_type,
    )

    if cache_key not in delta_cache:
        delta = calculate_option_delta(
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=underlying_price,
            option_price=option_price,
        )
        delta_cache[cache_key] = delta
    else:
        delta = delta_cache[cache_key]

    market_exposure = calculate_option_exposure(
        quantity=position.quantity,
        underlying_price=underlying_price,
        delta=delta,
    )

    beta_adjusted = calculate_beta_adjusted_exposure(market_exposure, beta)

    # Categorize based on delta exposure
    option_category = categorize_option_by_delta(delta)

    if option_category == "long":
        position_values["long_options"]["value"] += position_value
        position_values["long_options"]["beta_adjusted"] += beta_adjusted
        position_values["long_options"]["delta_exposure"] += market_exposure
    else:
        position_values["short_options"]["value"] += position_value
        position_values["short_options"]["beta_adjusted"] += beta_adjusted
        position_values["short_options"]["delta_exposure"] += market_exposure


def _get_option_market_data(position: Position) -> tuple[float, float]:
    """
    Get market data (underlying price and beta) for an option position.

    Args:
        position: The option position

    Returns:
        Tuple of (underlying_price, beta)
    """
    # Use ticker service to get price and beta
    underlying_price = ticker_service.get_price(position.ticker)
    beta = ticker_service.get_beta(position.ticker)

    # If price is 0, use strike as fallback
    if underlying_price == 0:
        underlying_price = position.strike

    return underlying_price, beta


def _get_position_beta(ticker: str) -> float:
    """
    Get beta for a position, with fallback to 1.0.

    Args:
        ticker: The position ticker

    Returns:
        Beta value, or 1.0 if beta cannot be retrieved
    """
    # Use ticker service to get beta
    return ticker_service.get_beta(ticker)


def _calculate_total_value(
    position_values: dict, pending_activity_value: float
) -> float:
    """
    Calculate total portfolio value from position values and pending activity.

    Args:
        position_values: Dictionary of position values by type
        pending_activity_value: Pending activity value

    Returns:
        Total portfolio value
    """
    total_value = (
        position_values["long_stocks"]["value"]
        + position_values["short_stocks"]["value"]
        + position_values["long_options"]["value"]
        + position_values["short_options"]["value"]
        + position_values["cash_value"]
        + position_values["unknown_value"]
    )

    # Add pending activity if available
    pending_activity = _get_pending_activity_value(pending_activity_value)
    if pending_activity != 0.0:
        total_value += pending_activity

    return total_value


def _get_pending_activity_value(pending_activity_value: float) -> float:
    """
    Get pending activity value, handling None and NaN values.

    Args:
        pending_activity_value: Raw pending activity value

    Returns:
        Cleaned pending activity value, or 0.0 if None or NaN
    """
    if pending_activity_value is None or pd.isna(pending_activity_value):
        return 0.0
    return pending_activity_value


def _calculate_net_exposure_percentage(
    net_market_exposure: float, total_value: float
) -> float:
    """
    Calculate net exposure as a percentage of total portfolio value.

    Args:
        net_market_exposure: Net market exposure value
        total_value: Total portfolio value

    Returns:
        Net exposure percentage, or 0.0 if total_value is 0
    """
    return (net_market_exposure / total_value) if total_value > 0 else 0.0


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
    logger.debug(f"Extracting pending activity value from holding: {holding}")

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
