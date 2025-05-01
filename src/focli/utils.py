"""
Utility functions for the Folio CLI.

This module provides helper functions used across the CLI.
"""

import logging
import os
from pathlib import Path

import pandas as pd

# Set up logging
logger = logging.getLogger(__name__)

from src.folib.data.loader import parse_portfolio_holdings
from src.folib.services.portfolio_service import (
    create_portfolio_groups_from_positions,
    create_portfolio_summary,
    process_portfolio,
)

# Import both old and new portfolio processing functions for transition
from src.folio.portfolio import process_portfolio_data


def load_portfolio(path, state, console=None):
    """Load a portfolio from a CSV file using folib.

    This function attempts to load a portfolio from the specified path.
    If no path is provided, it tries to load the default portfolio.
    If the specified file doesn't exist, it tries to find any CSV file
    in the default portfolio folder.

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

    # If no path is provided, use the default portfolio file
    if path is None:
        default_portfolio = "private-data/portfolios/portfolio-default.csv"
        console.print(
            f"No path provided, trying default portfolio: [cyan]{default_portfolio}[/cyan]"
        )
        path = default_portfolio

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
        # If the specified file doesn't exist, try to find any CSV in the default folder
        default_folder = Path(os.getcwd()) / "private-data/portfolios"
        if not default_folder.exists():
            project_root = Path(__file__).parent.parent.parent
            default_folder = project_root / "private-data/portfolios"

        if default_folder.exists():
            csv_files = list(default_folder.glob("*.csv"))
            if csv_files:
                resolved_path = csv_files[0]
                console.print(
                    f"Using portfolio from default folder: [cyan]{resolved_path}[/cyan]"
                )
            else:
                raise FileNotFoundError(
                    f"Portfolio file not found: {path} and no CSV files in {default_folder}"
                )
        else:
            raise FileNotFoundError(
                f"Portfolio file not found: {path} and default folder {default_folder} does not exist"
            )

    # Load the portfolio
    console.print(f"Loading portfolio from [cyan]{resolved_path}[/cyan]...")

    try:
        # Load the CSV file
        df = pd.read_csv(resolved_path)

        # Process using folib
        try:
            # Log which data provider is being used
            from src.folib.data.stock import stockdata

            logger.info(f"Using {stockdata.provider_name} provider for market data")
            logger.debug(f"Cache directory: {stockdata.cache_dir}")

            # Parse the portfolio holdings
            holdings = parse_portfolio_holdings(df)
            logger.debug(f"Parsed {len(holdings)} holdings from portfolio file")

            # Process the portfolio
            portfolio = process_portfolio(holdings)
            logger.debug(
                f"Processed portfolio with {len(portfolio.positions)} positions"
            )

            # Create portfolio summary
            summary = create_portfolio_summary(portfolio)
            logger.debug("Created portfolio summary")

            # For backward compatibility, create portfolio groups
            groups = create_portfolio_groups_from_positions(portfolio.positions)
            logger.debug(
                f"Created {len(groups)} portfolio groups for backward compatibility"
            )

            # Update the state
            state["portfolio"] = portfolio  # New folib Portfolio object
            state["portfolio_groups"] = groups  # For backward compatibility
            state["portfolio_summary"] = summary  # New folib PortfolioSummary object
            state["loaded_portfolio"] = str(resolved_path)

            console.print(
                f"Loaded portfolio with [green]{len(groups)}[/green] position groups using folib."
            )
            return groups, summary

        except Exception as folib_error:
            # If folib processing fails, fall back to the old method
            console.print(
                f"[yellow]Warning:[/yellow] folib processing failed: {folib_error}"
            )
            console.print(
                "[yellow]Falling back to legacy portfolio processing...[/yellow]"
            )

            # Process using the old method
            groups, summary, _ = process_portfolio_data(df, update_prices=True)

            # Update the state (old format only)
            state["portfolio_groups"] = groups
            state["portfolio_summary"] = summary
            state["loaded_portfolio"] = str(resolved_path)

            console.print(
                f"Loaded portfolio with [green]{len(groups)}[/green] position groups using legacy processor."
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


def find_positions_by_ticker(ticker, portfolio):
    """Find positions by ticker in a folib Portfolio.

    Args:
        ticker: Ticker symbol to find
        portfolio: folib Portfolio object

    Returns:
        Dictionary with stock and option positions for the ticker
    """
    from src.folib.services.portfolio_service import (
        get_option_positions_by_ticker,
        get_stock_position_by_ticker,
    )

    if not portfolio or not hasattr(portfolio, "positions"):
        return {
            "ticker": ticker.upper(),
            "stock_position": None,
            "option_positions": [],
        }

    # Normalize the ticker
    ticker = ticker.upper()

    # Find the positions
    stock_position = get_stock_position_by_ticker(portfolio.positions, ticker)
    option_positions = get_option_positions_by_ticker(portfolio.positions, ticker)

    return {
        "ticker": ticker,
        "stock_position": stock_position,
        "option_positions": option_positions,
    }


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


def filter_portfolio_positions(portfolio, filter_criteria=None):
    """Filter portfolio positions based on criteria.

    Args:
        portfolio: folib Portfolio object
        filter_criteria: Dictionary of filter criteria
            - tickers: List of tickers to include
            - min_value: Minimum position value
            - max_value: Maximum position value
            - has_options: Whether to include positions with options
            - has_stock: Whether to include positions with stock

    Returns:
        Filtered list of positions
    """
    from src.folib.services.portfolio_service import get_positions_by_type

    if not portfolio or not hasattr(portfolio, "positions") or not filter_criteria:
        return (
            portfolio.positions if portfolio and hasattr(portfolio, "positions") else []
        )

    filtered_positions = portfolio.positions

    # Filter by tickers
    if filter_criteria.get("tickers"):
        tickers = [t.upper() for t in filter_criteria["tickers"]]
        filtered_positions = [
            p for p in filtered_positions if p.ticker.upper() in tickers
        ]

    # Filter by position type
    if filter_criteria.get("has_options") is not None:
        has_options = filter_criteria["has_options"]
        if has_options:
            filtered_positions = get_positions_by_type(filtered_positions, "option")
        else:
            filtered_positions = [
                p for p in filtered_positions if p.position_type != "option"
            ]

    if filter_criteria.get("has_stock") is not None:
        has_stock = filter_criteria["has_stock"]
        if has_stock:
            filtered_positions = get_positions_by_type(filtered_positions, "stock")
        else:
            filtered_positions = [
                p for p in filtered_positions if p.position_type != "stock"
            ]

    # Filter by value
    if filter_criteria.get("min_value") is not None:
        filtered_positions = [
            p
            for p in filtered_positions
            if p.market_value >= filter_criteria["min_value"]
        ]

    if filter_criteria.get("max_value") is not None:
        filtered_positions = [
            p
            for p in filtered_positions
            if p.market_value <= filter_criteria["max_value"]
        ]

    return filtered_positions
