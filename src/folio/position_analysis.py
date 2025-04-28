"""
Position analysis module.

This module provides functions for analyzing position contributions to portfolio
performance under different market scenarios.
"""

from typing import Any

import pandas as pd


def analyze_position_contributions(simulation_result: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze how each position contributes to portfolio P&L at different SPY changes.

    Args:
        simulation_result: Result dictionary from simulate_portfolio

    Returns:
        Dictionary with position contribution analysis results
    """
    spy_changes = simulation_result["spy_changes"]
    position_results = simulation_result["position_results"]

    # Initialize data structures
    contributions = {}
    contribution_percents = {}

    # For each SPY change level, calculate the contribution of each position
    for i, spy_change in enumerate(spy_changes):
        contributions[spy_change] = {}
        contribution_percents[spy_change] = {}

        # Get the total P&L at this SPY change level
        total_pnl = simulation_result["portfolio_pnls"][i]

        # Calculate each position's contribution
        for ticker, results in position_results.items():
            position_pnl = results[i]["pnl"]
            contributions[spy_change][ticker] = position_pnl

            # Calculate percentage contribution to total P&L
            # Handle the case where total_pnl is zero or very small
            if abs(total_pnl) < 0.01:
                contribution_percent = 0.0
            else:
                contribution_percent = (position_pnl / abs(total_pnl)) * 100

            contribution_percents[spy_change][ticker] = contribution_percent

    # Create a DataFrame for easier analysis
    contribution_df = pd.DataFrame(contributions).T
    contribution_df.index.name = "spy_change"
    contribution_df.reset_index(inplace=True)

    # Create a DataFrame for percentage contributions
    contribution_percent_df = pd.DataFrame(contribution_percents).T
    contribution_percent_df.index.name = "spy_change"
    contribution_percent_df.reset_index(inplace=True)

    # Find the top contributors at each SPY change level
    top_contributors = {}
    bottom_contributors = {}

    for spy_change in spy_changes:
        # Sort positions by absolute contribution
        sorted_contributions = sorted(
            contributions[spy_change].items(), key=lambda x: abs(x[1]), reverse=True
        )

        # Get top 5 contributors by absolute value
        top_contributors[spy_change] = sorted_contributions[:5]

        # For negative SPY changes, get top negative contributors
        # For positive SPY changes, get top positive contributors
        if spy_change < 0:
            # For negative SPY changes, we want positions that lose the most
            bottom_sorted = sorted(
                contributions[spy_change].items(), key=lambda x: x[1]
            )
            bottom_contributors[spy_change] = bottom_sorted[:5]
        else:
            # For positive SPY changes, we want positions that gain the least or lose
            bottom_sorted = sorted(
                contributions[spy_change].items(), key=lambda x: x[1]
            )
            bottom_contributors[spy_change] = bottom_sorted[:5]

    # Find positions that contribute most to the negative performance in rising markets
    # Focus on SPY changes > 0 where portfolio P&L is negative
    problematic_positions = {}
    for i, spy_change in enumerate(spy_changes):
        if spy_change > 0 and simulation_result["portfolio_pnls"][i] < 0:
            # Sort positions by contribution (most negative first)
            sorted_contributions = sorted(
                contributions[spy_change].items(), key=lambda x: x[1]
            )

            # Get positions with negative contributions
            negative_contributors = [
                (ticker, pnl) for ticker, pnl in sorted_contributions if pnl < 0
            ]

            problematic_positions[spy_change] = negative_contributors

    return {
        "contributions": contributions,
        "contribution_percents": contribution_percents,
        "contribution_df": contribution_df,
        "contribution_percent_df": contribution_percent_df,
        "top_contributors": top_contributors,
        "bottom_contributors": bottom_contributors,
        "problematic_positions": problematic_positions,
    }


def find_key_spy_levels(simulation_result: dict[str, Any]) -> dict[str, Any]:
    """
    Find key SPY levels where portfolio behavior changes significantly.

    Args:
        simulation_result: Result dictionary from simulate_portfolio

    Returns:
        Dictionary with key SPY levels and related information
    """
    spy_changes = simulation_result["spy_changes"]
    portfolio_pnls = simulation_result["portfolio_pnls"]

    # Find where P&L changes from positive to negative or vice versa
    inflection_points = []
    for i in range(1, len(spy_changes)):
        if (portfolio_pnls[i - 1] >= 0 and portfolio_pnls[i] < 0) or (
            portfolio_pnls[i - 1] < 0 and portfolio_pnls[i] >= 0
        ):
            inflection_points.append((spy_changes[i], portfolio_pnls[i]))

    # Find the SPY change where portfolio P&L is maximum
    max_pnl_index = portfolio_pnls.index(max(portfolio_pnls))
    max_pnl_spy_change = spy_changes[max_pnl_index]

    # Find the SPY change where portfolio P&L is minimum
    min_pnl_index = portfolio_pnls.index(min(portfolio_pnls))
    min_pnl_spy_change = spy_changes[min_pnl_index]

    # Find the SPY change where portfolio starts to decline in rising markets
    declining_in_rising_market = None
    for i in range(1, len(spy_changes)):
        if (
            spy_changes[i - 1] < spy_changes[i]
            and portfolio_pnls[i - 1] > portfolio_pnls[i]
            and spy_changes[i] > 0
        ):
            declining_in_rising_market = spy_changes[i]
            break

    return {
        "inflection_points": inflection_points,
        "max_pnl_spy_change": max_pnl_spy_change,
        "min_pnl_spy_change": min_pnl_spy_change,
        "declining_in_rising_market": declining_in_rising_market,
    }
