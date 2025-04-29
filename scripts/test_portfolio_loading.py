#!/usr/bin/env python3
"""
End-to-end test script for portfolio loading.

This script tests the portfolio loading functionality by:
1. Loading a portfolio from a CSV file
2. Processing the portfolio
3. Displaying summary information

Usage:
    python scripts/test_portfolio_loading.py [csv_file]

If no CSV file is specified, the script uses the default portfolio file
at 'private-data/portfolio-private.csv'.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.data.stock import stockdata
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
logger = logging.getLogger("test_portfolio_loading")


def format_currency(value: float) -> str:
    """Format a value as currency."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format a value as a percentage."""
    return f"{value:.2%}"


def main():
    """Run the portfolio loading test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test portfolio loading")
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

    logger.info(f"Loading portfolio from {csv_path}")

    try:
        # Step 1: Load the portfolio from CSV
        df = load_portfolio_from_csv(csv_path)
        logger.info(f"Loaded {len(df)} rows from CSV")

        # Step 2: Parse portfolio holdings
        holdings = parse_portfolio_holdings(df)
        logger.info(f"Parsed {len(holdings)} holdings")

        # Step 3: Process the portfolio
        portfolio = process_portfolio(holdings, stockdata)
        logger.info(f"Processed portfolio with {len(portfolio.groups)} groups")

        # Step 4: Create portfolio summary
        summary = create_portfolio_summary(portfolio)

        # Step 5: Display summary information
        print("\n=== Portfolio Summary ===")
        print(f"Total Value: {format_currency(summary.total_value)}")
        print(f"Stock Value: {format_currency(summary.stock_value)}")
        print(f"Option Value: {format_currency(summary.option_value)}")
        print(f"Cash Value: {format_currency(summary.cash_value)}")
        print(f"Pending Activity: {format_currency(summary.pending_activity_value)}")

        if summary.portfolio_beta is not None:
            print(f"Portfolio Beta: {summary.portfolio_beta:.2f}")
        else:
            print("Portfolio Beta: N/A")

        print(f"Net Market Exposure: {format_currency(summary.net_market_exposure)}")

        # Calculate percentages
        if summary.total_value > 0:
            stock_pct = summary.stock_value / summary.total_value
            option_pct = summary.option_value / summary.total_value
            cash_pct = summary.cash_value / summary.total_value

            print("\n=== Asset Allocation ===")
            print(f"Stocks: {format_percentage(stock_pct)} ({format_currency(summary.stock_value)})")
            print(f"Options: {format_percentage(option_pct)} ({format_currency(summary.option_value)})")
            print(f"Cash: {format_percentage(cash_pct)} ({format_currency(summary.cash_value)})")

        # Display group information
        print("\n=== Portfolio Groups ===")
        for i, group in enumerate(portfolio.groups, 1):
            print(f"\nGroup {i}: {group.ticker}")

            if group.stock_position:
                stock = group.stock_position
                print(f"  Stock: {stock.ticker} - {stock.quantity} shares @ {format_currency(stock.price)} = {format_currency(stock.market_value)}")

            for j, option in enumerate(group.option_positions, 1):
                print(f"  Option {j}: {option.ticker} {option.option_type} {option.strike} {option.expiry} - {option.quantity} contracts @ {format_currency(option.price)} = {format_currency(option.market_value)}")

        # Display cash positions
        if portfolio.cash_positions:
            print("\n=== Cash Positions ===")
            for i, cash in enumerate(portfolio.cash_positions, 1):
                print(f"  {i}. {cash.ticker} - {format_currency(cash.market_value)}")

        print("\nPortfolio loading test completed successfully")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
