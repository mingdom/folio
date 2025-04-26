#!/usr/bin/env python3
"""
Validation script for P&L calculations using real portfolio data.

This script loads portfolio data from private-data/, processes the options,
and validates P&L calculations for a position group (e.g., SPY options).
"""

import logging
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.folio.pnl import (
    calculate_strategy_pnl,
    determine_price_range,
    summarize_strategy_pnl,
)
from src.folio.portfolio import process_portfolio_data

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_position_details(positions):
    """
    Print details of positions for debugging.

    Args:
        positions: List of positions
    """

    for _i, pos in enumerate(positions):
        position_type = getattr(pos, "position_type", "unknown")
        if position_type == "stock":
            pass
        elif position_type == "option":
            pass
        else:
            pass


def validate_pnl_for_group(group):
    """
    Validate P&L calculations for a position group.

    Args:
        group: Position group

    Returns:
        P&L data
    """
    # Collect all positions in the group
    all_positions = []
    if group.stock_position:
        all_positions.append(group.stock_position)

    all_positions.extend(group.option_positions)

    if not all_positions:
        logger.warning(f"No positions found in group {group.ticker}")
        return None

    # Print position details for debugging
    print_position_details(all_positions)

    # Get current price from stock position or first option position
    current_price = None
    if group.stock_position:
        current_price = group.stock_position.price
    elif group.option_positions:
        # Try to estimate underlying price from notional value and quantity
        first_option = group.option_positions[0]
        if hasattr(first_option, "notional_value") and hasattr(
            first_option, "quantity"
        ):
            # Notional value is 100 * underlying price * abs(quantity)
            abs_quantity = abs(first_option.quantity)
            if abs_quantity > 0:
                current_price = first_option.notional_value / (100 * abs_quantity)

    if current_price is None:
        # Fallback to a default value
        current_price = 100.0
        logger.warning(
            f"Could not determine current price for {group.ticker}, using default: ${current_price:.2f}"
        )
    else:
        logger.info(f"Using current price for {group.ticker}: ${current_price:.2f}")

    # Calculate price range
    price_range = determine_price_range(all_positions, current_price)
    logger.info(f"Price range: ${price_range[0]:.2f} to ${price_range[1]:.2f}")

    # Calculate P&L using current price as entry price (default mode)
    pnl_data_default = calculate_strategy_pnl(
        all_positions, price_range=price_range, num_points=100, use_cost_basis=False
    )

    # Generate summary for default mode
    summary_default = summarize_strategy_pnl(pnl_data_default, current_price)

    # Calculate P&L using cost basis as entry price
    pnl_data_cost_basis = calculate_strategy_pnl(
        all_positions, price_range=price_range, num_points=100, use_cost_basis=True
    )

    # Generate summary for cost basis mode
    summary_cost_basis = summarize_strategy_pnl(pnl_data_cost_basis, current_price)

    # Return both sets of data
    return {
        "default": (pnl_data_default, summary_default),
        "cost_basis": (pnl_data_cost_basis, summary_cost_basis),
    }, current_price


def plot_pnl(
    pnl_data, summary, current_price, ticker, mode="default", output_dir=".tmp"
):
    """
    Plot P&L data and save to file.

    Args:
        pnl_data: P&L data from calculate_strategy_pnl
        summary: Summary data from summarize_strategy_pnl
        current_price: Current price of the underlying
        ticker: Ticker symbol
        mode: Mode used for P&L calculation ("default" or "cost_basis")
        output_dir: Directory to save plot
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create figure
    plt.figure(figsize=(12, 8))

    # Plot combined P&L
    plt.plot(
        pnl_data["price_points"],
        pnl_data["pnl_values"],
        "b-",
        linewidth=2,
        label=f"{ticker} Strategy P&L",
    )

    # Plot individual position P&Ls
    if "individual_pnls" in pnl_data:
        for i, pos_pnl in enumerate(pnl_data["individual_pnls"]):
            pos_desc = pos_pnl.get("position", {}).get("ticker", f"Position {i + 1}")
            plt.plot(
                pos_pnl["price_points"],
                pos_pnl["pnl_values"],
                "--",
                linewidth=1,
                alpha=0.5,
                label=pos_desc,
            )

    # Add reference lines
    plt.axhline(y=0, color="r", linestyle="-", alpha=0.3)
    plt.axvline(
        x=current_price,
        color="g",
        linestyle="--",
        alpha=0.5,
        label=f"Current Price: ${current_price:.2f}",
    )

    # Add breakeven points
    for bp in summary["breakeven_points"]:
        plt.axvline(x=bp, color="orange", linestyle=":", alpha=0.5)
        plt.text(bp, 0, f"BE: ${bp:.2f}", rotation=90, verticalalignment="center")

    # Add max profit/loss points
    max_profit_price = summary["max_profit_price"]
    max_profit = summary["max_profit"]
    plt.plot(max_profit_price, max_profit, "go", markersize=8)
    plt.text(
        max_profit_price,
        max_profit,
        f"Max Profit: ${max_profit:.2f}",
        verticalalignment="bottom",
        horizontalalignment="center",
    )

    max_loss_price = summary["max_loss_price"]
    max_loss = summary["max_loss"]
    plt.plot(max_loss_price, max_loss, "ro", markersize=8)
    plt.text(
        max_loss_price,
        max_loss,
        f"Max Loss: ${max_loss:.2f}",
        verticalalignment="top",
        horizontalalignment="center",
    )

    # Add current P&L
    current_pnl = summary["current_pnl"]
    plt.plot(current_price, current_pnl, "yo", markersize=8)
    plt.text(
        current_price,
        current_pnl,
        f"Current P&L: ${current_pnl:.2f}",
        verticalalignment="bottom",
        horizontalalignment="right",
    )

    # Set labels and title
    mode_label = "Using Cost Basis" if mode == "cost_basis" else "Using Current Price"
    plt.title(f"P&L Analysis for {ticker} Position Group ({mode_label})")
    plt.xlabel(f"{ticker} Price")
    plt.ylabel("P&L ($)")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")

    # Save the plot
    output_file = os.path.join(
        output_dir, f"{ticker.lower()}_pnl_validation_{mode}.png"
    )
    plt.savefig(output_file)
    logger.info(f"P&L plot saved to {output_file}")

    # Close the figure to free memory
    plt.close()


def main():
    """
    Load portfolio data, process options, and validate P&L calculations.
    """
    # Find the most recent portfolio file in private-data/
    private_data_dir = Path("private-data")
    if not private_data_dir.exists():
        logger.error(f"Private data directory not found: {private_data_dir}")
        return

    portfolio_files = list(private_data_dir.glob("pf-*.csv"))
    if not portfolio_files:
        logger.error(f"No portfolio files found in {private_data_dir}")
        return

    # Sort by filename (assuming format pf-YYYYMMDD.csv)
    portfolio_files.sort(reverse=True)
    portfolio_file = portfolio_files[0]
    logger.info(f"Using portfolio file: {portfolio_file}")

    # Load portfolio data
    df = pd.read_csv(portfolio_file)
    logger.info(f"Loaded portfolio data with {len(df)} positions")

    # Process portfolio data
    try:
        # process_portfolio_data returns (groups, summary, cash_positions)
        result = process_portfolio_data(df)
        if isinstance(result, tuple) and len(result) >= 2:
            groups, summary = result[0], result[1]
            logger.info(
                f"Portfolio data processed successfully with {len(groups)} groups"
            )
        else:
            logger.error("Unexpected result format from process_portfolio_data")
            return
    except Exception as e:
        logger.error(f"Error processing portfolio data: {e}")
        return

    # Find position groups to analyze
    tickers_to_analyze = ["META", "AMZN", "GOOGL", "NVDA", "QQQ", "SPY"]

    found_group = False
    for ticker in tickers_to_analyze:
        # Find the group with matching ticker
        matching_groups = [g for g in groups if g.ticker == ticker]

        if not matching_groups:
            logger.warning(f"No {ticker} position group found in portfolio")
            continue

        group = matching_groups[0]
        found_group = True

        logger.info(f"Found {ticker} position group")
        if group.option_positions:
            logger.info(f"  Option positions: {len(group.option_positions)}")
        if group.stock_position:
            logger.info(f"  Stock position: {group.stock_position.quantity} shares")

        # Validate P&L calculations
        try:
            pnl_results, current_price = validate_pnl_for_group(group)
            if pnl_results:
                # Process default mode
                pnl_data, summary = pnl_results["default"]

                # Print P&L data structure validation

                # Check if pnl_data has the expected structure
                for key in pnl_data.keys():
                    if key == "individual_pnls":
                        for _i, _pos_pnl in enumerate(pnl_data[key]):
                            pass

                # Print individual position contributions at max profit price
                max_profit_price = summary["max_profit_price"]
                max_profit_idx = 0
                for i, price in enumerate(pnl_data["price_points"]):
                    if abs(price - max_profit_price) < 0.01:  # Find closest price point
                        max_profit_idx = i
                        break

                total_pnl = 0
                for i, pos_pnl in enumerate(pnl_data["individual_pnls"]):
                    pos_desc = pos_pnl.get("position", {}).get(
                        "ticker", f"Position {i + 1}"
                    )
                    pos_type = pos_pnl.get("position", {}).get(
                        "position_type", "unknown"
                    )
                    pos_pnl.get("position", {}).get("quantity", 0)

                    if pos_type == "option":
                        option_type = pos_pnl.get("position", {}).get("option_type", "")
                        strike = pos_pnl.get("position", {}).get("strike", 0)
                        pos_desc = f"{pos_desc} {option_type} {strike}"

                    pnl_at_max = pos_pnl["pnl_values"][max_profit_idx]
                    total_pnl += pnl_at_max

                # Also check at current price
                # Find the closest price point to current price
                price_points = np.array(pnl_data["price_points"])
                current_idx = np.abs(price_points - current_price).argmin()

                total_current_pnl = 0
                for i, pos_pnl in enumerate(pnl_data["individual_pnls"]):
                    pos_desc = pos_pnl.get("position", {}).get(
                        "ticker", f"Position {i + 1}"
                    )
                    pos_type = pos_pnl.get("position", {}).get(
                        "position_type", "unknown"
                    )
                    pos_pnl.get("position", {}).get("quantity", 0)

                    if pos_type == "option":
                        option_type = pos_pnl.get("position", {}).get("option_type", "")
                        strike = pos_pnl.get("position", {}).get("strike", 0)
                        pos_desc = f"{pos_desc} {option_type} {strike}"

                    pnl_at_current = pos_pnl["pnl_values"][current_idx]
                    total_current_pnl += pnl_at_current

                # Debug the current P&L calculation

                # Get the cost basis summary
                pnl_data_cost_basis, summary_cost_basis = pnl_results["cost_basis"]

                # Print individual position P&Ls at current price
                for i, pos_pnl in enumerate(pnl_data["individual_pnls"]):
                    pos_desc = pos_pnl.get("position", {}).get(
                        "ticker", f"Position {i + 1}"
                    )
                    pos_type = pos_pnl.get("position", {}).get(
                        "position_type", "unknown"
                    )

                    if pos_type == "option":
                        option_type = pos_pnl.get("position", {}).get("option_type", "")
                        strike = pos_pnl.get("position", {}).get("strike", 0)
                        pos_desc = f"{pos_desc} {option_type} {strike}"

                    pnl_at_current = pos_pnl["pnl_values"][current_idx]

                # Print summary

                # Plot P&L for default mode
                plot_pnl(pnl_data, summary, current_price, ticker, mode="default")

                # We already got the cost basis data above

                # Plot P&L for cost basis mode
                plot_pnl(
                    pnl_data_cost_basis,
                    summary_cost_basis,
                    current_price,
                    ticker,
                    mode="cost_basis",
                )

                logger.info(f"P&L validation completed for {ticker} in both modes")
                break  # Process only the first valid group
            else:
                logger.warning(f"No P&L data generated for {ticker}")
        except Exception as e:
            logger.error(f"Error validating P&L for {ticker}: {e}", exc_info=True)

    if not found_group:
        logger.error(
            "No valid position groups found for analysis. Please check the portfolio data."
        )


if __name__ == "__main__":
    main()
