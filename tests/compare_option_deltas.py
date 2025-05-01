#!/usr/bin/env python
"""
Compare Option Delta Calculations Test Script

This script compares the option delta calculations between the old implementation
in src/folio/options.py and the new implementation in src/folib/calculations/options.py.

It creates a set of test cases with different option parameters and compares the
delta values calculated by both implementations.
"""

import argparse
import datetime
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import old implementation
# Import new implementation
from src.folib.calculations.options import calculate_option_delta
from src.folio.options import OptionContract, calculate_black_scholes_delta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("option_delta_comparison.log"),
    ],
)
logger = logging.getLogger("option_delta_comparison")

# Rich console for pretty output
console = Console()


def create_test_cases():
    """
    Create a set of test cases for option delta calculation.

    Returns:
        List of test case dictionaries
    """
    # Current date for expiry calculations
    today = datetime.datetime.now()

    # Create expiry dates at different time horizons
    expiry_short = today + datetime.timedelta(days=30)  # 1 month
    expiry_medium = today + datetime.timedelta(days=90)  # 3 months
    expiry_long = today + datetime.timedelta(days=180)  # 6 months

    test_cases = [
        # At-the-money options
        {
            "name": "ATM Call - Short Term",
            "option_type": "CALL",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_short,
            "volatility": 0.3,
        },
        {
            "name": "ATM Put - Short Term",
            "option_type": "PUT",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_short,
            "volatility": 0.3,
        },

        # In-the-money options
        {
            "name": "ITM Call - Medium Term",
            "option_type": "CALL",
            "strike": 90,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.3,
        },
        {
            "name": "ITM Put - Medium Term",
            "option_type": "PUT",
            "strike": 110,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.3,
        },

        # Out-of-the-money options
        {
            "name": "OTM Call - Long Term",
            "option_type": "CALL",
            "strike": 110,
            "underlying_price": 100,
            "expiry": expiry_long,
            "volatility": 0.3,
        },
        {
            "name": "OTM Put - Long Term",
            "option_type": "PUT",
            "strike": 90,
            "underlying_price": 100,
            "expiry": expiry_long,
            "volatility": 0.3,
        },

        # Deep in-the-money options
        {
            "name": "Deep ITM Call",
            "option_type": "CALL",
            "strike": 80,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.3,
        },
        {
            "name": "Deep ITM Put",
            "option_type": "PUT",
            "strike": 120,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.3,
        },

        # Deep out-of-the-money options
        {
            "name": "Deep OTM Call",
            "option_type": "CALL",
            "strike": 120,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.3,
        },
        {
            "name": "Deep OTM Put",
            "option_type": "PUT",
            "strike": 80,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.3,
        },

        # High volatility options
        {
            "name": "High Vol Call",
            "option_type": "CALL",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.5,
        },
        {
            "name": "High Vol Put",
            "option_type": "PUT",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.5,
        },

        # Low volatility options
        {
            "name": "Low Vol Call",
            "option_type": "CALL",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.1,
        },
        {
            "name": "Low Vol Put",
            "option_type": "PUT",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "volatility": 0.1,
        },

        # Near expiry options
        {
            "name": "Near Expiry Call",
            "option_type": "CALL",
            "strike": 100,
            "underlying_price": 100,
            "expiry": today + datetime.timedelta(days=7),
            "volatility": 0.3,
        },
        {
            "name": "Near Expiry Put",
            "option_type": "PUT",
            "strike": 100,
            "underlying_price": 100,
            "expiry": today + datetime.timedelta(days=7),
            "volatility": 0.3,
        },
    ]

    return test_cases


def calculate_old_delta(test_case):
    """
    Calculate delta using the old implementation.

    Args:
        test_case: Test case dictionary

    Returns:
        Delta value
    """
    # Create an OptionContract object
    option = OptionContract(
        underlying=f"TEST_{test_case['option_type']}",
        expiry=test_case["expiry"],
        strike=test_case["strike"],
        option_type=test_case["option_type"],
        quantity=1,  # Quantity doesn't affect delta calculation
        current_price=1.0,  # Price doesn't affect delta calculation
        description=f"TEST {test_case['option_type']} {test_case['strike']}",
    )

    # Calculate delta using the old implementation
    delta = calculate_black_scholes_delta(
        option_position=option,
        underlying_price=test_case["underlying_price"],
        volatility=test_case["volatility"],
    )

    return delta


def calculate_new_delta(test_case):
    """
    Calculate delta using the new implementation.

    Args:
        test_case: Test case dictionary

    Returns:
        Delta value
    """
    # Calculate delta using the new implementation
    delta = calculate_option_delta(
        option_type=test_case["option_type"],
        strike=test_case["strike"],
        expiry=test_case["expiry"].date(),
        underlying_price=test_case["underlying_price"],
        volatility=test_case["volatility"],
        use_fallback=True,  # Enable fallback to match old implementation
    )

    return delta


def compare_deltas(test_cases):
    """
    Compare delta calculations between old and new implementations.

    Args:
        test_cases: List of test case dictionaries

    Returns:
        List of comparison results
    """
    results = []

    for test_case in test_cases:
        try:
            # Calculate deltas
            old_delta = calculate_old_delta(test_case)
            new_delta = calculate_new_delta(test_case)

            # Calculate difference
            diff = new_delta - old_delta
            pct_diff = (diff / abs(old_delta)) * 100 if old_delta != 0 else float("inf")

            # Add to results
            results.append({
                "name": test_case["name"],
                "option_type": test_case["option_type"],
                "strike": test_case["strike"],
                "underlying_price": test_case["underlying_price"],
                "expiry": test_case["expiry"].strftime("%Y-%m-%d"),
                "volatility": test_case["volatility"],
                "old_delta": old_delta,
                "new_delta": new_delta,
                "diff": diff,
                "pct_diff": pct_diff,
                "significant": abs(pct_diff) > 1.0,
            })

            logger.info(f"Compared {test_case['name']}: Old={old_delta:.4f}, New={new_delta:.4f}, Diff={diff:.4f} ({pct_diff:.2f}%)")

        except Exception as e:
            logger.error(f"Error comparing {test_case['name']}: {e}")
            # Add error result
            results.append({
                "name": test_case["name"],
                "option_type": test_case["option_type"],
                "strike": test_case["strike"],
                "underlying_price": test_case["underlying_price"],
                "expiry": test_case["expiry"].strftime("%Y-%m-%d"),
                "volatility": test_case["volatility"],
                "old_delta": None,
                "new_delta": None,
                "diff": None,
                "pct_diff": None,
                "significant": True,
                "error": str(e),
            })

    return results


def print_comparison_table(results):
    """
    Print a table comparing delta calculations.

    Args:
        results: List of comparison results
    """
    table = Table(title="Option Delta Comparison")

    table.add_column("Test Case", style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Strike", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Expiry", justify="right")
    table.add_column("Vol", justify="right")
    table.add_column("Old Delta", justify="right")
    table.add_column("New Delta", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("% Diff", justify="right")

    for result in results:
        # Skip rows with errors
        if result.get("error"):
            table.add_row(
                result["name"],
                result["option_type"],
                f"{result['strike']:.2f}",
                f"{result['underlying_price']:.2f}",
                result["expiry"],
                f"{result['volatility']:.2f}",
                "ERROR",
                "ERROR",
                "",
                "",
                style="red",
            )
            continue

        # Format values
        old_delta_str = f"{result['old_delta']:.4f}" if result['old_delta'] is not None else "N/A"
        new_delta_str = f"{result['new_delta']:.4f}" if result['new_delta'] is not None else "N/A"
        diff_str = f"{result['diff']:.4f}" if result['diff'] is not None else "N/A"
        pct_diff_str = f"{result['pct_diff']:.2f}%" if result['pct_diff'] is not None else "N/A"

        # Determine row style based on significance
        row_style = "red" if result.get("significant", False) else None

        table.add_row(
            result["name"],
            result["option_type"],
            f"{result['strike']:.2f}",
            f"{result['underlying_price']:.2f}",
            result["expiry"],
            f"{result['volatility']:.2f}",
            old_delta_str,
            new_delta_str,
            diff_str,
            pct_diff_str,
            style=row_style,
        )

    console.print(table)


def print_summary(results):
    """
    Print a summary of the comparison results.

    Args:
        results: List of comparison results
    """
    # Count significant differences
    significant_count = sum(1 for r in results if r.get("significant", False))
    error_count = sum(1 for r in results if r.get("error"))

    # Calculate average absolute percentage difference
    pct_diffs = [abs(r["pct_diff"]) for r in results if "pct_diff" in r and r["pct_diff"] is not None]
    avg_pct_diff = sum(pct_diffs) / len(pct_diffs) if pct_diffs else 0

    console.print("\n[bold cyan]Summary[/bold cyan]")
    console.print(f"Total test cases: {len(results)}")
    console.print(f"Significant differences: {significant_count}")
    console.print(f"Errors: {error_count}")
    console.print(f"Average absolute percentage difference: {avg_pct_diff:.2f}%")

    if significant_count > 0:
        console.print("\n[bold yellow]Recommendations[/bold yellow]")
        console.print("1. Review the option delta calculation implementations")
        console.print("2. Focus on test cases with significant differences")
        console.print("3. Consider adding more test cases for edge cases")
    else:
        console.print("\n[bold green]The implementations appear to be aligned[/bold green]")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Compare option delta calculations")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print header
    console.print("[bold cyan]Option Delta Calculation Comparison[/bold cyan]")
    console.print()

    try:
        # Create test cases
        test_cases = create_test_cases()
        logger.info(f"Created {len(test_cases)} test cases")

        # Compare deltas
        results = compare_deltas(test_cases)

        # Print results
        print_comparison_table(results)
        print_summary(results)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Error in comparison script")
        return 1


if __name__ == "__main__":
    sys.exit(main())
