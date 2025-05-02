"""
Utility functions for CLI commands.

This module provides utility functions used by multiple command implementations.
"""

from pathlib import Path
from typing import Any

from rich.console import Console

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.services.portfolio_service import process_portfolio

# Create console for rich output
console = Console()


def resolve_portfolio_path(file_path: str | None = None) -> Path:
    """
    Resolve a portfolio file path, using the default if none is provided.

    Args:
        file_path: Path to the portfolio file, or None to use the default

    Returns:
        Resolved Path object

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    # Use default path if none provided
    if file_path is None:
        file_path = "private-data/portfolios/portfolio-default.csv"

    # Resolve the path
    path = Path(file_path)

    # Check if the file exists
    if not path.exists():
        raise FileNotFoundError(f"Portfolio file not found: {path}")

    return path


def load_portfolio(file_path: str | None = None) -> dict[str, Any]:
    """
    Load a portfolio from a CSV file.

    Args:
        file_path: Path to the portfolio file, or None to use the default

    Returns:
        Dictionary containing:
        - df: Raw DataFrame from the CSV
        - holdings: Parsed portfolio holdings
        - portfolio: Processed portfolio

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is invalid
    """
    # Resolve the portfolio path
    path = resolve_portfolio_path(file_path)

    # Load the portfolio from CSV
    console.print(f"Loading portfolio from [bold]{path}[/bold]...")
    df = load_portfolio_from_csv(path)
    console.print(f"Loaded [bold]{len(df)}[/bold] rows from CSV")

    # Parse portfolio holdings
    console.print("Parsing portfolio holdings...")
    holdings = parse_portfolio_holdings(df)
    console.print(f"Parsed [bold]{len(holdings)}[/bold] holdings")

    # Process the portfolio
    console.print("Processing portfolio...")
    portfolio = process_portfolio(holdings)
    console.print(
        f"Processed portfolio with [bold]{len(portfolio.positions)}[/bold] positions"
    )

    return {
        "df": df,
        "holdings": holdings,
        "portfolio": portfolio,
    }
