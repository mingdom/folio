#!/usr/bin/env python3
"""
Portfolio Exposure Debugging Script

This script loads a portfolio CSV file and prints out detailed exposure calculations.
It can be used to debug exposure calculations for any portfolio.

Usage:
    python debug_portfolio.py [path_to_portfolio.csv]

If no path is provided, it will use the default sample portfolio.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

# Add the src directory to the Python path
script_dir = Path(__file__).resolve().parent
src_dir = script_dir.parent
sys.path.append(str(src_dir))

# Import after adding to path
from src.folio.portfolio import process_portfolio_data  # noqa: E402


def print_section_header(_title):
    """Print a section header with formatting."""


def print_exposure_breakdown(_name, breakdown):
    """Print details of an exposure breakdown."""

    # Calculate percentages
    if breakdown.total_exposure > 0:
        (breakdown.stock_exposure / breakdown.total_exposure) * 100
        (breakdown.option_delta_exposure / breakdown.total_exposure) * 100

    # Print components if available
    if hasattr(breakdown, "components") and breakdown.components:
        for _key, _value in breakdown.components.items():
            pass


def print_portfolio_summary(summary):
    """Print a detailed portfolio summary."""
    print_section_header("PORTFOLIO SUMMARY")

    # Calculate options metrics
    long_options = summary.long_exposure.option_delta_exposure
    short_options = summary.short_exposure.option_delta_exposure
    long_options - short_options

    # Calculate stock metrics
    long_stocks = summary.long_exposure.stock_exposure
    short_stocks = summary.short_exposure.stock_exposure

    # Calculate percentages
    total_exposure = (
        summary.long_exposure.total_exposure + summary.short_exposure.total_exposure
    )
    if total_exposure > 0:
        options_exposure = long_options + short_options
        (options_exposure / total_exposure) * 100
        ((long_stocks + short_stocks) / total_exposure) * 100

    # Calculate options exposure (absolute sum of long and short)
    options_exposure = long_options + short_options

    # Print exposure breakdowns
    print_exposure_breakdown("LONG EXPOSURE", summary.long_exposure)
    print_exposure_breakdown("SHORT EXPOSURE", summary.short_exposure)
    print_exposure_breakdown("OPTIONS EXPOSURE", summary.options_exposure)


def print_portfolio_groups(groups):
    """Print details of portfolio groups."""
    print_section_header("PORTFOLIO GROUPS")

    for _i, group in enumerate(groups):
        # Print stock position if available
        if group.stock_position:
            pass

        # Print option positions if available
        if group.option_positions:
            for _j, _option in enumerate(group.option_positions):
                pass


def print_cash_like_positions(positions):
    """Print details of cash-like positions."""
    print_section_header("CASH-LIKE POSITIONS")

    if not positions:
        return

    for _i, _pos in enumerate(positions):
        pass


def main():
    """Main function to load portfolio and print exposure calculations."""
    parser = argparse.ArgumentParser(
        description="Debug portfolio exposure calculations"
    )
    parser.add_argument(
        "portfolio_path",
        nargs="?",
        default=os.path.join(src_dir, "src", "folio", "assets", "sample-portfolio.csv"),
        help="Path to portfolio CSV file",
    )
    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.portfolio_path):
        sys.exit(1)

    try:
        # Load portfolio data
        df = pd.read_csv(args.portfolio_path)

        # Process portfolio data
        groups, summary, _ = process_portfolio_data(df)

        # Print portfolio groups
        print_portfolio_groups(groups)

        # Print cash-like positions
        print_cash_like_positions(summary.cash_like_positions)

        # Print portfolio summary (at the end for easy reference)
        print_portfolio_summary(summary)

    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
