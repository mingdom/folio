"""Utility functions for AI portfolio analysis."""

import logging
from typing import Any

from .data_model import PortfolioGroup, PortfolioSummary
from .portfolio import calculate_position_weight
from .portfolio_value import (
    calculate_component_percentages,
    get_portfolio_component_values,
)

logger = logging.getLogger(__name__)

# System prompt for the AI portfolio advisor
PORTFOLIO_ADVISOR_SYSTEM_PROMPT = """
You are a professional financial advisor specializing in portfolio analysis. Your role is strictly limited to:

1. Analyzing the client's investment portfolio
2. Providing insights on portfolio composition, risk, diversification, and performance
3. Offering investment advice related to the client's holdings
4. Answering questions about financial markets, investment strategies, and specific securities

Important guidelines:
- ONLY respond to questions related to investing, finance, and the client's portfolio
- REFUSE to answer any questions unrelated to finance or investments
- If asked about non-financial topics, politely redirect the conversation back to the portfolio
- Maintain a professional, knowledgeable tone
- Base your analysis on the portfolio data provided
- Be transparent about limitations in your analysis
- When discussing portfolio allocation, refer to the detailed breakdown provided in the context
- When discussing exposure, consider both the raw exposure values and beta-adjusted values
- Pay attention to the percentage of portfolio for each metric to provide context

Your goal is to help clients understand their investments and make informed decisions about their portfolio.
"""


def prepare_portfolio_data_for_analysis(
    groups: list[PortfolioGroup], summary: PortfolioSummary
) -> dict[str, Any]:
    """
    Prepare portfolio data for AI analysis.

    Args:
        groups: List of portfolio groups
        summary: Portfolio summary object

    Returns:
        Dictionary with formatted portfolio data
    """
    positions = []

    # Process each portfolio group
    for group in groups:
        # Add stock position if present
        if group.stock_position:
            stock = group.stock_position
            positions.append({
                "ticker": stock.ticker,
                "position_type": "stock",
                "market_value": stock.market_exposure,
                "beta": stock.beta,
                "weight": calculate_position_weight(
                    stock.market_exposure, summary.net_market_exposure
                ),
                "quantity": stock.quantity,
            })

        # Add option positions if present
        for option in group.option_positions:
            positions.append({
                "ticker": option.ticker,
                "position_type": "option",
                "market_value": option.market_exposure,
                "beta": option.beta,
                "weight": calculate_position_weight(
                    option.market_exposure, summary.net_market_exposure
                ),
                "option_type": option.option_type,
                "strike": option.strike,
                "expiry": option.expiry,
                "delta": option.delta,
            })

    # Enhanced summary data with portfolio value
    summary_data = {
        "portfolio_value": summary.portfolio_estimate_value,
        "net_market_exposure": summary.net_market_exposure,
        "long_exposure": summary.long_exposure.to_dict(),
        "short_exposure": summary.short_exposure.to_dict(),
        "options_exposure": summary.options_exposure.to_dict(),
        "cash_like_value": summary.cash_like_value,
    }

    # Get allocation data from existing portfolio_value functions
    values = get_portfolio_component_values(summary)
    percentages = calculate_component_percentages(values)

    # Create allocation data structure
    allocation_data = {"values": values, "percentages": percentages}

    return {
        "positions": positions,
        "summary": summary_data,
        "allocations": allocation_data,
    }
