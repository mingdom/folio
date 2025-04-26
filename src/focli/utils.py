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


def calculate_position_value_with_price_change(position_group, price_change):
    """Calculate the value of a position with a given price change.

    Args:
        position_group: PortfolioGroup to calculate
        price_change: Price change as a decimal (e.g., 0.05 for 5% increase)

    Returns:
        New position value
    """
    # Start with current value

    # For a simple implementation, we'll adjust the value based on the price change
    # This is a simplified approach - in a real implementation, we would recalculate
    # option values based on the new underlying price and delta

    # Calculate stock value change
    stock_value = (
        position_group.stock_position.market_value
        if position_group.stock_position
        else 0
    )
    new_stock_value = stock_value * (1 + price_change)

    # Calculate option value change (simplified)
    option_value = (
        sum(op.market_value for op in position_group.option_positions)
        if position_group.option_positions
        else 0
    )

    # For options, we use delta to approximate the change
    # This is a simplified approach
    option_delta_exposure = (
        position_group.total_delta_exposure
        if hasattr(position_group, "total_delta_exposure")
        else 0
    )
    option_delta_change = option_delta_exposure * price_change
    new_option_value = option_value + option_delta_change

    # Total new value
    new_value = new_stock_value + new_option_value

    return new_value


def simulate_position_with_spy_changes(position_group, spy_changes):
    """Simulate a position with SPY changes.

    Args:
        position_group: PortfolioGroup to simulate
        spy_changes: List of SPY changes as decimals

    Returns:
        Dictionary with simulation results
    """
    ticker = position_group.ticker
    beta = position_group.beta
    current_value = position_group.net_exposure

    # Calculate position values at different SPY changes
    values = []
    for spy_change in spy_changes:
        # Calculate the price change for this position based on beta
        price_change = spy_change * beta

        # Calculate the new position value
        new_value = calculate_position_value_with_price_change(
            position_group, price_change
        )
        values.append(new_value)

    # Calculate changes from current value
    changes = [value - current_value for value in values]
    pct_changes = [
        (change / current_value) * 100 if current_value != 0 else 0
        for change in changes
    ]

    # Find min and max values
    min_value = min(values)
    max_value = max(values)
    min_index = values.index(min_value)
    max_index = values.index(max_value)
    min_spy_change = spy_changes[min_index] * 100  # Convert to percentage
    max_spy_change = spy_changes[max_index] * 100  # Convert to percentage

    # Create results dictionary
    results = {
        "ticker": ticker,
        "beta": beta,
        "current_value": current_value,
        "spy_changes": spy_changes,
        "values": values,
        "changes": changes,
        "pct_changes": pct_changes,
        "min_value": min_value,
        "max_value": max_value,
        "min_spy_change": min_spy_change,
        "max_spy_change": max_spy_change,
    }

    return results


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
