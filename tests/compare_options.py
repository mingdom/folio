#!/usr/bin/env python
"""
Compare Option Calculations Test Script

This script compares option calculations between the old implementation
in src/folio/options.py and the new implementation in src/folib/calculations/.

It creates a set of test cases with different option parameters and compares:
1. Delta values
2. Exposure values

The script supports caching to avoid repeated API calls to Yahoo Finance.
"""

import argparse
import datetime
import hashlib
import logging
import pickle
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import new implementation
# Import old implementation
from src.folib.calculations.exposure import calculate_beta_adjusted_exposure
from src.folib.calculations.exposure import (
    calculate_option_exposure as new_calculate_option_exposure,
)
from src.folib.calculations.options import calculate_option_delta
from src.folio.options import OptionContract, calculate_black_scholes_delta
from src.folio.options import calculate_option_exposure as old_calculate_option_exposure

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("option_comparison.log"),
    ],
)
logger = logging.getLogger("option_comparison")

# Rich console for pretty output
console = Console()

# Cache directory
CACHE_DIR = Path("tests/.cache")
CACHE_DIR.mkdir(exist_ok=True)


def get_cache_key(comparison_type="all"):
    """
    Generate a cache key based on the current date and comparison type.

    Args:
        comparison_type: Type of comparison ("delta", "exposure", or "all")

    Returns:
        Cache key string
    """
    # Use today's date as part of the cache key
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Create a hash of the date and comparison type
    key = f"option_{comparison_type}_{today}"
    return hashlib.md5(key.encode()).hexdigest()


def load_from_cache(cache_key):
    """
    Load results from cache.

    Args:
        cache_key: Cache key

    Returns:
        Cached results or None if not found
    """
    cache_file = CACHE_DIR / f"{cache_key}.pickle"
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "rb") as f:
            results = pickle.load(f)
        logger.info(f"Loaded results from cache: {cache_file}")
        return results
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def save_to_cache(cache_key, results):
    """
    Save results to cache.

    Args:
        cache_key: Cache key
        results: Results to cache
    """
    cache_file = CACHE_DIR / f"{cache_key}.pickle"
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(results, f)
        logger.info(f"Saved results to cache: {cache_file}")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def create_test_cases():
    """
    Create a set of test cases for option calculations.

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
        quantity=test_case["quantity"],
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
    )

    return delta


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
    delta = calculate_new_delta(test_case)

    # Calculate exposure using the new implementation
    exposure = new_calculate_option_exposure(
        quantity=test_case["quantity"],
        underlying_price=test_case["underlying_price"],
        delta=delta,
    )

    # Calculate beta-adjusted exposure
    beta_adjusted = calculate_beta_adjusted_exposure(exposure, test_case["beta"])

    return {
        "delta": delta,
        "delta_exposure": exposure,
        "beta_adjusted_exposure": beta_adjusted,
        "notional_value": abs(
            test_case["quantity"] * 100 * test_case["underlying_price"]
        ),
    }


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
                    "old_delta": old_delta,
                    "new_delta": new_delta,
                    "diff": diff,
                    "pct_diff": pct_diff,
                    "significant": abs(pct_diff) > 1.0,
                }
            )

            logger.info(
                f"Compared delta for {test_case['name']}: Old={old_delta:.4f}, New={new_delta:.4f}, Diff={diff:.4f} ({pct_diff:.2f}%)"
            )

        except Exception as e:
            logger.error(f"Error comparing delta for {test_case['name']}: {e}")
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
                    "diff": None,
                    "pct_diff": None,
                    "significant": True,
                    "error": str(e),
                }
            )

    return results


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
                f"Compared exposure for {test_case['name']}: Old=${old_delta_exposure:.2f}, New=${new_delta_exposure:.2f}, Diff=${diff:.2f} ({pct_diff:.2f}%)"
            )

        except Exception as e:
            logger.error(f"Error comparing exposure for {test_case['name']}: {e}")
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


def print_delta_comparison_table(results):
    """
    Print a table comparing delta calculations.

    Args:
        results: List of comparison results
    """
    table = Table(title="Option Delta Comparison")

    table.add_column("Test Case", style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Qty", justify="right")
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
                f"{result['quantity']}",
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
        old_delta_str = (
            f"{result['old_delta']:.4f}" if result["old_delta"] is not None else "N/A"
        )
        new_delta_str = (
            f"{result['new_delta']:.4f}" if result["new_delta"] is not None else "N/A"
        )
        diff_str = f"{result['diff']:.4f}" if result["diff"] is not None else "N/A"
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
            result["expiry"],
            f"{result['volatility']:.2f}",
            old_delta_str,
            new_delta_str,
            diff_str,
            pct_diff_str,
            style=row_style,
        )

    console.print(table)


def print_exposure_comparison_table(results):
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


def print_summary(results, comparison_type="delta"):
    """
    Print a summary of the comparison results.

    Args:
        results: List of comparison results
        comparison_type: Type of comparison ("delta" or "exposure")
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
        console.print(
            f"1. Review the option {comparison_type} calculation implementations"
        )
        console.print("2. Focus on test cases with significant differences")
        console.print("3. Consider adding more test cases for edge cases")
    else:
        console.print(
            "\n[bold green]The implementations appear to be aligned[/bold green]"
        )


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Compare option calculations")
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
        help="Use cached results if available",
    )
    parser.add_argument(
        "--force-cache",
        "-f",
        action="store_true",
        help="Force cache refresh",
    )
    parser.add_argument(
        "--compare",
        choices=["delta", "exposure", "all"],
        default="all",
        help="What to compare (default: all)",
    )
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print header
    console.print("[bold cyan]Option Calculation Comparison[/bold cyan]")
    console.print(f"Using cache: [cyan]{args.use_cache}[/cyan]")
    console.print(f"Comparing: [cyan]{args.compare}[/cyan]")
    console.print()

    try:
        # Create test cases
        test_cases = create_test_cases()
        logger.info(f"Created {len(test_cases)} test cases")

        # Compare deltas
        if args.compare in ["delta", "all"]:
            # Generate cache key for delta comparison
            delta_cache_key = get_cache_key("delta") if args.use_cache else None

            # Try to load from cache
            delta_results = None
            if delta_cache_key and not args.force_cache:
                delta_results = load_from_cache(delta_cache_key)

            if delta_results is None:
                # Compare deltas
                delta_results = compare_deltas(test_cases)

                # Save to cache if enabled
                if args.use_cache:
                    save_to_cache(delta_cache_key, delta_results)

            # Print delta comparison results
            console.print("\n[bold cyan]Delta Comparison[/bold cyan]")
            print_delta_comparison_table(delta_results)
            print_summary(delta_results, "delta")

        # Compare exposures
        if args.compare in ["exposure", "all"]:
            # Generate cache key for exposure comparison
            exposure_cache_key = get_cache_key("exposure") if args.use_cache else None

            # Try to load from cache
            exposure_results = None
            if exposure_cache_key and not args.force_cache:
                exposure_results = load_from_cache(exposure_cache_key)

            if exposure_results is None:
                # Compare exposures
                exposure_results = compare_exposures(test_cases)

                # Save to cache if enabled
                if args.use_cache:
                    save_to_cache(exposure_cache_key, exposure_results)

            # Print exposure comparison results
            console.print("\n[bold cyan]Exposure Comparison[/bold cyan]")
            print_exposure_comparison_table(exposure_results)
            print_summary(exposure_results, "exposure")

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Error in comparison script")
        return 1


if __name__ == "__main__":
    sys.exit(main())
