#!/usr/bin/env python
"""
Compare Portfolio Implementations Test Script

This script compares the portfolio summary calculations between the old implementation
in src/folio/portfolio.py and the new implementation in src/folib/.

It loads the same portfolio data using both methods, calculates summaries, and
compares the results to identify discrepancies.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import old implementation
# Import new implementation
from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.domain import Portfolio, PortfolioSummary
from src.folib.services.portfolio_service import create_portfolio_summary
from src.folio.portfolio import process_portfolio_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("portfolio_comparison.log"),
    ],
)
logger = logging.getLogger("portfolio_comparison")

# Rich console for pretty output
console = Console()


def load_portfolio_old_method(file_path: str) -> tuple[list[Any], Any, list[dict]]:
    """
    Load portfolio using the old method.

    Args:
        file_path: Path to the portfolio CSV file

    Returns:
        Tuple of (groups, summary, positions)
    """
    logger.info(f"Loading portfolio using old method from: {file_path}")
    df = pd.read_csv(file_path)
    groups, summary, positions = process_portfolio_data(df, update_prices=False)
    logger.info(f"Loaded {len(groups)} groups with old method")
    return groups, summary, positions


def load_portfolio_new_method(file_path: str) -> tuple[Portfolio, PortfolioSummary]:
    """
    Load portfolio using the new method.

    Args:
        file_path: Path to the portfolio CSV file

    Returns:
        Tuple of (portfolio, summary)
    """
    logger.info(f"Loading portfolio using new method from: {file_path}")
    df = load_portfolio_from_csv(file_path)
    holdings = parse_portfolio_holdings(df)

    # Create portfolio groups for comparison with old implementation
    # Extract pending activity value
    from src.folib.services.portfolio_service import (
        _get_pending_activity,
        create_portfolio_groups,
    )

    pending_activity_value = _get_pending_activity(holdings)

    # Filter out pending activity from holdings
    filtered_holdings = [
        h for h in holdings if not h.symbol.upper().startswith("PENDING")
    ]

    # Create portfolio groups
    groups = create_portfolio_groups(filtered_holdings)

    # Create positions list from groups
    positions = []
    for group in groups:
        if group.stock_position:
            positions.append(group.stock_position)
        positions.extend(group.option_positions)

    # Create cash positions
    # Note: We don't need to create CashPosition objects here because the portfolio_service.py
    # will automatically identify cash-like positions (FMPXX, FZDXX, etc.) and treat them as cash
    # in the create_portfolio_summary function.
    # This avoids double-counting cash positions.

    # Create portfolio
    portfolio = Portfolio(
        positions=positions,
        pending_activity_value=pending_activity_value,
    )

    # Create portfolio summary
    summary = create_portfolio_summary(portfolio)

    logger.info(f"Loaded {len(portfolio.positions)} positions with new method")
    return portfolio, summary


def compare_summaries(
    old_summary: Any, new_summary: PortfolioSummary
) -> dict[str, dict]:
    """
    Compare portfolio summaries from old and new implementations.

    Args:
        old_summary: Summary from old implementation
        new_summary: Summary from new implementation

    Returns:
        Dictionary of comparison results
    """
    logger.info("Comparing portfolio summaries")

    # Define metrics to compare
    metrics = {
        "Total Value": {
            "old": old_summary.portfolio_estimate_value,
            "new": new_summary.total_value,
            "description": "Total portfolio value including all positions",
        },
        "Stock Value": {
            "old": old_summary.stock_value,
            "new": new_summary.stock_value,
            "description": "Total value of stock positions",
        },
        "Option Value": {
            "old": old_summary.option_value,
            "new": new_summary.option_value,
            "description": "Total value of option positions",
        },
        "Cash Value": {
            "old": old_summary.cash_like_value,
            "new": new_summary.cash_value,
            "description": "Total value of cash positions",
        },
        "Pending Activity": {
            "old": old_summary.pending_activity_value,
            "new": new_summary.pending_activity_value,
            "description": "Value of pending activity",
        },
        # Note: We're not comparing net_market_exposure directly because the calculation methods
        # are different between the old and new implementations. Instead, we're comparing the
        # exposure metrics in the analyze_exposure_differences function.
    }

    # Calculate differences and percentages
    for key, values in metrics.items():
        old_value = values["old"]
        new_value = values["new"]

        # Calculate absolute difference
        diff = new_value - old_value
        values["diff"] = diff

        # Calculate percentage difference
        if old_value != 0:
            pct_diff = (diff / abs(old_value)) * 100
        else:
            pct_diff = float("inf") if diff != 0 else 0
        values["pct_diff"] = pct_diff

        # Determine if the difference is significant (more than 1%)
        values["significant"] = abs(pct_diff) > 1.0

        logger.info(
            f"{key}: Old={old_value:.2f}, New={new_value:.2f}, Diff={diff:.2f} ({pct_diff:.2f}%)"
        )

    return metrics


def compare_positions(
    old_groups: list[Any], new_portfolio: Portfolio
) -> dict[str, dict]:
    """
    Compare positions between old and new implementations.

    Args:
        old_groups: Portfolio groups from old implementation
        new_portfolio: Portfolio from new implementation

    Returns:
        Dictionary of comparison results by ticker
    """
    logger.info("Comparing positions")

    # Create dictionaries for easy lookup
    old_positions_by_ticker = {}
    for group in old_groups:
        ticker = group.ticker

        # Add stock position if it exists
        if group.stock_position:
            old_positions_by_ticker[ticker] = {
                "ticker": ticker,
                "quantity": group.stock_position.quantity,
                "price": group.stock_position.price,
                "market_value": group.stock_position.market_value,
                "position_type": "stock",
                "raw_data": getattr(group.stock_position, "raw_data", None),
            }
            logger.debug(
                f"Old stock position: {ticker}, value: {group.stock_position.market_value:.2f}"
            )

        # Add option positions
        for i, option in enumerate(group.option_positions):
            option_key = f"{ticker}_option_{i}"
            old_positions_by_ticker[option_key] = {
                "ticker": ticker,
                "quantity": option.quantity,
                "price": option.price,
                "market_value": option.market_value,
                "position_type": "option",
                "strike": option.strike,
                "expiry": option.expiry,
                "option_type": option.option_type,
                "delta": getattr(option, "delta", None),
                "delta_exposure": getattr(option, "delta_exposure", None),
                "raw_data": getattr(option, "raw_data", None),
            }
            logger.debug(
                f"Old option position: {option_key}, value: {option.market_value:.2f}, delta: {getattr(option, 'delta', 'N/A')}"
            )

    # Create dictionary for new positions
    new_positions_by_ticker = {}
    for position in new_portfolio.positions:
        ticker = position.ticker

        if position.position_type == "stock":
            # Skip cash positions for comparison
            if ticker.upper() in ["SPAXX", "CORE", "FDRXX", "FMPXX", "FZDXX"]:
                logger.debug(f"Skipping cash position {ticker} in position comparison")
                continue

            new_positions_by_ticker[ticker] = {
                "ticker": ticker,
                "quantity": position.quantity,
                "price": position.price,
                "market_value": position.market_value,
                "position_type": "stock",
                "raw_data": getattr(position, "raw_data", None),
            }
            logger.debug(
                f"New stock position: {ticker}, value: {position.market_value:.2f}"
            )
        elif position.position_type == "option":
            # For options, we need to handle multiple options for the same ticker
            option_count = sum(
                1 for p in new_positions_by_ticker if p.startswith(f"{ticker}_option_")
            )
            option_key = f"{ticker}_option_{option_count}"

            new_positions_by_ticker[option_key] = {
                "ticker": ticker,
                "quantity": position.quantity,
                "price": position.price,
                "market_value": position.market_value,
                "position_type": "option",
                "strike": position.strike,
                "expiry": position.expiry,
                "option_type": position.option_type,
                "raw_data": getattr(position, "raw_data", None),
            }
            logger.debug(
                f"New option position: {option_key}, value: {position.market_value:.2f}"
            )

    # Compare positions
    comparison = {}
    all_tickers = set(old_positions_by_ticker.keys()) | set(
        new_positions_by_ticker.keys()
    )

    for ticker in all_tickers:
        old_pos = old_positions_by_ticker.get(ticker)
        new_pos = new_positions_by_ticker.get(ticker)

        if old_pos and new_pos:
            # Both implementations have this position
            market_value_diff = new_pos["market_value"] - old_pos["market_value"]
            if old_pos["market_value"] != 0:
                market_value_pct_diff = (
                    market_value_diff / abs(old_pos["market_value"])
                ) * 100
            else:
                market_value_pct_diff = float("inf") if market_value_diff != 0 else 0

            comparison[ticker] = {
                "ticker": ticker,
                "position_type": old_pos["position_type"],
                "old_market_value": old_pos["market_value"],
                "new_market_value": new_pos["market_value"],
                "market_value_diff": market_value_diff,
                "market_value_pct_diff": market_value_pct_diff,
                "significant": abs(market_value_pct_diff) > 1.0,
                "status": "both",
            }
        elif old_pos:
            # Only in old implementation
            comparison[ticker] = {
                "ticker": ticker,
                "position_type": old_pos["position_type"],
                "old_market_value": old_pos["market_value"],
                "new_market_value": 0,
                "market_value_diff": -old_pos["market_value"],
                "market_value_pct_diff": -100.0,
                "significant": True,
                "status": "old_only",
            }
        elif new_pos:
            # Only in new implementation
            comparison[ticker] = {
                "ticker": ticker,
                "position_type": new_pos["position_type"],
                "old_market_value": 0,
                "new_market_value": new_pos["market_value"],
                "market_value_diff": new_pos["market_value"],
                "market_value_pct_diff": float("inf"),
                "significant": True,
                "status": "new_only",
            }

    return comparison


def analyze_exposure_differences(
    old_summary: Any, new_portfolio: Portfolio
) -> dict[str, Any]:
    """
    Analyze differences in exposure calculations.

    Args:
        old_summary: Summary from old implementation
        new_portfolio: Portfolio from new implementation

    Returns:
        Dictionary with analysis results
    """
    logger.info("Analyzing exposure differences")

    # Get exposures from old implementation
    old_net_exposure = old_summary.net_market_exposure
    old_long_exposure = old_summary.long_exposure.total_exposure
    old_short_exposure = abs(old_summary.short_exposure.total_exposure)

    # Log detailed old exposure components
    logger.debug("Old implementation exposure components:")
    logger.debug(
        f"  Long stock exposure: {old_summary.long_exposure.stock_exposure:.2f}"
    )
    logger.debug(
        f"  Long option delta exposure: {old_summary.long_exposure.option_delta_exposure:.2f}"
    )
    logger.debug(
        f"  Short stock exposure: {abs(old_summary.short_exposure.stock_exposure):.2f}"
    )
    logger.debug(
        f"  Short option delta exposure: {abs(old_summary.short_exposure.option_delta_exposure):.2f}"
    )

    # Calculate exposures for new implementation
    from src.folib.services.portfolio_service import get_portfolio_exposures

    new_exposures = get_portfolio_exposures(new_portfolio)
    new_net_exposure = new_exposures["net_market_exposure"]
    new_long_stock_exposure = new_exposures["long_stock_exposure"]
    new_short_stock_exposure = new_exposures["short_stock_exposure"]
    new_long_option_exposure = new_exposures["long_option_exposure"]
    new_short_option_exposure = new_exposures["short_option_exposure"]

    # Log detailed new exposure components
    logger.debug("New implementation exposure components:")
    logger.debug(f"  Long stock exposure: {new_long_stock_exposure:.2f}")
    logger.debug(f"  Long option exposure: {new_long_option_exposure:.2f}")
    logger.debug(f"  Short stock exposure: {new_short_stock_exposure:.2f}")
    logger.debug(f"  Short option exposure: {new_short_option_exposure:.2f}")

    # Calculate total long and short exposures
    new_long_exposure = new_long_stock_exposure + new_long_option_exposure
    new_short_exposure = new_short_stock_exposure + new_short_option_exposure

    # Compare exposures
    analysis = {
        "Net Exposure": {
            "old": old_net_exposure,
            "new": new_net_exposure,
            "diff": new_net_exposure - old_net_exposure,
            "pct_diff": ((new_net_exposure - old_net_exposure) / abs(old_net_exposure))
            * 100
            if old_net_exposure != 0
            else float("inf"),
        },
        "Long Exposure": {
            "old": old_long_exposure,
            "new": new_long_exposure,
            "diff": new_long_exposure - old_long_exposure,
            "pct_diff": (
                (new_long_exposure - old_long_exposure) / abs(old_long_exposure)
            )
            * 100
            if old_long_exposure != 0
            else float("inf"),
        },
        "Short Exposure": {
            "old": old_short_exposure,
            "new": new_short_exposure,
            "diff": new_short_exposure - old_short_exposure,
            "pct_diff": (
                (new_short_exposure - old_short_exposure) / abs(old_short_exposure)
            )
            * 100
            if old_short_exposure != 0
            else float("inf"),
        },
    }

    # Add detailed breakdown
    analysis["Details"] = {
        "old_long_stock_exposure": old_summary.long_exposure.stock_exposure,
        "old_long_option_exposure": old_summary.long_exposure.option_delta_exposure,
        "old_short_stock_exposure": abs(old_summary.short_exposure.stock_exposure),
        "old_short_option_exposure": abs(
            old_summary.short_exposure.option_delta_exposure
        ),
        "new_long_stock_exposure": new_long_stock_exposure,
        "new_long_option_exposure": new_long_option_exposure,
        "new_short_stock_exposure": new_short_stock_exposure,
        "new_short_option_exposure": new_short_option_exposure,
    }

    return analysis


def print_summary_comparison(metrics: dict[str, dict]) -> None:
    """
    Print a table comparing summary metrics.

    Args:
        metrics: Dictionary of comparison results
    """
    table = Table(title="Portfolio Summary Comparison")

    table.add_column("Metric", style="cyan")
    table.add_column("Old Value", justify="right")
    table.add_column("New Value", justify="right")
    table.add_column("Difference", justify="right")
    table.add_column("% Diff", justify="right")
    table.add_column("Significant", justify="center")

    for key, values in metrics.items():
        old_value = values["old"]
        new_value = values["new"]
        diff = values["diff"]
        pct_diff = values["pct_diff"]
        significant = values["significant"]

        # Format values
        old_str = f"${old_value:,.2f}"
        new_str = f"${new_value:,.2f}"
        diff_str = f"${diff:,.2f}"
        pct_diff_str = f"{pct_diff:.2f}%"

        # Determine row style based on significance
        sig_str = "✓" if significant else ""
        row_style = "red" if significant else None

        table.add_row(
            key, old_str, new_str, diff_str, pct_diff_str, sig_str, style=row_style
        )

    console.print(table)


def print_position_comparison(comparison: dict[str, dict]) -> None:
    """
    Print a table comparing positions.

    Args:
        comparison: Dictionary of position comparison results
    """
    # Filter for significant differences
    significant_diffs = {k: v for k, v in comparison.items() if v["significant"]}

    if not significant_diffs:
        console.print("[green]No significant position differences found[/green]")
        return

    table = Table(
        title=f"Position Comparison (Showing {len(significant_diffs)} significant differences)"
    )

    table.add_column("Ticker", style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Status", style="cyan")
    table.add_column("Old Value", justify="right")
    table.add_column("New Value", justify="right")
    table.add_column("Difference", justify="right")
    table.add_column("% Diff", justify="right")

    for ticker, values in significant_diffs.items():
        position_type = values["position_type"]
        status = values["status"]
        old_value = values["old_market_value"]
        new_value = values["new_market_value"]
        diff = values["market_value_diff"]
        pct_diff = values["market_value_pct_diff"]

        # Format values
        old_str = f"${old_value:,.2f}"
        new_str = f"${new_value:,.2f}"
        diff_str = f"${diff:,.2f}"
        pct_diff_str = f"{pct_diff:.2f}%" if pct_diff != float("inf") else "∞"

        # Determine row style based on status
        row_style = "red" if status != "both" else None

        table.add_row(
            ticker,
            position_type,
            status,
            old_str,
            new_str,
            diff_str,
            pct_diff_str,
            style=row_style,
        )

    console.print(table)


def print_exposure_analysis(analysis: dict[str, Any]) -> None:
    """
    Print exposure analysis.

    Args:
        analysis: Dictionary with exposure analysis results
    """
    table = Table(title="Exposure Analysis")

    table.add_column("Metric", style="cyan")
    table.add_column("Old Value", justify="right")
    table.add_column("New Value", justify="right")
    table.add_column("Difference", justify="right")
    table.add_column("% Diff", justify="right")

    for key, values in analysis.items():
        if key == "Details":
            continue

        old_value = values["old"]
        new_value = values["new"]
        diff = values["diff"]
        pct_diff = values["pct_diff"]

        # Format values
        old_str = f"${old_value:,.2f}"
        new_str = f"${new_value:,.2f}"
        diff_str = f"${diff:,.2f}"
        pct_diff_str = f"{pct_diff:.2f}%" if pct_diff != float("inf") else "∞"

        # Determine row style based on significance
        row_style = "red" if abs(pct_diff) > 1.0 else None

        table.add_row(key, old_str, new_str, diff_str, pct_diff_str, style=row_style)

    console.print(table)

    # Print detailed breakdown
    details = analysis["Details"]

    detail_table = Table(title="Exposure Breakdown")
    detail_table.add_column("Component", style="cyan")
    detail_table.add_column("Old Value", justify="right")
    detail_table.add_column("New Value", justify="right")

    detail_table.add_row(
        "Long Stock Exposure",
        f"${details['old_long_stock_exposure']:,.2f}",
        f"${details['new_long_stock_exposure']:,.2f}",
    )
    detail_table.add_row(
        "Long Option Exposure",
        f"${details['old_long_option_exposure']:,.2f}",
        f"${details['new_long_option_exposure']:,.2f}",
    )
    detail_table.add_row(
        "Short Stock Exposure",
        f"${details['old_short_stock_exposure']:,.2f}",
        f"${details['new_short_stock_exposure']:,.2f}",
    )
    detail_table.add_row(
        "Short Option Exposure",
        f"${details['old_short_option_exposure']:,.2f}",
        f"${details['new_short_option_exposure']:,.2f}",
    )

    console.print(detail_table)


def generate_recommendations(
    summary_metrics: dict[str, dict],
    position_comparison: dict[str, dict],
    exposure_analysis: dict[str, Any],
) -> list[str]:
    """
    Generate recommendations based on comparison results.

    Args:
        summary_metrics: Summary comparison results
        position_comparison: Position comparison results
        exposure_analysis: Exposure analysis results

    Returns:
        List of recommendations
    """
    recommendations = []

    # Check for significant summary differences
    significant_summary_diffs = [
        k for k, v in summary_metrics.items() if v["significant"]
    ]
    if significant_summary_diffs:
        recommendations.append(
            f"Investigate significant differences in summary metrics: {', '.join(significant_summary_diffs)}"
        )

    # Check for missing positions
    old_only = [k for k, v in position_comparison.items() if v["status"] == "old_only"]
    new_only = [k for k, v in position_comparison.items() if v["status"] == "new_only"]

    if old_only:
        recommendations.append(
            f"Investigate positions present in old implementation but missing in new: {', '.join(old_only)}"
        )

    if new_only:
        recommendations.append(
            f"Investigate positions present in new implementation but missing in old: {', '.join(new_only)}"
        )

    # Check for exposure differences
    for key, values in exposure_analysis.items():
        if key != "Details" and abs(values.get("pct_diff", 0)) > 5.0:
            recommendations.append(
                f"Investigate large difference in {key}: {values['pct_diff']:.2f}%"
            )

    # Add specific recommendations based on patterns
    if abs(exposure_analysis.get("Net Exposure", {}).get("pct_diff", 0)) > 5.0:
        recommendations.append(
            "Review option delta calculation in both implementations - this is likely the source of exposure differences"
        )

    if abs(summary_metrics.get("Stock Value", {}).get("pct_diff", 0)) > 1.0:
        recommendations.append(
            "Check stock position identification logic in both implementations"
        )

    if abs(summary_metrics.get("Option Value", {}).get("pct_diff", 0)) > 1.0:
        recommendations.append(
            "Check option position identification and valuation logic in both implementations"
        )

    if abs(summary_metrics.get("Cash Value", {}).get("pct_diff", 0)) > 1.0:
        recommendations.append(
            "Review cash position identification logic in both implementations"
        )

    return recommendations


def save_old_implementation_cache(old_groups, old_summary, portfolio_path):
    """
    Save the old implementation results to a cache file.

    Args:
        old_groups: Portfolio groups from old implementation
        old_summary: Summary from old implementation
        portfolio_path: Path to the portfolio CSV file
    """
    import hashlib
    import pickle

    # Create a hash of the portfolio file path to use in the cache filename
    portfolio_hash = hashlib.md5(portfolio_path.encode()).hexdigest()
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, f"old_implementation_{portfolio_hash}.pkl")

    # Save the old implementation results
    with open(cache_file, "wb") as f:
        pickle.dump((old_groups, old_summary), f)

    logger.info(f"Saved old implementation results to cache: {cache_file}")


def load_old_implementation_cache(portfolio_path):
    """
    Load the old implementation results from a cache file.

    Args:
        portfolio_path: Path to the portfolio CSV file

    Returns:
        Tuple of (old_groups, old_summary) or None if cache doesn't exist
    """
    import hashlib
    import pickle

    # Create a hash of the portfolio file path to use in the cache filename
    portfolio_hash = hashlib.md5(portfolio_path.encode()).hexdigest()
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
    cache_file = os.path.join(cache_dir, f"old_implementation_{portfolio_hash}.pkl")

    # Check if cache file exists
    if not os.path.exists(cache_file):
        logger.info(f"Cache file not found: {cache_file}")
        return None

    # Load the old implementation results
    try:
        with open(cache_file, "rb") as f:
            old_groups, old_summary = pickle.load(f)

        logger.info(f"Loaded old implementation results from cache: {cache_file}")
        return old_groups, old_summary
    except Exception as e:
        logger.error(f"Error loading cache file: {e}")
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Compare portfolio implementations")
    parser.add_argument(
        "--portfolio",
        "-p",
        type=str,
        default="private-data/portfolio-private.csv",
        help="Path to portfolio CSV file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--use-cache",
        "-c",
        action="store_true",
        help="Use cached old implementation results if available",
    )
    parser.add_argument(
        "--save-cache",
        "-s",
        action="store_true",
        help="Save old implementation results to cache",
    )
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print header
    console.print("[bold cyan]Portfolio Implementation Comparison[/bold cyan]")
    console.print(f"Portfolio file: [cyan]{args.portfolio}[/cyan]")
    console.print()

    # Check if portfolio file exists
    if not os.path.exists(args.portfolio):
        console.print(
            f"[bold red]Error:[/bold red] Portfolio file not found: {args.portfolio}"
        )
        return 1

    try:
        # Load old implementation results
        old_groups = None
        old_summary = None

        if args.use_cache:
            # Try to load from cache
            cache_result = load_old_implementation_cache(args.portfolio)
            if cache_result:
                old_groups, old_summary = cache_result
                console.print("[green]Using cached old implementation results[/green]")

        # If not using cache or cache loading failed, run the old implementation
        if old_groups is None or old_summary is None:
            old_groups, old_summary, _ = load_portfolio_old_method(args.portfolio)

            # Save to cache if requested
            if args.save_cache:
                save_old_implementation_cache(old_groups, old_summary, args.portfolio)

        # Always run the new implementation
        new_portfolio, new_summary = load_portfolio_new_method(args.portfolio)

        # Compare summaries
        summary_metrics = compare_summaries(old_summary, new_summary)

        # Compare positions
        position_comparison = compare_positions(old_groups, new_portfolio)

        # Analyze exposure differences
        exposure_analysis = analyze_exposure_differences(old_summary, new_portfolio)

        # Print results
        console.print("\n[bold cyan]Summary Comparison[/bold cyan]")
        print_summary_comparison(summary_metrics)

        console.print("\n[bold cyan]Position Comparison[/bold cyan]")
        print_position_comparison(position_comparison)

        console.print("\n[bold cyan]Exposure Analysis[/bold cyan]")
        print_exposure_analysis(exposure_analysis)

        # Generate recommendations
        recommendations = generate_recommendations(
            summary_metrics, position_comparison, exposure_analysis
        )

        console.print("\n[bold cyan]Recommendations[/bold cyan]")
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                console.print(f"{i}. {rec}")
        else:
            console.print(
                "[green]No recommendations - implementations appear to be aligned[/green]"
            )

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Error in comparison script")
        return 1


if __name__ == "__main__":
    sys.exit(main())
