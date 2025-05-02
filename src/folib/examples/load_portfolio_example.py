#!/usr/bin/env python3
# ruff: noqa: T201
"""
Portfolio Demo Script (Version 2)

This script demonstrates how to use the folib library for portfolio analysis with the new domain model:
1. Load a portfolio from a CSV file
2. Parse the portfolio holdings
3. Process the portfolio into a flat list of positions
4. Calculate portfolio summary metrics
5. Display detailed portfolio information

Usage:
    python src/folib/examples/load_portfolio_example_v2.py [csv_file]

If no CSV file is specified, the script uses the default portfolio file
at 'private-data/portfolio-private.csv'.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Import YFRateLimitError for explicit handling
from yfinance.exceptions import YFRateLimitError

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.services.portfolio_service import (
    create_portfolio_summary,
    get_portfolio_exposures,
    group_positions_by_ticker,
    process_portfolio,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
# Set specific loggers to DEBUG level
logging.getLogger("folib").setLevel(logging.DEBUG)

# Keep yfinance at INFO level to avoid too much output
logging.getLogger("yfinance").setLevel(logging.ERROR)
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
    parser = argparse.ArgumentParser(description="Folib Portfolio Demo (V2)")
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
        logger.info(f"Processed portfolio with {len(portfolio.positions)} positions")

        # Step 4: Create portfolio summary
        logger.info("Creating portfolio summary")
        summary = create_portfolio_summary(portfolio)

        # Step 5: Calculate portfolio exposures
        logger.info("Calculating portfolio exposures")
        exposures = get_portfolio_exposures(portfolio)

        # Step 6: Display portfolio information
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

        # Display portfolio exposures
        print("\n" + "=" * 80)
        print("PORTFOLIO EXPOSURES".center(80))
        print("=" * 80)
        print(
            f"\nLong Stock Exposure:    {format_currency(exposures['long_stock_exposure'])}"
        )
        print(
            f"Short Stock Exposure:   {format_currency(exposures['short_stock_exposure'])}"
        )
        print(
            f"Long Option Exposure:   {format_currency(exposures['long_option_exposure'])}"
        )
        print(
            f"Short Option Exposure:  {format_currency(exposures['short_option_exposure'])}"
        )
        print(
            f"Net Market Exposure:    {format_currency(exposures['net_market_exposure'])}"
        )
        print(
            f"Beta-Adjusted Exposure: {format_currency(exposures['beta_adjusted_exposure'])}"
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
                # Get description if available (UnknownPosition has it)
                description = ""
                if hasattr(position, "description"):
                    # Truncate description if too long
                    description = (
                        position.description[:27] + "..."
                        if len(position.description) > 30
                        else position.description
                    )

                print(
                    f"{i:<6} {position.ticker:<15} {description:<30} {format_currency(position.market_value):<15}"
                )

            print(
                f"\nTotal Unknown Value: {format_currency(sum(p.market_value for p in portfolio.unknown_positions))}"
            )

        # Display position information
        print("\n" + "=" * 80)
        print("PORTFOLIO POSITIONS".center(80))
        print("=" * 80)

        # Count positions by type
        stock_count = len(portfolio.stock_positions)
        option_count = len(portfolio.option_positions)
        cash_count = len(portfolio.cash_positions)
        unknown_count = len(portfolio.unknown_positions)

        print(f"\nTotal Positions: {len(portfolio.positions)}")
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
        stock_positions = portfolio.stock_positions

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
        call_options = [
            p for p in portfolio.option_positions if p.option_type == "CALL"
        ]
        put_options = [p for p in portfolio.option_positions if p.option_type == "PUT"]

        # Display call options summary
        call_value = sum(option.market_value for option in call_options)
        put_value = sum(option.market_value for option in put_options)

        print(
            f"\nCall Options: {len(call_options)} positions, {format_currency(call_value)}"
        )
        print(
            f"Put Options: {len(put_options)} positions, {format_currency(put_value)}"
        )

        # Demonstrate group_positions_by_ticker functionality
        print("\n" + "=" * 80)
        print("POSITIONS GROUPED BY TICKER (TOP 5)".center(80))
        print("=" * 80)

        # Group all positions by ticker
        grouped_positions = group_positions_by_ticker(portfolio.positions)

        # Get the top 5 tickers by total absolute market value
        ticker_values = {}
        for ticker, positions in grouped_positions.items():
            ticker_values[ticker] = sum(abs(p.market_value) for p in positions)

        top_tickers = sorted(ticker_values.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        # Display positions for each top ticker
        for i, (ticker, _) in enumerate(top_tickers, 1):
            positions = grouped_positions[ticker]

            # Calculate total market value for this ticker
            total_value = sum(p.market_value for p in positions)

            # Get stock and option positions
            stock_positions = [p for p in positions if p.position_type == "stock"]
            option_positions = [p for p in positions if p.position_type == "option"]

            print(f"\n{i}. {ticker} - Total Value: {format_currency(total_value)}")
            print(
                f"   Total Positions: {len(positions)} ({len(stock_positions)} stocks, {len(option_positions)} options)"
            )

            # Display stock positions
            if stock_positions:
                print("\n   Stock Positions:")
                print("   " + "-" * 60)
                print(
                    "   {:<6} {:<10} {:<15} {:<15}".format(
                        "Type", "Quantity", "Price", "Value"
                    )
                )
                print("   " + "-" * 60)

                for position in stock_positions:
                    print(
                        "   {:<6} {:<10} {:<15} {:<15}".format(
                            "Stock",
                            f"{position.quantity:,.0f}",
                            format_currency(position.price),
                            format_currency(position.market_value),
                        )
                    )

            # Display option positions
            if option_positions:
                print("\n   Option Positions:")
                print("   " + "-" * 75)
                print(
                    "   {:<6} {:<10} {:<10} {:<15} {:<15} {:<15}".format(
                        "Type", "Quantity", "Strike", "Expiry", "Price", "Value"
                    )
                )
                print("   " + "-" * 75)

                for position in option_positions:
                    print(
                        "   {:<6} {:<10} {:<10} {:<15} {:<15} {:<15}".format(
                            position.option_type,
                            f"{position.quantity:,.0f}",
                            f"${position.strike:,.2f}",
                            position.expiry.strftime("%Y-%m-%d"),
                            format_currency(position.price),
                            format_currency(position.market_value),
                        )
                    )

            print("\n" + "-" * 80)

        print("\nDemo completed successfully")

    except YFRateLimitError as e:
        logger.error(
            f"Yahoo Finance rate limit exceeded: {e}\n"
            "This error occurs when too many requests are made to Yahoo Finance in a short period.\n"
            "Possible solutions:\n"
            "1. Wait a few minutes and try again\n"
            "2. Use cached data if available\n"
            "3. Implement a retry mechanism with exponential backoff"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
