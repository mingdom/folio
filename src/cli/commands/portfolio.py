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
    get_portfolio_exposures,
)

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
):
    """Load portfolio data from a CSV file."""
    try:
        # Load the portfolio
        load_portfolio(file_path)

        # Print success message
        console.print(f"[green]Successfully loaded portfolio from {file_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error loading portfolio:[/red] {e!s}")
        raise typer.Exit(code=1)


@portfolio_app.command("summary")
def portfolio_summary_cmd(
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
):
    """Display high-level portfolio metrics."""
    try:
        # Load the portfolio
        result = load_portfolio(file_path)
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
        raise typer.Exit(code=1)


@portfolio_app.command("list")
def portfolio_list_cmd(
    file_path: str | None = typer.Option(
        None, "--file", "-f", help="Path to the portfolio CSV file"
    ),
    focus: str | None = typer.Option(
        None, "--focus", help="Focus on specific tickers (comma-separated)"
    ),
    position_type: str | None = typer.Option(
        None, "--type", help="Filter by position type (stock, option, cash)"
    ),
    min_value: float | None = typer.Option(
        None, "--min-value", help="Minimum position value"
    ),
    max_value: float | None = typer.Option(
        None, "--max-value", help="Maximum position value"
    ),
    sort_by: str = typer.Option(
        "value:desc", "--sort", help="Sort by field (ticker, value, beta, exposure)"
    ),
):
    """List positions with filtering and sorting."""
    try:
        # Load the portfolio
        result = load_portfolio(file_path)
        portfolio = result["portfolio"]

        # Get all positions
        positions = portfolio.positions

        # Apply filters
        filtered_positions = positions

        # Filter by position type
        if position_type:
            position_type = position_type.lower()
            if position_type == "stock":
                filtered_positions = portfolio.stock_positions
            elif position_type == "option":
                filtered_positions = portfolio.option_positions
            elif position_type == "cash":
                filtered_positions = portfolio.cash_positions
            elif position_type == "unknown":
                filtered_positions = portfolio.unknown_positions

        # Filter by ticker
        if focus:
            tickers = [t.strip().upper() for t in focus.split(",")]
            filtered_positions = [p for p in filtered_positions if p.ticker in tickers]

        # Filter by value
        if min_value is not None:
            filtered_positions = [
                p for p in filtered_positions if abs(p.market_value) >= min_value
            ]
        if max_value is not None:
            filtered_positions = [
                p for p in filtered_positions if abs(p.market_value) <= max_value
            ]

        # Sort positions
        sort_field, sort_direction = (
            sort_by.split(":") if ":" in sort_by else (sort_by, "asc")
        )

        if sort_field == "ticker":
            filtered_positions.sort(key=lambda p: p.ticker)
        elif sort_field == "value":
            filtered_positions.sort(key=lambda p: abs(p.market_value))
        elif sort_field == "beta":
            # Beta sorting requires additional data, not implemented yet
            console.print(
                "[yellow]Warning:[/yellow] Sorting by beta not implemented yet, using value instead"
            )
            filtered_positions.sort(key=lambda p: abs(p.market_value))
        elif sort_field == "exposure":
            # Exposure sorting requires additional data, not implemented yet
            console.print(
                "[yellow]Warning:[/yellow] Sorting by exposure not implemented yet, using value instead"
            )
            filtered_positions.sort(key=lambda p: abs(p.market_value))
        else:
            # Default to sorting by value
            filtered_positions.sort(key=lambda p: abs(p.market_value))

        # Reverse if descending
        if sort_direction.lower() == "desc":
            filtered_positions.reverse()

        # Display positions
        if filtered_positions:
            # Create a list of dictionaries for the table using to_dict method
            position_data = [p.to_dict() for p in filtered_positions]

            # Create and display the table
            table = create_positions_table(
                position_data,
                title=f"Portfolio Positions ({len(filtered_positions)} of {len(positions)})",
            )
            console.print(table)
        else:
            console.print("[yellow]No positions match the specified filters[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing positions:[/red] {e!s}")
        raise typer.Exit(code=1)


# Interactive mode command functions


def portfolio_load(state, args):
    """Load portfolio data from a CSV file (interactive mode)."""
    if not args:
        console.print("[red]Error:[/red] Missing file path")
        console.print("Usage: portfolio load <FILE_PATH>")
        return

    file_path = args[0]

    try:
        # Load the portfolio
        result = load_portfolio(file_path)

        # Update state
        state.loaded_portfolio_path = Path(file_path)
        state.portfolio_df = result["df"]
        state.portfolio = result["portfolio"]
        state.portfolio_summary = create_portfolio_summary(result["portfolio"])

        # Print success message
        console.print(f"[green]Successfully loaded portfolio from {file_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error loading portfolio:[/red] {e!s}")


def portfolio_summary(state, args):
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
    """List positions with filtering and sorting (interactive mode)."""
    # Check if portfolio is loaded
    if not state.has_portfolio():
        console.print("[red]Error:[/red] No portfolio loaded")
        console.print("Use 'portfolio load <FILE_PATH>' to load a portfolio")
        return

    # Parse arguments
    focus = None
    position_type = None
    min_value = None
    max_value = None
    sort_by = "value:desc"

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--focus" and i + 1 < len(args):
            focus = args[i + 1]
            i += 2
        elif arg == "--type" and i + 1 < len(args):
            position_type = args[i + 1]
            i += 2
        elif arg == "--min-value" and i + 1 < len(args):
            try:
                min_value = float(args[i + 1])
                i += 2
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid min-value: {args[i + 1]}")
                return
        elif arg == "--max-value" and i + 1 < len(args):
            try:
                max_value = float(args[i + 1])
                i += 2
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid max-value: {args[i + 1]}")
                return
        elif arg == "--sort" and i + 1 < len(args):
            sort_by = args[i + 1]
            i += 2
        else:
            i += 1

    try:
        # Get all positions
        positions = state.portfolio.positions

        # Apply filters
        filtered_positions = positions

        # Filter by position type
        if position_type:
            position_type = position_type.lower()
            if position_type == "stock":
                filtered_positions = state.portfolio.stock_positions
            elif position_type == "option":
                filtered_positions = state.portfolio.option_positions
            elif position_type == "cash":
                filtered_positions = state.portfolio.cash_positions
            elif position_type == "unknown":
                filtered_positions = state.portfolio.unknown_positions

        # Filter by ticker
        if focus:
            tickers = [t.strip().upper() for t in focus.split(",")]
            filtered_positions = [p for p in filtered_positions if p.ticker in tickers]

        # Filter by value
        if min_value is not None:
            filtered_positions = [
                p for p in filtered_positions if abs(p.market_value) >= min_value
            ]
        if max_value is not None:
            filtered_positions = [
                p for p in filtered_positions if abs(p.market_value) <= max_value
            ]

        # Sort positions
        sort_field, sort_direction = (
            sort_by.split(":") if ":" in sort_by else (sort_by, "asc")
        )

        if sort_field == "ticker":
            filtered_positions.sort(key=lambda p: p.ticker)
        elif sort_field == "value":
            filtered_positions.sort(key=lambda p: abs(p.market_value))
        elif sort_field == "beta":
            # Beta sorting requires additional data, not implemented yet
            console.print(
                "[yellow]Warning:[/yellow] Sorting by beta not implemented yet, using value instead"
            )
            filtered_positions.sort(key=lambda p: abs(p.market_value))
        elif sort_field == "exposure":
            # Exposure sorting requires additional data, not implemented yet
            console.print(
                "[yellow]Warning:[/yellow] Sorting by exposure not implemented yet, using value instead"
            )
            filtered_positions.sort(key=lambda p: abs(p.market_value))
        else:
            # Default to sorting by value
            filtered_positions.sort(key=lambda p: abs(p.market_value))

        # Reverse if descending
        if sort_direction.lower() == "desc":
            filtered_positions.reverse()

        # Display positions
        if filtered_positions:
            # Create a list of dictionaries for the table using to_dict method
            position_data = [p.to_dict() for p in filtered_positions]

            # Create and display the table
            table = create_positions_table(
                position_data,
                title=f"Portfolio Positions ({len(filtered_positions)} of {len(positions)})",
            )
            console.print(table)
        else:
            console.print("[yellow]No positions match the specified filters[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing positions:[/red] {e!s}")
