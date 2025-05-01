#!/usr/bin/env python
"""
Compare Option Categorization Test Script

This script compares how options are categorized between the old and new implementations.
It breaks down option exposures by:
- Option type (calls vs puts)
- Position direction (long vs short)
- Delta sign (positive vs negative)
- Various combinations of these factors

This helps identify exactly where the categorization differences occur.
"""

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import old implementation
# Import new implementation

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("option_categorization_comparison.log"),
    ],
)
logger = logging.getLogger("option_categorization_comparison")

# Rich console for pretty output
console = Console()


def load_portfolio_data(file_path: str):
    """
    Load portfolio data from a CSV file.

    Args:
        file_path: Path to the portfolio CSV file

    Returns:
        Tuple of (old_portfolio, new_portfolio)
    """
    logger.info(f"Loading portfolio data from: {file_path}")

    # Load old implementation
    import pandas as pd

    from src.folio.portfolio import process_portfolio_data

    df = pd.read_csv(file_path)
    old_groups, old_summary, old_positions = process_portfolio_data(
        df, update_prices=False
    )

    # Load new implementation
    from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
    from src.folib.services.portfolio_service import process_portfolio

    df = load_portfolio_from_csv(file_path)
    holdings = parse_portfolio_holdings(df)
    new_portfolio = process_portfolio(holdings)

    return old_groups, old_summary, old_positions, new_portfolio


def categorize_old_options(old_groups):
    """
    Categorize options in the old implementation.

    Args:
        old_groups: Portfolio groups from old implementation

    Returns:
        Dictionary with categorized option exposures
    """
    logger.info("Categorizing options in old implementation")

    # Initialize categories
    categories = {
        "calls": {"long": 0.0, "short": 0.0},
        "puts": {"long": 0.0, "short": 0.0},
        "positive_quantity": {"positive_delta": 0.0, "negative_delta": 0.0},
        "negative_quantity": {"positive_delta": 0.0, "negative_delta": 0.0},
        "positive_delta": {"calls": 0.0, "puts": 0.0},
        "negative_delta": {"calls": 0.0, "puts": 0.0},
        "total": {"long": 0.0, "short": 0.0},
    }

    # Process each group
    for group in old_groups:
        for option in group.option_positions:
            # Extract key attributes
            option_type = option.option_type
            quantity = option.quantity
            delta = option.delta
            delta_exposure = option.delta_exposure

            # Categorize by option type
            if option_type == "CALL":
                if delta_exposure >= 0:  # Long exposure
                    categories["calls"]["long"] += abs(delta_exposure)
                else:  # Short exposure
                    categories["calls"]["short"] += abs(delta_exposure)
            elif delta_exposure >= 0:  # Long exposure
                categories["puts"]["long"] += abs(delta_exposure)
            else:  # Short exposure
                categories["puts"]["short"] += abs(delta_exposure)

            # Categorize by position direction
            if quantity >= 0:  # Long position
                if delta >= 0:  # Positive delta
                    categories["positive_quantity"]["positive_delta"] += abs(
                        delta_exposure
                    )
                else:  # Negative delta
                    categories["positive_quantity"]["negative_delta"] += abs(
                        delta_exposure
                    )
            elif delta >= 0:  # Positive delta
                categories["negative_quantity"]["positive_delta"] += abs(delta_exposure)
            else:  # Negative delta
                categories["negative_quantity"]["negative_delta"] += abs(delta_exposure)

            # Categorize by delta sign
            if delta >= 0:  # Positive delta
                if option_type == "CALL":
                    categories["positive_delta"]["calls"] += abs(delta_exposure)
                else:  # PUT
                    categories["positive_delta"]["puts"] += abs(delta_exposure)
            elif option_type == "CALL":
                categories["negative_delta"]["calls"] += abs(delta_exposure)
            else:  # PUT
                categories["negative_delta"]["puts"] += abs(delta_exposure)

            # Categorize by total exposure
            if delta_exposure >= 0:  # Long exposure
                categories["total"]["long"] += abs(delta_exposure)
            else:  # Short exposure
                categories["total"]["short"] += abs(delta_exposure)

    return categories


def categorize_new_options(new_portfolio):
    """
    Categorize options in the new implementation.

    Args:
        new_portfolio: Portfolio from new implementation

    Returns:
        Dictionary with categorized option exposures
    """
    logger.info("Categorizing options in new implementation")

    # Initialize categories
    categories = {
        "calls": {"long": 0.0, "short": 0.0},
        "puts": {"long": 0.0, "short": 0.0},
        "positive_quantity": {"positive_delta": 0.0, "negative_delta": 0.0},
        "negative_quantity": {"positive_delta": 0.0, "negative_delta": 0.0},
        "positive_delta": {"calls": 0.0, "puts": 0.0},
        "negative_delta": {"calls": 0.0, "puts": 0.0},
        "total": {"long": 0.0, "short": 0.0},
    }

    # Import required functions
    from src.folib.calculations.exposure import calculate_option_exposure
    from src.folib.calculations.options import calculate_option_delta

    # Process each option position
    for position in new_portfolio.option_positions:
        # Get underlying price
        try:
            underlying_price = get_price(position.ticker)
        except Exception:
            # Fallback to using strike as proxy for underlying price
            underlying_price = position.strike

        # Calculate delta
        delta = calculate_option_delta(
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=underlying_price,
            use_fallback=True,
        )

        # Calculate exposure
        exposure = calculate_option_exposure(
            quantity=position.quantity,
            underlying_price=underlying_price,
            delta=delta,
        )

        # Extract key attributes
        option_type = position.option_type
        quantity = position.quantity

        # Categorize by option type
        if option_type == "CALL":
            if exposure >= 0:  # Long exposure
                categories["calls"]["long"] += abs(exposure)
            else:  # Short exposure
                categories["calls"]["short"] += abs(exposure)
        elif exposure >= 0:  # Long exposure
            categories["puts"]["long"] += abs(exposure)
        else:  # Short exposure
            categories["puts"]["short"] += abs(exposure)

        # Categorize by position direction
        if quantity >= 0:  # Long position
            if delta >= 0:  # Positive delta
                categories["positive_quantity"]["positive_delta"] += abs(exposure)
            else:  # Negative delta
                categories["positive_quantity"]["negative_delta"] += abs(exposure)
        elif delta >= 0:  # Positive delta
            categories["negative_quantity"]["positive_delta"] += abs(exposure)
        else:  # Negative delta
            categories["negative_quantity"]["negative_delta"] += abs(exposure)

        # Categorize by delta sign
        if delta >= 0:  # Positive delta
            if option_type == "CALL":
                categories["positive_delta"]["calls"] += abs(exposure)
            else:  # PUT
                categories["positive_delta"]["puts"] += abs(exposure)
        elif option_type == "CALL":
            categories["negative_delta"]["calls"] += abs(exposure)
        else:  # PUT
            categories["negative_delta"]["puts"] += abs(exposure)

        # Categorize by total exposure
        if exposure >= 0:  # Long exposure
            categories["total"]["long"] += abs(exposure)
        else:  # Short exposure
            categories["total"]["short"] += abs(exposure)

    return categories


def compare_categorizations(old_categories, new_categories):
    """
    Compare option categorizations between old and new implementations.

    Args:
        old_categories: Categories from old implementation
        new_categories: Categories from new implementation

    Returns:
        Dictionary with comparison results
    """
    logger.info("Comparing option categorizations")

    # Initialize comparison results
    comparison = {}

    # Compare each category
    for category, subcategories in old_categories.items():
        comparison[category] = {}
        for subcategory, old_value in subcategories.items():
            new_value = new_categories[category][subcategory]
            diff = new_value - old_value
            pct_diff = (diff / old_value * 100) if old_value != 0 else float("inf")
            comparison[category][subcategory] = {
                "old": old_value,
                "new": new_value,
                "diff": diff,
                "pct_diff": pct_diff,
                "significant": abs(pct_diff) > 5.0,
            }

    return comparison


def print_comparison_tables(comparison):
    """
    Print comparison tables for each category.

    Args:
        comparison: Comparison results
    """
    # Print option type comparison
    option_type_table = Table(title="Option Type Comparison")
    option_type_table.add_column("Category", style="cyan")
    option_type_table.add_column("Subcategory", style="cyan")
    option_type_table.add_column("Old Value", justify="right")
    option_type_table.add_column("New Value", justify="right")
    option_type_table.add_column("Difference", justify="right")
    option_type_table.add_column("% Diff", justify="right")

    for category in ["calls", "puts"]:
        for subcategory, values in comparison[category].items():
            old_str = f"${values['old']:,.2f}"
            new_str = f"${values['new']:,.2f}"
            diff_str = f"${values['diff']:,.2f}"
            pct_diff_str = (
                f"{values['pct_diff']:.2f}%"
                if values["pct_diff"] != float("inf")
                else "∞"
            )
            row_style = "red" if values["significant"] else None
            option_type_table.add_row(
                category,
                subcategory,
                old_str,
                new_str,
                diff_str,
                pct_diff_str,
                style=row_style,
            )

    console.print(option_type_table)

    # Print position direction comparison
    position_table = Table(title="Position Direction Comparison")
    position_table.add_column("Category", style="cyan")
    position_table.add_column("Subcategory", style="cyan")
    position_table.add_column("Old Value", justify="right")
    position_table.add_column("New Value", justify="right")
    position_table.add_column("Difference", justify="right")
    position_table.add_column("% Diff", justify="right")

    for category in ["positive_quantity", "negative_quantity"]:
        for subcategory, values in comparison[category].items():
            old_str = f"${values['old']:,.2f}"
            new_str = f"${values['new']:,.2f}"
            diff_str = f"${values['diff']:,.2f}"
            pct_diff_str = (
                f"{values['pct_diff']:.2f}%"
                if values["pct_diff"] != float("inf")
                else "∞"
            )
            row_style = "red" if values["significant"] else None
            position_table.add_row(
                category,
                subcategory,
                old_str,
                new_str,
                diff_str,
                pct_diff_str,
                style=row_style,
            )

    console.print(position_table)

    # Print delta sign comparison
    delta_table = Table(title="Delta Sign Comparison")
    delta_table.add_column("Category", style="cyan")
    delta_table.add_column("Subcategory", style="cyan")
    delta_table.add_column("Old Value", justify="right")
    delta_table.add_column("New Value", justify="right")
    delta_table.add_column("Difference", justify="right")
    delta_table.add_column("% Diff", justify="right")

    for category in ["positive_delta", "negative_delta"]:
        for subcategory, values in comparison[category].items():
            old_str = f"${values['old']:,.2f}"
            new_str = f"${values['new']:,.2f}"
            diff_str = f"${values['diff']:,.2f}"
            pct_diff_str = (
                f"{values['pct_diff']:.2f}%"
                if values["pct_diff"] != float("inf")
                else "∞"
            )
            row_style = "red" if values["significant"] else None
            delta_table.add_row(
                category,
                subcategory,
                old_str,
                new_str,
                diff_str,
                pct_diff_str,
                style=row_style,
            )

    console.print(delta_table)

    # Print total comparison
    total_table = Table(title="Total Exposure Comparison")
    total_table.add_column("Category", style="cyan")
    total_table.add_column("Old Value", justify="right")
    total_table.add_column("New Value", justify="right")
    total_table.add_column("Difference", justify="right")
    total_table.add_column("% Diff", justify="right")

    for subcategory, values in comparison["total"].items():
        old_str = f"${values['old']:,.2f}"
        new_str = f"${values['new']:,.2f}"
        diff_str = f"${values['diff']:,.2f}"
        pct_diff_str = (
            f"{values['pct_diff']:.2f}%" if values["pct_diff"] != float("inf") else "∞"
        )
        row_style = "red" if values["significant"] else None
        total_table.add_row(
            subcategory,
            old_str,
            new_str,
            diff_str,
            pct_diff_str,
            style=row_style,
        )

    console.print(total_table)


def generate_recommendations(comparison):
    """
    Generate recommendations based on comparison results.

    Args:
        comparison: Comparison results

    Returns:
        List of recommendations
    """
    recommendations = []

    # Check for significant differences in option types
    for category in ["calls", "puts"]:
        for subcategory, values in comparison[category].items():
            if values["significant"]:
                recommendations.append(
                    f"Investigate {category} {subcategory} exposure difference: {values['pct_diff']:.2f}%"
                )

    # Check for significant differences in position direction
    for category in ["positive_quantity", "negative_quantity"]:
        for subcategory, values in comparison[category].items():
            if values["significant"]:
                recommendations.append(
                    f"Investigate {category} with {subcategory} exposure difference: {values['pct_diff']:.2f}%"
                )

    # Check for significant differences in delta sign
    for category in ["positive_delta", "negative_delta"]:
        for subcategory, values in comparison[category].items():
            if values["significant"]:
                recommendations.append(
                    f"Investigate {category} {subcategory} exposure difference: {values['pct_diff']:.2f}%"
                )

    # Check for significant differences in total exposure
    for subcategory, values in comparison["total"].items():
        if values["significant"]:
            recommendations.append(
                f"Investigate total {subcategory} exposure difference: {values['pct_diff']:.2f}%"
            )

    # Add specific recommendations based on patterns
    if (
        comparison["calls"]["long"]["significant"]
        and comparison["puts"]["short"]["significant"]
    ):
        recommendations.append(
            "Review how long calls and short puts are categorized - these should both be positive delta positions"
        )

    if (
        comparison["calls"]["short"]["significant"]
        and comparison["puts"]["long"]["significant"]
    ):
        recommendations.append(
            "Review how short calls and long puts are categorized - these should both be negative delta positions"
        )

    if (
        comparison["positive_quantity"]["positive_delta"]["significant"]
        and comparison["negative_quantity"]["negative_delta"]["significant"]
    ):
        recommendations.append(
            "Review how position direction affects exposure calculation - check for double inversion"
        )

    return recommendations


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Compare option categorization")
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
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print header
    console.print("[bold cyan]Option Categorization Comparison[/bold cyan]")
    console.print(f"Portfolio file: [cyan]{args.portfolio}[/cyan]")
    console.print()

    try:
        # Load portfolio data
        old_groups, old_summary, old_positions, new_portfolio = load_portfolio_data(
            args.portfolio
        )

        # Categorize options
        old_categories = categorize_old_options(old_groups)
        new_categories = categorize_new_options(new_portfolio)

        # Compare categorizations
        comparison = compare_categorizations(old_categories, new_categories)

        # Print comparison tables
        print_comparison_tables(comparison)

        # Generate recommendations
        recommendations = generate_recommendations(comparison)

        # Print recommendations
        console.print("\n[bold cyan]Recommendations[/bold cyan]")
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                console.print(f"{i}. {rec}")
        else:
            console.print(
                "[green]No recommendations - categorizations appear to be aligned[/green]"
            )

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Error in comparison script")
        return 1


if __name__ == "__main__":
    sys.exit(main())
