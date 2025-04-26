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


def generate_spy_changes(range_pct, steps):
    """Generate a list of SPY changes for simulation.

    Args:
        range_pct: Range of SPY changes in percent (e.g., 20.0 for ±20%)
        steps: Number of steps in the simulation

    Returns:
        List of SPY changes as decimals (e.g., [-0.2, -0.1, 0.0, 0.1, 0.2])
    """
    # Calculate the step size
    step_size = (2 * range_pct) / (steps - 1) if steps > 1 else 0

    # Generate the SPY changes
    spy_changes = [-range_pct + i * step_size for i in range(steps)]

    # Ensure we have a zero point
    if 0.0 not in spy_changes and steps > 2:
        # Find the closest point to zero and replace it with zero
        closest_to_zero = min(spy_changes, key=lambda x: abs(x))
        zero_index = spy_changes.index(closest_to_zero)
        spy_changes[zero_index] = 0.0

    # Convert to percentages
    spy_changes = [change / 100.0 for change in spy_changes]

    return spy_changes


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
