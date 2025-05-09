"""
Portfolio commands for the Folio CLI.

This module provides implementations of the portfolio commands for the Folio CLI,
including load, summary, and list.
"""

from pathlib import Path

import typer
from rich.console import Console

from src.folib.services.portfolio_service import (
    create_portfolio_summary,
    filter_positions_by_criteria,
    get_portfolio_exposures,
    sort_positions,
)
from src.folib.services.ticker_service import ticker_service

from ..formatters import (
    create_exposures_table,
    create_portfolio_summary_table,
    create_positions_table,
)
from .utils import load_portfolio

# Create Typer app for portfolio commands
portfolio_app = typer.Typer(help="View and manage the portfolio")

# Create console for rich output
console = Console()


@portfolio_app.command("load")
def portfolio_load_cmd(
    file_path: str = typer.Argument(..., help="Path to the portfolio CSV file"),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Clear cache before loading (forces fresh data)"
    ),
):
    """Load portfolio data from a CSV file."""
    try:
        # Load the portfolio
        load_portfolio(file_path, update_prices=False, no_cache=no_cache)

        # Print success message with prominent portfolio path
        console.print("[green]Successfully loaded portfolio[/green]")
        console.print(f"[bold blue]PORTFOLIO:[/bold blue] [bold]{file_path}[/bold]")

    except Exception as e:
        console.print(f"[red]Error loading portfolio:[/red] {e!s}")
        raise typer.Exit(code=1) from e


@portfolio_app.command("summary")
def portfolio_summary_cmd(
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Clear cache before loading (forces fresh data)"
    ),
):
    """Display high-level portfolio metrics."""
    try:
        # Load the portfolio
        result = load_portfolio(file_path, no_cache=no_cache)
        portfolio = result["portfolio"]

        # Create portfolio summary
        console.print("Creating portfolio summary...")
        summary = create_portfolio_summary(portfolio)

        # Calculate portfolio exposures
        console.print("Calculating portfolio exposures...")
        exposures = get_portfolio_exposures(portfolio)

        # Display portfolio summary
        console.print("\n")
        console.print(create_portfolio_summary_table(summary))

        # Display portfolio exposures
        console.print("\n")
        console.print(create_exposures_table(exposures))

        # Display position counts
        console.print("\n[bold]Position Counts:[/bold]")
        console.print(f"Total Positions: {len(portfolio.positions)}")
        console.print(f"Stock Positions: {len(portfolio.stock_positions)}")
        console.print(f"Option Positions: {len(portfolio.option_positions)}")
        console.print(f"Cash Positions: {len(portfolio.cash_positions)}")
        console.print(f"Unknown Positions: {len(portfolio.unknown_positions)}")

    except Exception as e:
        console.print(f"[red]Error creating portfolio summary:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Define argument outside the function to avoid B008 lint error
filter_args_arg = typer.Argument(
    None,
    help="Filter criteria in key=value format (e.g., type=stock symbol=AAPL sort=value:desc)",
)


@portfolio_app.command("list")
def portfolio_list_cmd(
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
    filter_args: list[str] = filter_args_arg,
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Clear cache before loading (forces fresh data)"
    ),
):
    """
    List positions with filtering and sorting.

    Examples:
        portfolio list type=stock
        portfolio list symbol=AAPL
        portfolio list type=option sort=symbol:asc
        portfolio list min_value=10000 max_value=50000
    """
    try:
        # Load the portfolio
        result = load_portfolio(file_path, no_cache=no_cache)
        portfolio = result["portfolio"]

        # Get all positions
        positions = portfolio.positions

        # Parse filter arguments
        filter_criteria = {}
        sort_by = "beta_adjusted_exposure"  # Default to beta-adjusted exposure
        sort_direction = "desc"

        if filter_args:
            for arg in filter_args:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    if key.lower() == "sort":
                        # Handle sort separately
                        if ":" in value:
                            sort_by, sort_direction = value.split(":", 1)
                        else:
                            sort_by = value
                    else:
                        # Add to filter criteria
                        filter_criteria[key.lower()] = value

        # Apply filters using the filter_positions_by_criteria function
        filtered_positions = filter_positions_by_criteria(positions, filter_criteria)

        # Use standard sorting for all fields
        filtered_positions = sort_positions(filtered_positions, sort_by, sort_direction)

        # Display positions
        if filtered_positions:
            # Get portfolio exposures to access exposure data
            get_portfolio_exposures(portfolio)

            # Create a list of dictionaries for the table using to_dict method
            position_data = []

            for position in filtered_positions:
                # Start with the basic position data
                pos_dict = position.to_dict()

                # Calculate exposure based on position type
                if position.position_type == "stock":
                    from src.folib.calculations.exposure import (
                        calculate_beta_adjusted_exposure,
                        calculate_stock_exposure,
                    )

                    # Calculate stock exposure
                    market_exposure = calculate_stock_exposure(
                        position.quantity, position.price
                    )
                    # Get beta for the stock using the ticker service
                    beta = ticker_service.get_beta(position.ticker)
                    # Calculate beta-adjusted exposure
                    beta_adjusted_exposure = calculate_beta_adjusted_exposure(
                        market_exposure, beta
                    )
                elif position.position_type == "option":
                    from src.folib.calculations.exposure import (
                        calculate_beta_adjusted_exposure,
                        calculate_option_exposure,
                    )
                    from src.folib.calculations.options import calculate_option_delta

                    # Get underlying price and beta using the ticker service
                    underlying_price = ticker_service.get_price(position.ticker)
                    beta = ticker_service.get_beta(position.ticker)

                    # If price is 0, use strike as fallback
                    if underlying_price == 0:
                        underlying_price = position.strike

                    # Calculate delta
                    delta = calculate_option_delta(
                        option_type=position.option_type,
                        strike=position.strike,
                        expiry=position.expiry,
                        underlying_price=underlying_price,
                    )

                    # Calculate exposure
                    market_exposure = calculate_option_exposure(
                        position.quantity, underlying_price, delta
                    )
                    beta_adjusted_exposure = calculate_beta_adjusted_exposure(
                        market_exposure, beta
                    )
                else:
                    # For cash or unknown positions, get values from ticker service
                    beta = ticker_service.get_beta(position.ticker)
                    market_exposure = 0.0  # Cash has no market exposure
                    beta_adjusted_exposure = 0.0  # Cash has no beta-adjusted exposure

                # Add beta and exposure values to the position dictionary
                pos_dict["beta"] = beta
                pos_dict["beta_adjusted_exposure"] = beta_adjusted_exposure

                position_data.append(pos_dict)

            # Sort position data by beta-adjusted exposure if that's the sort criteria
            if sort_by.lower() == "beta_adjusted_exposure":
                position_data.sort(
                    key=lambda x: x["beta_adjusted_exposure"],
                    reverse=(sort_direction.lower() == "desc"),
                )

            # Create and display the table
            table = create_positions_table(
                position_data,
                title=f"Portfolio Positions ({len(filtered_positions)} of {len(positions)})",
            )
            console.print(table)

            # Display filter criteria if any
            if filter_criteria:
                filter_desc = [f"{k}={v}" for k, v in filter_criteria.items()]
                console.print(f"[italic]Filtered by: {', '.join(filter_desc)}[/italic]")

            # Display sort criteria
            console.print(f"[italic]Sorted by: {sort_by} ({sort_direction})[/italic]")
        else:
            console.print("[yellow]No positions match the specified filters[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing positions:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Interactive mode command functions


def portfolio_load(state, args):
    """Load portfolio data from a CSV file (interactive mode)."""
    if not args:
        console.print("[red]Error:[/red] Missing file path")
        console.print("Usage: portfolio load <FILE_PATH> [--no-cache]")
        return

    # Parse arguments
    file_path = args[0]
    no_cache = "--no-cache" in args

    try:
        # Load the portfolio
        result = load_portfolio(file_path, no_cache=no_cache)

        # Update state
        state.loaded_portfolio_path = Path(file_path)
        state.portfolio_df = result["df"]
        state.portfolio = result["portfolio"]
        state.portfolio_summary = create_portfolio_summary(result["portfolio"])

        # Print success message with prominent portfolio path
        console.print("[green]Successfully loaded portfolio[/green]")
        console.print(f"[bold blue]PORTFOLIO:[/bold blue] [bold]{file_path}[/bold]")

    except Exception as e:
        console.print(f"[red]Error loading portfolio:[/red] {e!s}")


def portfolio_summary(state, args):  # noqa: ARG001
    """Display high-level portfolio metrics (interactive mode)."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    try:
        # Create portfolio summary if not already created
        if state.portfolio_summary is None:
            state.portfolio_summary = create_portfolio_summary(state.portfolio)

        # Calculate portfolio exposures
        exposures = get_portfolio_exposures(state.portfolio)

        # Display portfolio summary
        console.print("\n")
        console.print(create_portfolio_summary_table(state.portfolio_summary))

        # Display portfolio exposures
        console.print("\n")
        console.print(create_exposures_table(exposures))

        # Display position counts
        console.print("\n[bold]Position Counts:[/bold]")
        console.print(f"Total Positions: {len(state.portfolio.positions)}")
        console.print(f"Stock Positions: {len(state.portfolio.stock_positions)}")
        console.print(f"Option Positions: {len(state.portfolio.option_positions)}")
        console.print(f"Cash Positions: {len(state.portfolio.cash_positions)}")
        console.print(f"Unknown Positions: {len(state.portfolio.unknown_positions)}")

    except Exception as e:
        console.print(f"[red]Error creating portfolio summary:[/red] {e!s}")


def portfolio_list(state, args):
    """
    List positions with filtering and sorting (interactive mode).

    Examples:
        portfolio list type=stock
        portfolio list symbol=AAPL
        portfolio list type=option sort=symbol:asc
        portfolio list min_value=10000 max_value=50000
    """
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    try:
        # Get all positions
        positions = state.portfolio.positions

        # Parse filter arguments
        filter_criteria = {}
        sort_by = "beta_adjusted_exposure"  # Default to beta-adjusted exposure
        sort_direction = "desc"

        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                if key.lower() == "sort":
                    # Handle sort separately
                    if ":" in value:
                        sort_by, sort_direction = value.split(":", 1)
                    else:
                        sort_by = value
                else:
                    # Add to filter criteria
                    filter_criteria[key.lower()] = value

        # Apply filters using the filter_positions_by_criteria function
        filtered_positions = filter_positions_by_criteria(positions, filter_criteria)

        # Use standard sorting for all fields
        filtered_positions = sort_positions(filtered_positions, sort_by, sort_direction)

        # Display positions
        if filtered_positions:
            # Get portfolio exposures to access exposure data
            get_portfolio_exposures(state.portfolio)

            # Create a list of dictionaries for the table using to_dict method
            position_data = []

            for position in filtered_positions:
                # Start with the basic position data
                pos_dict = position.to_dict()

                # Calculate exposure based on position type
                if position.position_type == "stock":
                    from src.folib.calculations.exposure import (
                        calculate_beta_adjusted_exposure,
                        calculate_stock_exposure,
                    )

                    # Calculate stock exposure
                    market_exposure = calculate_stock_exposure(
                        position.quantity, position.price
                    )
                    # Get beta for the stock using the ticker service
                    beta = ticker_service.get_beta(position.ticker)
                    # Calculate beta-adjusted exposure
                    beta_adjusted_exposure = calculate_beta_adjusted_exposure(
                        market_exposure, beta
                    )
                elif position.position_type == "option":
                    from src.folib.calculations.exposure import (
                        calculate_beta_adjusted_exposure,
                        calculate_option_exposure,
                    )
                    from src.folib.calculations.options import calculate_option_delta

                    # Get underlying price and beta using the ticker service
                    underlying_price = ticker_service.get_price(position.ticker)
                    beta = ticker_service.get_beta(position.ticker)

                    # If price is 0, use strike as fallback
                    if underlying_price == 0:
                        underlying_price = position.strike

                    # Calculate delta
                    delta = calculate_option_delta(
                        option_type=position.option_type,
                        strike=position.strike,
                        expiry=position.expiry,
                        underlying_price=underlying_price,
                    )

                    # Calculate exposure
                    market_exposure = calculate_option_exposure(
                        position.quantity, underlying_price, delta
                    )
                    beta_adjusted_exposure = calculate_beta_adjusted_exposure(
                        market_exposure, beta
                    )
                else:
                    # For cash or unknown positions, get values from ticker service
                    beta = ticker_service.get_beta(position.ticker)
                    market_exposure = 0.0  # Cash has no market exposure
                    beta_adjusted_exposure = 0.0  # Cash has no beta-adjusted exposure

                # Add beta and exposure values to the position dictionary
                pos_dict["beta"] = beta
                pos_dict["beta_adjusted_exposure"] = beta_adjusted_exposure

                position_data.append(pos_dict)

            # Sort position data by beta-adjusted exposure if that's the sort criteria
            if sort_by.lower() == "beta_adjusted_exposure":
                position_data.sort(
                    key=lambda x: x["beta_adjusted_exposure"],
                    reverse=(sort_direction.lower() == "desc"),
                )

            # Create and display the table
            table = create_positions_table(
                position_data,
                title=f"Portfolio Positions ({len(filtered_positions)} of {len(positions)})",
            )
            console.print(table)

            # Display filter criteria if any
            if filter_criteria:
                filter_desc = [f"{k}={v}" for k, v in filter_criteria.items()]
                console.print(f"[italic]Filtered by: {', '.join(filter_desc)}[/italic]")

            # Display sort criteria
            console.print(f"[italic]Sorted by: {sort_by} ({sort_direction})[/italic]")
        else:
            console.print("[yellow]No positions match the specified filters[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing positions:[/red] {e!s}")
