#!/usr/bin/env python3
# pylint: disable=print-statement,print-used
# ruff: noqa: E402, F401
"""
Portfolio SPY Simulator

This script simulates how a portfolio would respond to changes in SPY (S&P 500 ETF).
It provides detailed analysis of the portfolio's behavior under different SPY price
scenarios, helping investors understand their market exposure and risk profile.

The script uses the Rich library to create beautiful, interactive terminal output
with colorful tables and charts for better data visualization.

Configuration:
    The default parameters can be adjusted by modifying the constants at the top of this file.
    - DEFAULT_SPY_RANGE: The default range of SPY changes to simulate (e.g., 20.0 for ±20%)
    - DEFAULT_STEPS: The default number of steps in the simulation
    - CHART_WIDTH: Width of the chart visualization
    - CHART_HEIGHT: Height of the chart visualization
    - PORTFOLIO_PATH: Path to the portfolio CSV file

Usage:
    # Recommended: Use the make target (activates virtual environment automatically)
    make simulator [range=5] [steps=11] [focus=SPY,QQQ] [detailed=1]

    # Alternative: Activate virtual environment first, then run the script
    source venv/bin/activate
    python scripts/folio-simulator.py [options]

    # Show help
    python scripts/folio-simulator.py --help

Options:
    --focus TICKERS    Comma-separated list of tickers to focus on (e.g., "SPY,QQQ,AAPL")
    --range PERCENT    SPY change range in percent (default: 20.0)
    --steps N          Number of steps in the simulation (default: 13)
    --detailed         Show detailed analysis for all positions

Examples:
    # Run with default settings (±20% SPY range with 13 steps)
    make simulator

    # Run with a narrower range of ±5% SPY with 11 steps (1% increments)
    make simulator range=5 steps=11

    # Focus on a specific ticker with default range
    make simulator focus=SPY

    # Focus on multiple tickers with a custom range
    make simulator focus=SPY,QQQ,AAPL range=15 steps=31

    # Show detailed analysis for all positions
    make simulator detailed=1

Output:
    The script provides several sections of output:

    1. Portfolio Summary - A table showing current, minimum, and maximum portfolio values.

    2. Portfolio Values Table - A detailed table showing portfolio values,
       absolute changes, and percentage changes at each SPY change point.

    3. Portfolio Value Chart - A visual chart showing how the
       portfolio value changes across the SPY range.

    4. Portfolio Value Summary - Key metrics including worst and best case scenarios.

    5. Correlation Analysis - Tables showing positions with negative correlation to SPY
       (lose value when SPY goes up) and inverse correlation (gain value when SPY goes down).

    6. Portfolio Beta Analysis - The portfolio's beta for up and down moves, average
       beta, and a note about non-linear behavior if applicable.

Notes:
    - The script requires a portfolio CSV file at 'private-data/portfolio-private.csv'.
    - The script updates prices for all positions before running the simulation.
    - When focusing on specific tickers, only those positions are included in the simulation.
    - The script calculates implied beta based on the portfolio's response to SPY changes.
"""

import logging
import os
import sys
from pathlib import Path


# Check if running in the correct environment
# pylint: disable=import-outside-toplevel,unused-import
def check_environment():
    """Check if the script is running in the correct environment with all dependencies."""
    try:
        # Try to import pandas to check if dependencies are installed
        import pandas

        return True
    except ImportError:
        # If pandas is not found, provide helpful error message
        # pylint: disable=multiple-statements
        return False


# Exit if not in the correct environment
if not check_environment():
    sys.exit(1)

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# pylint: disable=wrong-import-position
import pandas as pd
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.folio.formatting import format_currency
from src.folio.portfolio import process_portfolio_data
from src.folio.simulator import simulate_portfolio_with_spy_changes

console = Console()

# Configurable constants
DEFAULT_SPY_RANGE = 20.0  # Default range of SPY changes to simulate (±20%)
DEFAULT_STEPS = 13  # Default number of steps (gives 1% increments for default range)
CHART_WIDTH = 50  # Width of the ASCII chart visualization
CHART_HEIGHT = 10  # Height of the ASCII chart visualization
PORTFOLIO_PATH = "private-data/portfolio-private.csv"  # Path to the portfolio CSV file

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("spy_simulator_debug.log", mode="w"),
        logging.StreamHandler(),
    ],
)
# Set specific loggers to INFO to reduce noise
logging.getLogger("matplotlib").setLevel(logging.INFO)
logging.getLogger("PIL").setLevel(logging.INFO)


def debug_simulate_portfolio(
    portfolio_groups,
    cash_like_positions=None,
    pending_activity_value=0.0,
    spy_range=10.0,
    steps=21,
):
    """Run the portfolio simulator with detailed logging for debugging.

    Args:
        portfolio_groups: Dictionary of portfolio position groups
        cash_like_positions: List of cash-like positions
        pending_activity_value: Value of pending activity
        spy_range: Range of SPY changes to simulate (e.g., 10.0 for ±10%)
        steps: Number of steps in the simulation (default: 21)
    """
    logger = logging.getLogger("debug_simulator")
    logger.info("Starting detailed portfolio simulation")
    logger.info(f"Using SPY range of ±{spy_range}% with {steps} steps")

    # Calculate the step size
    step_size = (2 * spy_range) / (steps - 1) if steps > 1 else 0

    # Generate the SPY changes
    spy_changes = [-spy_range + i * step_size for i in range(steps)]

    # Ensure we have a zero point
    if 0.0 not in spy_changes and steps > 2:
        # Find the closest point to zero and replace it with zero
        closest_to_zero = min(spy_changes, key=lambda x: abs(x))
        zero_index = spy_changes.index(closest_to_zero)
        spy_changes[zero_index] = 0.0

    # Convert to percentages
    spy_changes = [change / 100.0 for change in spy_changes]

    logger.info(f"SPY changes: {[f'{change:.1%}' for change in spy_changes]}")

    # Get the original results from the simulator
    results = simulate_portfolio_with_spy_changes(
        portfolio_groups=portfolio_groups,
        spy_changes=spy_changes,
        cash_like_positions=cash_like_positions,
        pending_activity_value=pending_activity_value,
    )

    # Add position-by-position analysis
    logger.info("Analyzing position-by-position behavior")

    # Track original values for each position
    original_values = {}
    zero_index = spy_changes.index(0.0)

    # For each position, track how it changes with SPY
    for group in portfolio_groups:
        ticker = group.ticker
        logger.info(f"Analyzing position: {ticker}")

        # Calculate total market value
        stock_value = group.stock_position.market_value if group.stock_position else 0
        option_value = (
            sum(op.market_value for op in group.option_positions)
            if group.option_positions
            else 0
        )
        total_market_value = stock_value + option_value

        # Skip positions with no market value
        if total_market_value == 0:
            logger.info(f"  Skipping {ticker} - zero market value")
            continue

        # Log position details
        logger.info(f"  Beta: {group.beta:.2f}")
        logger.info(f"  Market Value: {format_currency(total_market_value)}")

        if group.stock_position:
            logger.info(
                f"  Stock: {group.stock_position.quantity} shares @ {group.stock_position.price:.2f}"
            )
            logger.info(
                f"    Stock Value: {format_currency(group.stock_position.market_value)}"
            )

        if group.option_positions:
            logger.info(f"  Options: {len(group.option_positions)}")
            for i, option in enumerate(group.option_positions):
                logger.info(
                    f"    Option {i + 1}: {option.quantity} {option.option_type} @ {option.strike:.2f}, expires {option.expiry}"
                )
                logger.info(
                    f"      Price: {option.price:.4f}, Delta: {option.delta:.4f}"
                )
                logger.info(f"      Value: {format_currency(option.market_value)}")

        # Calculate total market value
        stock_value = group.stock_position.market_value if group.stock_position else 0
        option_value = (
            sum(op.market_value for op in group.option_positions)
            if group.option_positions
            else 0
        )
        total_market_value = stock_value + option_value

        # Calculate expected behavior based on beta
        expected_change_at_10pct = group.beta * 0.1 * total_market_value
        logger.info(
            f"  Expected change at +10% SPY: {format_currency(expected_change_at_10pct)}"
        )

        # Store original value
        original_values[ticker] = total_market_value

    # Analyze the results
    logger.info("\nAnalyzing simulation results")

    # Find positions with unexpected behavior

    # Find the indices for min, max, and zero values
    zero_index = next(
        (i for i, change in enumerate(spy_changes) if abs(change) < 0.001), 0
    )
    min_index = 0  # First element (most negative)
    max_index = len(spy_changes) - 1  # Last element (most positive)

    # Calculate the total portfolio change
    total_min = results["portfolio_values"][min_index]
    total_zero = results["portfolio_values"][zero_index]
    total_max = results["portfolio_values"][max_index]

    min_change = spy_changes[min_index]
    max_change = spy_changes[max_index]

    logger.info(
        f"Portfolio value at {min_change:.1%} SPY: {format_currency(total_min)}"
    )
    logger.info(f"Portfolio value at 0% SPY: {format_currency(total_zero)}")
    logger.info(
        f"Portfolio value at {max_change:.1%} SPY: {format_currency(total_max)}"
    )

    down_change = total_min - total_zero
    up_change = total_max - total_zero

    logger.info(
        f"Change on {min_change:.1%} SPY: {format_currency(down_change)} ({down_change / total_zero * 100:.2f}%)"
    )
    logger.info(
        f"Change on {max_change:.1%} SPY: {format_currency(up_change)} ({up_change / total_zero * 100:.2f}%)"
    )

    # Calculate implied beta
    down_beta = -down_change / (total_zero * 0.1)
    up_beta = up_change / (total_zero * 0.1)

    logger.info(f"Implied beta on down moves: {down_beta:.2f}")
    logger.info(f"Implied beta on up moves: {up_beta:.2f}")

    # Add position-level analysis
    if "position_values" in results:
        logger.info("\nAnalyzing position-level contributions:")

        # Calculate position-level changes
        position_changes = {}
        for ticker, values in results["position_values"].items():
            if len(values) > zero_index:
                base_value = values[zero_index]
                if base_value == 0:
                    continue

                # Calculate changes at min and max SPY values
                min_spy_value = values[min_index] if min_index < len(values) else 0
                max_spy_value = values[max_index] if max_index < len(values) else 0

                down_change = min_spy_value - base_value
                up_change = max_spy_value - base_value

                # Calculate percentage changes
                down_pct = (down_change / base_value) * 100 if base_value != 0 else 0
                up_pct = (up_change / base_value) * 100 if base_value != 0 else 0

                # Store the changes
                position_changes[ticker] = {
                    "base_value": base_value,
                    "min_spy_value": min_spy_value,
                    "max_spy_value": max_spy_value,
                    "down_change": down_change,
                    "up_change": up_change,
                    "down_pct": down_pct,
                    "up_pct": up_pct,
                }

                logger.info(f"  {ticker}:")
                logger.info(f"    Base Value: {format_currency(base_value)}")
                logger.info(
                    f"    Change at -10% SPY: {format_currency(down_change)} ({down_pct:.2f}%)"
                )
                logger.info(
                    f"    Change at +10% SPY: {format_currency(up_change)} ({up_pct:.2f}%)"
                )

        # Find positions with largest contributions
        sorted_down = sorted(
            position_changes.items(), key=lambda x: x[1]["down_change"]
        )
        sorted_up = sorted(
            position_changes.items(), key=lambda x: x[1]["up_change"], reverse=True
        )

        logger.info("\nLargest contributors to downside moves:")
        for ticker, data in sorted_down[:5]:
            logger.info(
                f"  {ticker}: {format_currency(data['down_change'])} ({data['down_pct']:.2f}%)"
            )

        logger.info("\nLargest contributors to upside moves:")
        for ticker, data in sorted_up[:5]:
            logger.info(
                f"  {ticker}: {format_currency(data['up_change'])} ({data['up_pct']:.2f}%)"
            )

    # Add the analysis to the results
    results["analysis"] = {
        "down_beta": down_beta,
        "up_beta": up_beta,
        "original_values": original_values,
        "position_changes": position_changes if "position_values" in results else {},
    }

    # Add the portfolio groups to the results for position type identification
    results["portfolio_groups"] = portfolio_groups

    return results


def main():
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="Portfolio SPY Simulator - Analyze portfolio behavior under different SPY price scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (±20% SPY range with 13 steps)
  python scripts/folio-simulator.py

  # Run with a narrower range of ±5% SPY with 11 steps (1% increments)
  python scripts/folio-simulator.py --range 5 --steps 11

  # Focus on a specific ticker with default range
  python scripts/folio-simulator.py --focus SPY

  # Focus on multiple tickers with a custom range
  python scripts/folio-simulator.py --focus SPY,QQQ,AAPL --range 15 --steps 31

  # Show detailed analysis for all positions
  python scripts/folio-simulator.py --detailed
        """,
    )

    # Add a group for simulation parameters
    sim_group = parser.add_argument_group("Simulation Parameters")
    sim_group.add_argument(
        "--range",
        type=float,
        default=DEFAULT_SPY_RANGE,
        help=f"SPY change range in percent (default: ±{DEFAULT_SPY_RANGE}%%)",
        metavar="PERCENT",
    )
    sim_group.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_STEPS,
        help=f"Number of steps in the simulation (default: {DEFAULT_STEPS}, which gives {DEFAULT_SPY_RANGE / (DEFAULT_STEPS - 1) * 2:.1f}%% increments for default range)",
        metavar="N",
    )

    # Add a group for filtering and display options
    filter_group = parser.add_argument_group("Filtering and Display Options")
    filter_group.add_argument(
        "--focus",
        type=str,
        help="Comma-separated list of tickers to focus on (e.g., 'SPY,QQQ,AAPL')",
        metavar="TICKERS",
    )
    filter_group.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed analysis for all positions",
    )

    args = parser.parse_args()

    # Path to the portfolio CSV file
    csv_path = Path(os.getcwd()) / PORTFOLIO_PATH

    if not csv_path.exists():
        sys.exit(1)

    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)

        # Process the portfolio data with price updates
        groups, summary, _ = process_portfolio_data(df, update_prices=True)

        # Filter portfolio if focus is specified
        focus_tickers = []
        if args.focus:
            focus_tickers = [ticker.strip().upper() for ticker in args.focus.split(",")]

            # Create a filtered portfolio with only the specified positions
            filtered_groups = {}

            # Convert list to dictionary if needed
            if isinstance(groups, list):
                groups_dict = {group.ticker: group for group in groups}
            else:
                groups_dict = groups

            for ticker, group in groups_dict.items():
                if ticker in focus_tickers:
                    filtered_groups[ticker] = group

            if not filtered_groups:
                pass
            # Use the filtered groups
            elif isinstance(groups, list):
                groups = list(filtered_groups.values())
            else:
                groups = filtered_groups

        # Run the simulation with detailed debugging
        results = debug_simulate_portfolio(
            portfolio_groups=groups,
            cash_like_positions=summary.cash_like_positions,
            pending_activity_value=getattr(summary, "pending_activity_value", 0.0),
            spy_range=args.range,
            steps=args.steps,
        )

        # Print the results
        # Get the current value (at 0% SPY change)
        current_value = results["current_value"]

        # Get min and max values
        min_value = min(results["portfolio_values"])
        max_value = max(results["portfolio_values"])
        min_index = results["portfolio_values"].index(min_value)
        max_index = results["portfolio_values"].index(max_value)
        min_spy_change = (
            results["spy_changes"][min_index] * 100
        )  # Convert to percentage
        max_spy_change = (
            results["spy_changes"][max_index] * 100
        )  # Convert to percentage

        # Create a table of all SPY changes and portfolio values
        if True:
            console.print("\n[bold cyan]Portfolio Simulation Results[/bold cyan]")

            # Create a summary table
            summary_table = Table(title="Portfolio Summary", box=box.ROUNDED)
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")
            summary_table.add_column("SPY Change", style="yellow")

            summary_table.add_row("Current Value", f"${current_value:,.2f}", "0.0%")
            summary_table.add_row(
                "Minimum Value", f"${min_value:,.2f}", f"{min_spy_change:.1f}%"
            )
            summary_table.add_row(
                "Maximum Value", f"${max_value:,.2f}", f"{max_spy_change:.1f}%"
            )

            console.print(summary_table)

            # Create a detailed table with all values
            value_table = Table(
                title="Portfolio Values at Different SPY Changes", box=box.ROUNDED
            )
            value_table.add_column("SPY Change", style="yellow")
            value_table.add_column("Portfolio Value", style="green")
            value_table.add_column("Change", style="cyan")
            value_table.add_column("% Change", style="magenta")

            for i, spy_change in enumerate(results["spy_changes"]):
                portfolio_value = results["portfolio_values"][i]
                value_change = portfolio_value - current_value
                pct_change = (
                    (value_change / current_value) * 100 if current_value != 0 else 0
                )

                # Format the change with color based on positive/negative
                change_str = f"${value_change:+,.2f}"
                pct_change_str = f"{pct_change:+.2f}%"

                value_table.add_row(
                    f"{spy_change * 100:.1f}%",
                    f"${portfolio_value:,.2f}",
                    change_str,
                    pct_change_str,
                )

            console.print(value_table)

        # Create a visualization of the portfolio value curve

        # Find min and max values for scaling
        min_value = min(results["portfolio_values"])
        max_value = max(results["portfolio_values"])
        value_range = max_value - min_value

        if True:
            # Create a panel for the chart
            chart_title = f"Portfolio Value vs SPY Change (Min: ${min_value:,.2f}, Max: ${max_value:,.2f})"

            # Create the visualization using Unicode block characters for a smoother chart
            chart = [" " * CHART_WIDTH for _ in range(CHART_HEIGHT)]

            # Map SPY changes to x positions
            x_positions = []
            for spy_change in results["spy_changes"]:
                # Map from min to max SPY change to 0 to CHART_WIDTH-1
                min_spy = results["spy_changes"][0]
                max_spy = results["spy_changes"][-1]
                spy_range = max_spy - min_spy
                x_pos = int((spy_change - min_spy) / spy_range * (CHART_WIDTH - 1))
                x_positions.append(max(0, min(CHART_WIDTH - 1, x_pos)))

            # Map portfolio values to y positions
            y_positions = []
            for value in results["portfolio_values"]:
                if value_range > 0:
                    # Map from min_value to max_value to 0 to CHART_HEIGHT-1
                    y_pos = int((value - min_value) / value_range * (CHART_HEIGHT - 1))
                    y_positions.append(max(0, min(CHART_HEIGHT - 1, y_pos)))
                else:
                    y_positions.append(CHART_HEIGHT // 2)

            # Plot the points with different characters based on position
            for x, y in zip(x_positions, y_positions, strict=False):
                row = chart[y]
                # Use different characters for different parts of the curve
                if y == 0:  # Top of chart
                    char = "▲"
                elif y == CHART_HEIGHT - 1:  # Bottom of chart
                    char = "▼"
                else:
                    char = "●"
                chart[y] = row[:x] + char + row[x + 1 :]

            # Create the chart string
            chart_str = "\n".join(
                ["|" + row + "|" for row in chart[::-1]]
            )  # Reverse to show bottom to top

            # Add a border
            border = "+" + "-" * CHART_WIDTH + "+"
            chart_str = border + "\n" + chart_str + "\n" + border

            # Add axis labels
            min_spy_label = f"{results['spy_changes'][0] * 100:.1f}%"
            max_spy_label = f"{results['spy_changes'][-1] * 100:.1f}%"
            zero_spy_index = next(
                (
                    i
                    for i, change in enumerate(results["spy_changes"])
                    if abs(change) < 0.001
                ),
                None,
            )
            zero_spy_label = "0.0%" if zero_spy_index is not None else ""

            axis_labels = f"{min_spy_label}{' ' * (CHART_WIDTH - len(min_spy_label) - len(max_spy_label))}{max_spy_label}"
            if zero_spy_index is not None:
                zero_pos = int(
                    zero_spy_index / (len(results["spy_changes"]) - 1) * CHART_WIDTH
                )
                axis_labels = (
                    axis_labels[:zero_pos]
                    + zero_spy_label
                    + axis_labels[zero_pos + len(zero_spy_label) :]
                )

            chart_str += "\n" + axis_labels

            # Create a panel with the chart
            chart_panel = Panel(chart_str, title=chart_title, border_style="cyan")
            console.print(chart_panel)

        # Add value scale
        value_range / 4 if value_range > 0 else 0

        # Print summary analysis
        min_value = min(results["portfolio_values"])
        max_value = max(results["portfolio_values"])
        min_change = min_value - current_value
        max_change = max_value - current_value
        min_pct_change = (min_change / current_value) * 100 if current_value != 0 else 0
        max_pct_change = (max_change / current_value) * 100 if current_value != 0 else 0

        min_index = results["portfolio_values"].index(min_value)
        max_index = results["portfolio_values"].index(max_value)
        min_spy_change = (
            results["spy_changes"][min_index] * 100
        )  # Convert to percentage
        max_spy_change = (
            results["spy_changes"][max_index] * 100
        )  # Convert to percentage

        # Print summary analysis
        if True:
            summary_table = Table(title="Portfolio Value Summary", box=box.ROUNDED)
            summary_table.add_column("Scenario", style="cyan")
            summary_table.add_column("Value", style="green")
            summary_table.add_column("Change", style="magenta")
            summary_table.add_column("SPY Change", style="yellow")

            summary_table.add_row(
                "Worst Case",
                f"${min_value:,.2f}",
                f"{min_pct_change:+.2f}%",
                f"{min_spy_change:.1f}%",
            )
            summary_table.add_row(
                "Best Case",
                f"${max_value:,.2f}",
                f"{max_pct_change:+.2f}%",
                f"{max_spy_change:.1f}%",
            )

            console.print(summary_table)

        # Print position-level analysis
        if "position_values" in results:
            # Find the indices for min, max, and zero values
            try:
                zero_index = next(
                    (
                        i
                        for i, change in enumerate(results["spy_changes"])
                        if abs(change) < 0.001
                    ),
                    0,
                )
                min_index = 0  # First element (most negative)
                max_index = (
                    len(results["spy_changes"]) - 1
                )  # Last element (most positive)

                # Calculate position-level changes
                position_changes = {}
                for ticker, values in results["position_values"].items():
                    if len(values) > zero_index:
                        base_value = values[zero_index]
                        if base_value == 0:
                            continue

                        # Calculate changes at min and max SPY values
                        min_spy_value = (
                            values[min_index] if min_index < len(values) else 0
                        )
                        max_spy_value = (
                            values[max_index] if max_index < len(values) else 0
                        )

                        down_change = min_spy_value - base_value
                        up_change = max_spy_value - base_value

                        # Calculate percentage changes
                        down_pct = (
                            (down_change / base_value) * 100 if base_value != 0 else 0
                        )
                        up_pct = (
                            (up_change / base_value) * 100 if base_value != 0 else 0
                        )

                        # Store the changes
                        position_changes[ticker] = {
                            "base_value": base_value,
                            "min_spy_value": min_spy_value,
                            "max_spy_value": max_spy_value,
                            "down_change": down_change,
                            "up_change": up_change,
                            "down_pct": down_pct,
                            "up_pct": up_pct,
                        }

                # Get position details for comparison
                position_details = results.get("position_details", {})

                # Find positions with largest contributions
                sorted_down = sorted(
                    position_changes.items(), key=lambda x: x[1]["down_change"]
                )
                sorted_up = sorted(
                    position_changes.items(),
                    key=lambda x: x[1]["up_change"],
                    reverse=True,
                )

                # Print positions with largest downside contributions
                for ticker, data in sorted_down[:5]:
                    # Calculate expected change based on beta
                    beta = position_details.get(ticker, {}).get("beta", 0)
                    base_value = data["base_value"]
                    expected_change = (
                        beta * min_spy_change * base_value
                    )  # Expected change at min SPY
                    actual_change = data["down_change"]
                    difference = actual_change - expected_change
                    (
                        (difference / abs(expected_change)) * 100
                        if expected_change != 0
                        else 0
                    )

                # Print positions with largest upside contributions
                for ticker, data in sorted_up[:5]:
                    # Calculate expected change based on beta
                    beta = position_details.get(ticker, {}).get("beta", 0)
                    base_value = data["base_value"]
                    expected_change = (
                        beta * max_spy_change * base_value
                    )  # Expected change at max SPY
                    actual_change = data["up_change"]
                    difference = actual_change - expected_change
                    (
                        (difference / abs(expected_change)) * 100
                        if expected_change != 0
                        else 0
                    )

                # Find positions that lose value when SPY goes up (negative correlation)
                negative_correlation = []
                for ticker, data in position_changes.items():
                    # If position value decreases when SPY increases
                    if data["up_change"] < 0:
                        # For any ticker, provide detailed position analysis when requested
                        if args.detailed:
                            pass
                        negative_correlation.append((ticker, data))

                if negative_correlation:
                    # Sort by the magnitude of negative impact
                    negative_correlation.sort(key=lambda x: x[1]["up_change"])

                    if True:
                        # Create a table for positions that lose value when SPY goes up
                        neg_corr_table = Table(
                            title="Positions that LOSE value when SPY goes UP (negative correlation)",
                            box=box.ROUNDED,
                        )
                        neg_corr_table.add_column("Ticker", style="cyan")
                        neg_corr_table.add_column("Change", style="red")
                        neg_corr_table.add_column("% Change", style="red")
                        neg_corr_table.add_column("Beta", style="yellow")

                        for ticker, data in negative_correlation:
                            beta = position_details.get(ticker, {}).get("beta", 0)
                            neg_corr_table.add_row(
                                ticker,
                                f"${data['up_change']:+,.2f}",
                                f"{data['up_pct']:+.2f}%",
                                f"{beta:+.2f}",
                            )

                        console.print(neg_corr_table)

                # Find positions that gain value when SPY goes down (inverse correlation)
                inverse_correlation = []
                for ticker, data in position_changes.items():
                    # If position value increases when SPY decreases
                    if data["down_change"] > 0:
                        inverse_correlation.append((ticker, data))

                if inverse_correlation:
                    # Sort by the magnitude of positive impact
                    inverse_correlation.sort(
                        key=lambda x: x[1]["down_change"], reverse=True
                    )

                    if True:
                        # Create a table for positions that gain value when SPY goes down
                        inv_corr_table = Table(
                            title="Positions that GAIN value when SPY goes DOWN (inverse correlation)",
                            box=box.ROUNDED,
                        )
                        inv_corr_table.add_column("Ticker", style="cyan")
                        inv_corr_table.add_column("Change", style="green")
                        inv_corr_table.add_column("% Change", style="green")
                        inv_corr_table.add_column("Beta", style="yellow")

                        for ticker, data in inverse_correlation:
                            beta = position_details.get(ticker, {}).get("beta", 0)
                            inv_corr_table.add_row(
                                ticker,
                                f"${data['down_change']:+,.2f}",
                                f"{data['down_pct']:+.2f}%",
                                f"{beta:+.2f}",
                            )

                        console.print(inv_corr_table)

            except (StopIteration, IndexError):
                pass

        # Calculate the portfolio's beta based on the simulation results
        try:
            # Get the min and max values
            min_index = 0  # First element (most negative)
            max_index = len(results["spy_changes"]) - 1  # Last element (most positive)

            min_value = results["portfolio_values"][min_index]
            max_value = results["portfolio_values"][max_index]

            min_spy_change = results["spy_changes"][min_index]
            max_spy_change = results["spy_changes"][max_index]

            min_pct_change = (min_value / current_value - 1) * 100
            max_pct_change = (max_value / current_value - 1) * 100

            # Calculate beta for up and down moves
            beta_up = max_pct_change / (
                max_spy_change * 100
            )  # How much portfolio changes per 1% SPY up move
            beta_down = min_pct_change / (
                min_spy_change * 100
            )  # How much portfolio changes per 1% SPY down move
            (beta_up + beta_down) / 2

            # Print beta analysis
            if True:
                beta_table = Table(title="Portfolio Beta Analysis", box=box.ROUNDED)
                beta_table.add_column("Direction", style="cyan")
                beta_table.add_column("Beta", style="yellow")

                beta_table.add_row("Up Moves", f"{beta_up:.2f}")
                beta_table.add_row("Down Moves", f"{beta_down:.2f}")
                beta_table.add_row("Average", f"{(beta_up + beta_down) / 2:.2f}")

                console.print(beta_table)

                if abs(beta_up - beta_down) > 0.5:
                    console.print(
                        f"[bold yellow]Note:[/bold yellow] Beta difference of {abs(beta_up - beta_down):.2f} indicates non-linear behavior"
                    )
        except (StopIteration, IndexError):
            pass

    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
