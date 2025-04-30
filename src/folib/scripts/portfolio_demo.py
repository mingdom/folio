#!/usr/bin/env python3
# ruff: noqa: T201
"""
Portfolio Demo Script

This script demonstrates how to use the folib library for portfolio analysis:
1. Load a portfolio from a CSV file
2. Parse the portfolio holdings
3. Process the portfolio into groups
4. Calculate portfolio summary metrics
5. Display detailed portfolio information

Usage:
    python -m folib.scripts.portfolio_demo [csv_file]

If no CSV file is specified, the script uses the default portfolio file
at 'private-data/portfolio-private.csv'.
"""

import argparse
import logging
import sys
from pathlib import Path

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.services.portfolio_service import (
    create_portfolio_summary,
    process_portfolio,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("folib.demo")


def format_currency(value: float) -> str:
    """Format a value as currency."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format a value as a percentage."""
    return f"{value:.2%}"


def main():
    """Run the portfolio demo."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Folib Portfolio Demo")
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="private-data/portfolio-private.csv",
        help="Path to the portfolio CSV file",
    )
    args = parser.parse_args()

    # Check if the file exists
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        logger.error(f"File not found: {csv_path}")
        sys.exit(1)

    try:
        # Step 1: Load the portfolio from CSV
        logger.info(f"Loading portfolio from {csv_path}")
        df = load_portfolio_from_csv(csv_path)
        logger.info(f"Loaded {len(df)} rows from CSV")

        # Step 2: Parse portfolio holdings
        logger.info("Parsing portfolio holdings")
        holdings = parse_portfolio_holdings(df)
        logger.info(f"Parsed {len(holdings)} holdings")

        # Step 3: Process the portfolio
        logger.info("Processing portfolio")
        portfolio = process_portfolio(holdings)
        logger.info(f"Processed portfolio with {len(portfolio.groups)} groups")

        # Step 4: Create portfolio summary
        logger.info("Creating portfolio summary")
        summary = create_portfolio_summary(portfolio)

        # Step 5: Display portfolio information
        print("\n" + "=" * 80)
        print("PORTFOLIO SUMMARY".center(80))
        print("=" * 80)

        print(f"\nTotal Value:       {format_currency(summary.total_value)}")
        print(f"Stock Value:       {format_currency(summary.stock_value)}")
        print(f"Option Value:      {format_currency(summary.option_value)}")
        print(f"Cash Value:        {format_currency(summary.cash_value)}")
        print(f"Unknown Value:     {format_currency(summary.unknown_value)}")
        print(f"Pending Activity:  {format_currency(summary.pending_activity_value)}")

        if summary.portfolio_beta is not None:
            print(f"Portfolio Beta:    {summary.portfolio_beta:.2f}")
        else:
            print("Portfolio Beta:    N/A")

        print(f"Market Exposure:   {format_currency(summary.net_market_exposure)}")

        # Calculate percentages
        if summary.total_value > 0:
            stock_pct = summary.stock_value / summary.total_value
            option_pct = summary.option_value / summary.total_value
            cash_pct = summary.cash_value / summary.total_value
            unknown_pct = summary.unknown_value / summary.total_value
            pending_pct = summary.pending_activity_value / summary.total_value

            print("\n" + "=" * 80)
            print("ASSET ALLOCATION".center(80))
            print("=" * 80)
            print(
                f"\nStocks:          {format_percentage(stock_pct)} ({format_currency(summary.stock_value)})"
            )
            print(
                f"Options:         {format_percentage(option_pct)} ({format_currency(summary.option_value)})"
            )
            print(
                f"Cash:            {format_percentage(cash_pct)} ({format_currency(summary.cash_value)})"
            )
            print(
                f"Unknown:         {format_percentage(unknown_pct)} ({format_currency(summary.unknown_value)})"
            )
            print(
                f"Pending Activity: {format_percentage(pending_pct)} ({format_currency(summary.pending_activity_value)})"
            )

        # Display cash positions
        if portfolio.cash_positions:
            print("\n" + "=" * 80)
            print("CASH POSITIONS".center(80))
            print("=" * 80)

            print(
                "\n{:<6} {:<15} {:<15} {:<15}".format(
                    "No.", "Symbol", "Quantity", "Value"
                )
            )
            print("-" * 55)

            for i, position in enumerate(portfolio.cash_positions, 1):
                print(
                    "{:<6} {:<15} {:<15} {:<15}".format(
                        i,
                        position.ticker,
                        f"{position.quantity:,.2f}",
                        format_currency(position.market_value),
                    )
                )

            print(
                f"\nTotal Cash Value: {format_currency(sum(p.market_value for p in portfolio.cash_positions))}"
            )

        # Display unknown positions
        if portfolio.unknown_positions:
            print("\n" + "=" * 80)
            print("UNKNOWN/INVALID POSITIONS".center(80))
            print("=" * 80)

            print(
                "\n{:<6} {:<15} {:<30} {:<15}".format(
                    "No.", "Symbol", "Description", "Value"
                )
            )
            print("-" * 70)

            for i, position in enumerate(portfolio.unknown_positions, 1):
                # Truncate description if too long
                description = (
                    position.description[:27] + "..."
                    if len(position.description) > 30
                    else position.description
                )

                print(
                    f"{i:<6} {position.symbol:<15} {description:<30} {format_currency(position.value):<15}"
                )

            print(
                f"\nTotal Unknown Value: {format_currency(sum(p.value for p in portfolio.unknown_positions))}"
            )

        # Display group information
        print("\n" + "=" * 80)
        print("PORTFOLIO GROUPS".center(80))
        print("=" * 80)

        # Count positions by type
        stock_count = sum(1 for g in portfolio.groups if g.stock_position is not None)
        option_count = sum(len(g.option_positions) for g in portfolio.groups)
        cash_count = len(portfolio.cash_positions)
        unknown_count = len(portfolio.unknown_positions)

        print(f"\nTotal Groups: {len(portfolio.groups)}")
        print(f"Stock Positions: {stock_count}")
        print(f"Option Positions: {option_count}")
        print(f"Cash Positions: {cash_count}")
        print(f"Unknown Positions: {unknown_count}")
        if portfolio.pending_activity_value != 0:
            print(
                f"Pending Activity: {format_currency(portfolio.pending_activity_value)}"
            )

        # Display top holdings by value
        print("\n" + "=" * 80)
        print("TOP STOCK HOLDINGS".center(80))
        print("=" * 80)

        # Get stock positions and sort by value
        stock_positions = []
        for group in portfolio.groups:
            if group.stock_position:
                stock_positions.append(group.stock_position)

        # Sort by absolute value (to handle short positions)
        stock_positions.sort(key=lambda x: abs(x.market_value), reverse=True)

        # Display top 10 stock positions
        print(
            "\n{:<6} {:<8} {:<10} {:<15} {:<15}".format(
                "Rank", "Ticker", "Quantity", "Price", "Value"
            )
        )
        print("-" * 60)

        for i, position in enumerate(stock_positions[:10], 1):
            print(
                "{:<6} {:<8} {:<10} {:<15} {:<15}".format(
                    i,
                    position.ticker,
                    f"{position.quantity:,.0f}",
                    format_currency(position.price),
                    format_currency(position.market_value),
                )
            )

        # Display option positions by type
        print("\n" + "=" * 80)
        print("OPTION POSITIONS BY TYPE".center(80))
        print("=" * 80)

        # Collect all option positions
        call_options = []
        put_options = []

        for group in portfolio.groups:
            for option in group.option_positions:
                if option.option_type == "CALL":
                    call_options.append(option)
                else:
                    put_options.append(option)

        # Display call options summary
        call_value = sum(option.market_value for option in call_options)
        put_value = sum(option.market_value for option in put_options)

        print(
            f"\nCall Options: {len(call_options)} positions, {format_currency(call_value)}"
        )
        print(
            f"Put Options: {len(put_options)} positions, {format_currency(put_value)}"
        )

        print("\nDemo completed successfully")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
