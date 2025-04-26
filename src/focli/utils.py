"""
Utility functions for the Folio CLI.

This module provides helper functions used across the CLI.
"""

import os
from pathlib import Path

import pandas as pd

from src.folio.portfolio import process_portfolio_data


def load_portfolio(path, state, console=None):
    """Load a portfolio from a CSV file.

    Args:
        path: Path to the portfolio CSV file
        state: Application state dictionary
        console: Rich console for output

    Returns:
        Tuple of (groups, summary)
    """
    from rich.console import Console

    if console is None:
        console = Console()

    # Resolve the path
    if not os.path.isabs(path):
        # Try relative to current directory
        resolved_path = Path(os.getcwd()) / path
        if not resolved_path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            resolved_path = project_root / path
    else:
        resolved_path = Path(path)

    # Check if the file exists
    if not resolved_path.exists():
        raise FileNotFoundError(f"Portfolio file not found: {path}")

    # Load the portfolio
    console.print(f"Loading portfolio from [cyan]{resolved_path}[/cyan]...")

    try:
        df = pd.read_csv(resolved_path)
        groups, summary, _ = process_portfolio_data(df, update_prices=True)

        # Update the state
        state["portfolio_groups"] = groups
        state["portfolio_summary"] = summary
        state["loaded_portfolio"] = str(resolved_path)

        console.print(
            f"Loaded portfolio with [green]{len(groups)}[/green] position groups."
        )
        return groups, summary
    except Exception as e:
        raise RuntimeError(f"Error loading portfolio: {e!s}") from e


def find_position_group(ticker, portfolio_groups):
    """Find a position group by ticker.

    Args:
        ticker: Ticker symbol to find
        portfolio_groups: List of portfolio groups

    Returns:
        PortfolioGroup if found, None otherwise
    """
    if not portfolio_groups:
        return None

    # Normalize the ticker
    ticker = ticker.upper()

    # Find the group
    for group in portfolio_groups:
        if group.ticker == ticker:
            return group

    return None


def parse_args(args, arg_specs):
    """Parse command arguments according to specifications.

    Args:
        args: List of argument strings
        arg_specs: Dictionary mapping argument names to specifications
            Each specification is a dictionary with:
                - type: Type to convert to (float, int, str, bool)
                - default: Default value
                - help: Help text
                - aliases: List of aliases (e.g., ['-r', '--range'])

    Returns:
        Dictionary of parsed arguments
    """
    # Initialize with default values
    result = {name: spec.get("default") for name, spec in arg_specs.items()}

    # Parse arguments
    i = 0
    while i < len(args):
        arg = args[i]

        # Check if this is a flag/option
        if arg.startswith("-"):
            # Find the matching argument
            found = False
            for name, spec in arg_specs.items():
                aliases = spec.get("aliases", [])
                if arg in aliases:
                    # This is a match
                    found = True

                    # Handle boolean flags
                    if spec.get("type") is bool:
                        result[name] = True
                        i += 1
                        break

                    # Handle value arguments
                    if i + 1 < len(args):
                        try:
                            # Convert to the specified type
                            value = args[i + 1]
                            if spec.get("type") is float:
                                result[name] = float(value)
                            elif spec.get("type") is int:
                                result[name] = int(value)
                            else:
                                result[name] = value
                            i += 2
                            break
                        except ValueError as ve:
                            raise ValueError(
                                f"Invalid value for {arg}: {args[i + 1]}"
                            ) from ve
                    else:
                        raise ValueError(f"Missing value for {arg}")

            if not found:
                raise ValueError(f"Unknown argument: {arg}")
        else:
            # This is a positional argument
            # For now, we'll just skip it
            i += 1

    return result


def filter_portfolio_groups(portfolio_groups, filter_criteria=None):
    """Filter portfolio groups based on criteria.

    Args:
        portfolio_groups: List of portfolio groups
        filter_criteria: Dictionary of filter criteria
            - tickers: List of tickers to include
            - min_value: Minimum position value
            - max_value: Maximum position value
            - has_options: Whether to include positions with options
            - has_stock: Whether to include positions with stock

    Returns:
        Filtered list of portfolio groups
    """
    if not filter_criteria:
        return portfolio_groups

    filtered_groups = portfolio_groups

    # Filter by tickers
    if filter_criteria.get("tickers"):
        tickers = [t.upper() for t in filter_criteria["tickers"]]
        filtered_groups = [g for g in filtered_groups if g.ticker in tickers]

    # Filter by value
    if filter_criteria.get("min_value") is not None:
        filtered_groups = [
            g for g in filtered_groups if g.net_exposure >= filter_criteria["min_value"]
        ]

    if filter_criteria.get("max_value") is not None:
        filtered_groups = [
            g for g in filtered_groups if g.net_exposure <= filter_criteria["max_value"]
        ]

    # Filter by position type
    if filter_criteria.get("has_options") is not None:
        has_options = filter_criteria["has_options"]
        filtered_groups = [
            g for g in filtered_groups if bool(g.option_positions) == has_options
        ]

    if filter_criteria.get("has_stock") is not None:
        has_stock = filter_criteria["has_stock"]
        filtered_groups = [
            g for g in filtered_groups if bool(g.stock_position) == has_stock
        ]

    return filtered_groups
