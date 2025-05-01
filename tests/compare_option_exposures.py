#!/usr/bin/env python
"""
Compare Option Exposure Calculations Test Script

This script compares the option exposure calculations between the old implementation
in src/folio/options.py and the new implementation in src/folib/calculations/exposure.py.

It creates a set of test cases with different option parameters and compares the
exposure values calculated by both implementations.
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
from src.folib.calculations.exposure import (
    calculate_option_exposure as new_calculate_option_exposure,
)
from src.folib.calculations.options import (
    calculate_option_delta as new_calculate_option_delta,
)
from src.folio.options import OptionContract
from src.folio.options import calculate_option_exposure as old_calculate_option_exposure

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("option_exposure_comparison.log"),
    ],
)
logger = logging.getLogger("option_exposure_comparison")

# Rich console for pretty output
console = Console()


def create_test_cases():
    """
    Create a set of test cases for option exposure calculation.

    Returns:
        List of test case dictionaries
    """
    # Current date for expiry calculations
    today = datetime.datetime.now()

    # Create expiry dates at different time horizons
    today + datetime.timedelta(days=30)  # 1 month
    expiry_medium = today + datetime.timedelta(days=90)  # 3 months
    today + datetime.timedelta(days=180)  # 6 months

    test_cases = [
        # Long call options
        {
            "name": "Long ATM Call",
            "option_type": "CALL",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": 10,  # 10 contracts
            "volatility": 0.3,
            "beta": 1.0,
        },
        {
            "name": "Long ITM Call",
            "option_type": "CALL",
            "strike": 90,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": 5,  # 5 contracts
            "volatility": 0.3,
            "beta": 1.2,  # Higher beta
        },
        {
            "name": "Long OTM Call",
            "option_type": "CALL",
            "strike": 110,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": 20,  # 20 contracts
            "volatility": 0.3,
            "beta": 0.8,  # Lower beta
        },
        # Short call options
        {
            "name": "Short ATM Call",
            "option_type": "CALL",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": -10,  # -10 contracts (short)
            "volatility": 0.3,
            "beta": 1.0,
        },
        {
            "name": "Short ITM Call",
            "option_type": "CALL",
            "strike": 90,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": -5,  # -5 contracts (short)
            "volatility": 0.3,
            "beta": 1.2,  # Higher beta
        },
        {
            "name": "Short OTM Call",
            "option_type": "CALL",
            "strike": 110,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": -20,  # -20 contracts (short)
            "volatility": 0.3,
            "beta": 0.8,  # Lower beta
        },
        # Long put options
        {
            "name": "Long ATM Put",
            "option_type": "PUT",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": 10,  # 10 contracts
            "volatility": 0.3,
            "beta": 1.0,
        },
        {
            "name": "Long ITM Put",
            "option_type": "PUT",
            "strike": 110,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": 5,  # 5 contracts
            "volatility": 0.3,
            "beta": 1.2,  # Higher beta
        },
        {
            "name": "Long OTM Put",
            "option_type": "PUT",
            "strike": 90,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": 20,  # 20 contracts
            "volatility": 0.3,
            "beta": 0.8,  # Lower beta
        },
        # Short put options
        {
            "name": "Short ATM Put",
            "option_type": "PUT",
            "strike": 100,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": -10,  # -10 contracts (short)
            "volatility": 0.3,
            "beta": 1.0,
        },
        {
            "name": "Short ITM Put",
            "option_type": "PUT",
            "strike": 110,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": -5,  # -5 contracts (short)
            "volatility": 0.3,
            "beta": 1.2,  # Higher beta
        },
        {
            "name": "Short OTM Put",
            "option_type": "PUT",
            "strike": 90,
            "underlying_price": 100,
            "expiry": expiry_medium,
            "quantity": -20,  # -20 contracts (short)
            "volatility": 0.3,
            "beta": 0.8,  # Lower beta
        },
    ]

    return test_cases


def calculate_old_exposure(test_case):
    """
    Calculate exposure using the old implementation.

    Args:
        test_case: Test case dictionary

    Returns:
        Dictionary with exposure metrics
    """
    # Create an OptionContract object
    option = OptionContract(
        underlying=f"TEST_{test_case['option_type']}",
        expiry=test_case["expiry"],
        strike=test_case["strike"],
        option_type=test_case["option_type"],
        quantity=test_case["quantity"],
        current_price=1.0,  # Price doesn't affect exposure calculation
        description=f"TEST {test_case['option_type']} {test_case['strike']}",
    )

    # Set the underlying price on the option
    option.underlying_price = test_case["underlying_price"]

    # Calculate exposure using the old implementation
    exposure = old_calculate_option_exposure(
        option=option,
        underlying_price=test_case["underlying_price"],
        beta=test_case["beta"],
        implied_volatility=test_case["volatility"],
    )

    return exposure


def calculate_new_exposure(test_case):
    """
    Calculate exposure using the new implementation.

    Args:
        test_case: Test case dictionary

    Returns:
        Dictionary with exposure metrics
    """
    # First calculate delta using the new implementation
    delta = new_calculate_option_delta(
        option_type=test_case["option_type"],
        strike=test_case["strike"],
        expiry=test_case["expiry"].date(),
        underlying_price=test_case["underlying_price"],
        volatility=test_case["volatility"],
        use_fallback=True,  # Enable fallback to match old implementation
        quantity=test_case[
            "quantity"
        ],  # Pass quantity to adjust delta based on position direction
    )

    # Calculate exposure using the new implementation
    exposure = new_calculate_option_exposure(
        quantity=test_case["quantity"],
        underlying_price=test_case["underlying_price"],
        delta=delta,
    )

    # Calculate beta-adjusted exposure
    from src.folib.calculations.exposure import calculate_beta_adjusted_exposure

    beta_adjusted = calculate_beta_adjusted_exposure(exposure, test_case["beta"])

    return {
        "delta": delta,
        "delta_exposure": exposure,
        "beta_adjusted_exposure": beta_adjusted,
        "notional_value": abs(
            test_case["quantity"] * 100 * test_case["underlying_price"]
        ),
    }


def compare_exposures(test_cases):
    """
    Compare exposure calculations between old and new implementations.

    Args:
        test_cases: List of test case dictionaries

    Returns:
        List of comparison results
    """
    results = []

    for test_case in test_cases:
        try:
            # Calculate exposures
            old_exposure = calculate_old_exposure(test_case)
            new_exposure = calculate_new_exposure(test_case)

            # Extract delta exposure values
            old_delta_exposure = old_exposure["delta_exposure"]
            new_delta_exposure = new_exposure["delta_exposure"]

            # Calculate difference
            diff = new_delta_exposure - old_delta_exposure
            pct_diff = (
                (diff / abs(old_delta_exposure)) * 100
                if old_delta_exposure != 0
                else float("inf")
            )

            # Add to results
            results.append(
                {
                    "name": test_case["name"],
                    "option_type": test_case["option_type"],
                    "strike": test_case["strike"],
                    "underlying_price": test_case["underlying_price"],
                    "quantity": test_case["quantity"],
                    "expiry": test_case["expiry"].strftime("%Y-%m-%d"),
                    "volatility": test_case["volatility"],
                    "beta": test_case["beta"],
                    "old_delta": old_exposure["delta"],
                    "new_delta": new_exposure["delta"],
                    "old_delta_exposure": old_delta_exposure,
                    "new_delta_exposure": new_delta_exposure,
                    "old_beta_adjusted": old_exposure["beta_adjusted_exposure"],
                    "new_beta_adjusted": new_exposure["beta_adjusted_exposure"],
                    "diff": diff,
                    "pct_diff": pct_diff,
                    "significant": abs(pct_diff) > 1.0,
                }
            )

            logger.info(
                f"Compared {test_case['name']}: Old={old_delta_exposure:.2f}, New={new_delta_exposure:.2f}, Diff={diff:.2f} ({pct_diff:.2f}%)"
            )

        except Exception as e:
            logger.error(f"Error comparing {test_case['name']}: {e}")
            # Add error result
            results.append(
                {
                    "name": test_case["name"],
                    "option_type": test_case["option_type"],
                    "strike": test_case["strike"],
                    "underlying_price": test_case["underlying_price"],
                    "quantity": test_case["quantity"],
                    "expiry": test_case["expiry"].strftime("%Y-%m-%d"),
                    "volatility": test_case["volatility"],
                    "beta": test_case["beta"],
                    "old_delta": None,
                    "new_delta": None,
                    "old_delta_exposure": None,
                    "new_delta_exposure": None,
                    "old_beta_adjusted": None,
                    "new_beta_adjusted": None,
                    "diff": None,
                    "pct_diff": None,
                    "significant": True,
                    "error": str(e),
                }
            )

    return results


def print_comparison_table(results):
    """
    Print a table comparing exposure calculations.

    Args:
        results: List of comparison results
    """
    table = Table(title="Option Exposure Comparison")

    table.add_column("Test Case", style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Qty", justify="right")
    table.add_column("Strike", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Old Delta", justify="right")
    table.add_column("New Delta", justify="right")
    table.add_column("Old Exposure", justify="right")
    table.add_column("New Exposure", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("% Diff", justify="right")

    for result in results:
        # Skip rows with errors
        if result.get("error"):
            table.add_row(
                result["name"],
                result["option_type"],
                f"{result['quantity']}",
                f"{result['strike']:.2f}",
                f"{result['underlying_price']:.2f}",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "",
                "",
                style="red",
            )
            continue

        # Format values
        old_delta_str = (
            f"{result['old_delta']:.4f}" if result["old_delta"] is not None else "N/A"
        )
        new_delta_str = (
            f"{result['new_delta']:.4f}" if result["new_delta"] is not None else "N/A"
        )
        old_exposure_str = (
            f"${result['old_delta_exposure']:,.2f}"
            if result["old_delta_exposure"] is not None
            else "N/A"
        )
        new_exposure_str = (
            f"${result['new_delta_exposure']:,.2f}"
            if result["new_delta_exposure"] is not None
            else "N/A"
        )
        diff_str = f"${result['diff']:,.2f}" if result["diff"] is not None else "N/A"
        pct_diff_str = (
            f"{result['pct_diff']:.2f}%" if result["pct_diff"] is not None else "N/A"
        )

        # Determine row style based on significance
        row_style = "red" if result.get("significant", False) else None

        table.add_row(
            result["name"],
            result["option_type"],
            f"{result['quantity']}",
            f"{result['strike']:.2f}",
            f"{result['underlying_price']:.2f}",
            old_delta_str,
            new_delta_str,
            old_exposure_str,
            new_exposure_str,
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
    pct_diffs = [
        abs(r["pct_diff"])
        for r in results
        if "pct_diff" in r and r["pct_diff"] is not None
    ]
    avg_pct_diff = sum(pct_diffs) / len(pct_diffs) if pct_diffs else 0

    console.print("\n[bold cyan]Summary[/bold cyan]")
    console.print(f"Total test cases: {len(results)}")
    console.print(f"Significant differences: {significant_count}")
    console.print(f"Errors: {error_count}")
    console.print(f"Average absolute percentage difference: {avg_pct_diff:.2f}%")

    if significant_count > 0:
        console.print("\n[bold yellow]Recommendations[/bold yellow]")
        console.print("1. Review the option exposure calculation implementations")
        console.print("2. Focus on test cases with significant differences")
        console.print("3. Consider adding more test cases for edge cases")
    else:
        console.print(
            "\n[bold green]The implementations appear to be aligned[/bold green]"
        )


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Compare option exposure calculations")
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
    console.print("[bold cyan]Option Exposure Calculation Comparison[/bold cyan]")
    console.print()

    try:
        # Create test cases
        test_cases = create_test_cases()
        logger.info(f"Created {len(test_cases)} test cases")

        # Compare exposures
        results = compare_exposures(test_cases)

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
