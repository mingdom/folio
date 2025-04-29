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

from ..data.stock import StockOracle, stockdata
from ..domain import (
    OptionPosition,
    Portfolio,
    PortfolioGroup,
    PortfolioHolding,
    PortfolioSummary,
    StockPosition,
)

# Set up logging
logger = logging.getLogger(__name__)


def process_portfolio(
    holdings: list[PortfolioHolding],
    market_oracle: StockOracle,
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

    # Separate cash-like positions and unknown positions
    non_cash_holdings = []
    cash_positions = []
    unknown_positions = []
    pending_activity_value = 0.0

    for holding in holdings:
        # Check for pending activity
        if holding.symbol.upper() == "PENDING ACTIVITY":
            pending_activity_value += holding.value
            logger.debug(f"Identified pending activity: {holding.value}")
            continue

        # Check for cash-like positions
        if market_oracle.is_cash_like(holding.symbol, holding.description):
            # Convert to StockPosition for cash-like holdings
            cash_position = StockPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            cash_positions.append(cash_position)
            logger.debug(f"Identified cash-like position: {holding.symbol}")
        # Check for unknown/invalid positions
        elif not market_oracle.is_valid_stock_symbol(holding.symbol):
            unknown_positions.append(holding)
            logger.warning(f"Identified unknown/invalid position: {holding.symbol}")
        else:
            non_cash_holdings.append(holding)

    # Create portfolio groups from non-cash, non-unknown holdings
    groups = create_portfolio_groups(non_cash_holdings, market_oracle)
    logger.debug(f"Created {len(groups)} portfolio groups")

    # Create and return the portfolio
    portfolio = Portfolio(
        groups=groups,
        cash_positions=cash_positions,
        unknown_positions=unknown_positions,
        pending_activity_value=pending_activity_value,
    )

    logger.debug(
        f"Portfolio processing complete: {len(groups)} groups, {len(cash_positions)} cash positions, {len(unknown_positions)} unknown positions"
    )
    return portfolio


def create_portfolio_groups(
    holdings: list[PortfolioHolding], market_oracle: StockOracle
) -> list[PortfolioGroup]:
    """
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
        # Check if this is an option based on the symbol pattern (usually starts with a space and hyphen)
        if holding.symbol.strip().startswith("-") or _is_option_description(
            holding.description
        ):
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
                    underlying_price=stock_holding.price,
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

            # Fetch the underlying price
            try:
                underlying_price = market_oracle.get_price(ticker)
            except Exception as e:
                logger.warning(f"Could not fetch price for {ticker}: {e}")
                underlying_price = 0.0

            # Create option position
            option_position = OptionPosition(
                ticker=data["ticker"],
                quantity=data["quantity"],
                strike=data["strike"],
                expiry=data["expiry"],
                option_type=data["option_type"],
                price=data["holding"].price,
                underlying_price=underlying_price,
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

    # Initialize values
    total_value = 0.0
    stock_value = 0.0
    option_value = 0.0
    cash_value = 0.0
    unknown_value = 0.0
    net_market_exposure = 0.0
    weighted_beta_sum = 0.0
    total_stock_value = 0.0  # For beta calculation

    # Process groups
    for group in portfolio.groups:
        # Process stock position
        if group.stock_position:
            position_value = group.stock_position.market_value
            # Skip NaN values
            if pd.isna(position_value):
                logger.warning(
                    f"Skipping NaN market value for {group.stock_position.ticker}"
                )
                continue

            stock_value += position_value
            total_value += position_value

            # Get beta for exposure calculation
            try:
                beta = stockdata.get_beta(group.stock_position.ticker)
                weighted_beta_sum += beta * position_value
                total_stock_value += position_value
                net_market_exposure += position_value * beta
            except Exception as e:
                logger.warning(
                    f"Could not calculate beta for {group.stock_position.ticker}: {e}"
                )

        # Process option positions
        for option in group.option_positions:
            position_value = option.market_value
            # Skip NaN values
            if pd.isna(position_value):
                logger.warning(
                    f"Skipping NaN market value for option {option.ticker} {option.strike} {option.expiry}"
                )
                continue

            option_value += position_value
            total_value += position_value

            # Options exposure is more complex and would be calculated in a separate function
            # For now, we're just adding the market value to the total

    # Process cash positions
    for cash_position in portfolio.cash_positions:
        position_value = cash_position.market_value
        # Skip NaN values
        if pd.isna(position_value):
            logger.warning(
                f"Skipping NaN market value for cash position {cash_position.ticker}"
            )
            continue

        cash_value += position_value
        total_value += position_value
        # Cash has zero beta, so no contribution to market exposure

    # Process unknown positions
    for unknown_position in portfolio.unknown_positions:
        position_value = unknown_position.value
        # Skip NaN values
        if pd.isna(position_value):
            logger.warning(
                f"Skipping NaN value for unknown position {unknown_position.symbol}"
            )
            continue

        unknown_value += position_value
        total_value += position_value
        # Unknown positions don't contribute to beta or market exposure

    # Add pending activity
    total_value += portfolio.pending_activity_value

    # Calculate portfolio beta (weighted average of stock betas)
    portfolio_beta = None
    if total_stock_value > 0:
        portfolio_beta = weighted_beta_sum / total_stock_value

    # Create and return summary
    summary = PortfolioSummary(
        total_value=total_value,
        stock_value=stock_value,
        option_value=option_value,
        cash_value=cash_value,
        unknown_value=unknown_value,
        pending_activity_value=portfolio.pending_activity_value,
        net_market_exposure=net_market_exposure,
        portfolio_beta=portfolio_beta,
    )

    logger.debug(
        f"Portfolio summary: total value = {total_value:.2f}, beta = {portfolio_beta}"
    )
    return summary


def get_portfolio_exposures(portfolio: Portfolio) -> dict:  # noqa: ARG001
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

    # This is a placeholder implementation
    # A full implementation would calculate delta-adjusted exposures for options
    # and beta-adjusted exposures for all positions

    logger.debug("Portfolio exposure calculation not fully implemented yet")
    return exposures


# Helper functions


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
