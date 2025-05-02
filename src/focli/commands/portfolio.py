"""
Portfolio management commands for the Folio CLI.

This module provides commands for managing and analyzing portfolios.
"""

from typing import Any

from rich.box import ROUNDED
from rich.table import Table

from src.focli.formatters import display_portfolio_summary, format_currency
from src.focli.utils import (
    filter_portfolio_groups,
    filter_portfolio_positions,
    load_portfolio,
    parse_args,
)


def portfolio_command(args: list[str], state: dict[str, Any], console):
    """View and analyze portfolio.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if we have a subcommand
    if not args:
        # Default to summary if no subcommand is specified
        portfolio_summary([], state, console)
        return

    subcommand = args[0].lower()
    subcommand_args = args[1:]

    if subcommand == "list":
        portfolio_list(subcommand_args, state, console)
    elif subcommand == "summary":
        portfolio_summary(subcommand_args, state, console)
    elif subcommand == "load":
        portfolio_load(subcommand_args, state, console)
    else:
        console.print(f"[bold red]Unknown subcommand:[/bold red] {subcommand}")
        console.print("Available subcommands: list, summary, load")


def portfolio_list(args: list[str], state: dict[str, Any], console):
    """List all positions in the portfolio.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio") and not state.get("portfolio_groups"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Define argument specifications
    arg_specs = {
        "focus": {
            "type": str,
            "default": None,
            "help": "Comma-separated list of tickers to focus on",
            "aliases": ["-f", "--focus"],
        },
        "options": {
            "type": bool,
            "default": None,
            "help": "Show only positions with options",
            "aliases": ["--options"],
        },
        "stocks": {
            "type": bool,
            "default": None,
            "help": "Show only positions with stocks",
            "aliases": ["--stocks"],
        },
        "min_value": {
            "type": float,
            "default": None,
            "help": "Minimum position value",
            "aliases": ["--min-value"],
        },
        "max_value": {
            "type": float,
            "default": None,
            "help": "Maximum position value",
            "aliases": ["--max-value"],
        },
        "sort": {
            "type": str,
            "default": "ticker",
            "help": "Sort by: ticker, value, beta",
            "aliases": ["-s", "--sort"],
        },
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)

        # Create filter criteria
        filter_criteria = {}

        if parsed_args["focus"]:
            filter_criteria["tickers"] = [
                t.strip().upper() for t in parsed_args["focus"].split(",")
            ]

        if parsed_args["options"] is not None:
            filter_criteria["has_options"] = parsed_args["options"]

        if parsed_args["stocks"] is not None:
            filter_criteria["has_stock"] = parsed_args["stocks"]

        if parsed_args["min_value"] is not None:
            filter_criteria["min_value"] = parsed_args["min_value"]

        if parsed_args["max_value"] is not None:
            filter_criteria["max_value"] = parsed_args["max_value"]

        # Check if we have the new folib Portfolio object
        if state.get("portfolio"):
            # Filter using the new folib functions
            from src.folib.data.stock import stockdata
            from src.folib.services.portfolio_service import group_positions_by_ticker

            # Filter the portfolio positions
            filtered_positions = filter_portfolio_positions(
                state["portfolio"], filter_criteria
            )

            # Group positions by ticker for display
            position_groups = group_positions_by_ticker(filtered_positions)

            # Create a list of groups for display and sorting
            display_groups = []
            for ticker, positions in position_groups.items():
                stock_position = None
                option_positions = []

                # Separate stock and option positions
                for position in positions:
                    if position.position_type == "stock":
                        stock_position = position
                    elif position.position_type == "option":
                        option_positions.append(position)

                # Calculate beta
                beta = stockdata.get_beta(ticker) if ticker else 1.0

                # Calculate net exposure
                stock_value = stock_position.market_value if stock_position else 0
                option_value = (
                    sum(op.market_value for op in option_positions)
                    if option_positions
                    else 0
                )
                net_exposure = stock_value + option_value

                # Create a group object for display
                display_groups.append(
                    {
                        "ticker": ticker,
                        "beta": beta,
                        "net_exposure": net_exposure,
                        "stock_position": stock_position,
                        "option_positions": option_positions,
                    }
                )

            # Sort the groups
            sort_by = parsed_args["sort"].lower()
            if sort_by == "value":
                display_groups = sorted(
                    display_groups, key=lambda g: g["net_exposure"], reverse=True
                )
            elif sort_by == "beta":
                display_groups = sorted(
                    display_groups, key=lambda g: g["beta"], reverse=True
                )
            else:  # Default to ticker
                display_groups = sorted(display_groups, key=lambda g: g["ticker"])

            # For backward compatibility, store the filtered groups
            from src.folib.services.portfolio_service import (
                create_portfolio_groups_from_positions,
            )

            state["filtered_groups"] = create_portfolio_groups_from_positions(
                filtered_positions
            )

            # Create a table of positions
            table = Table(title="Portfolio Positions", box=ROUNDED)
            table.add_column("Ticker", style="cyan")
            table.add_column("Beta", style="yellow", justify="right")
            table.add_column("Net Exposure", style="green", justify="right")
            table.add_column("Stock Value", style="green", justify="right")
            table.add_column("Option Value", style="green", justify="right")
            table.add_column("Options", style="magenta", justify="right")

            # Add rows for each position
            for group in display_groups:
                stock_value = (
                    group["stock_position"].market_value
                    if group["stock_position"]
                    else 0
                )
                option_value = (
                    sum(op.market_value for op in group["option_positions"])
                    if group["option_positions"]
                    else 0
                )
                option_count = (
                    len(group["option_positions"]) if group["option_positions"] else 0
                )

                # Handle None beta values
                beta_str = "N/A"
                if group["beta"] is not None:
                    beta_str = f"{group['beta']:.2f}"

                table.add_row(
                    group["ticker"],
                    beta_str,
                    format_currency(group["net_exposure"]),
                    format_currency(stock_value),
                    format_currency(option_value),
                    f"{option_count}",
                )

            console.print(table)

            # Print filter summary
            if filter_criteria:
                filter_desc = []
                if filter_criteria.get("tickers"):
                    filter_desc.append(
                        f"tickers: {', '.join(filter_criteria['tickers'])}"
                    )
                if filter_criteria.get("has_options") is not None:
                    filter_desc.append(f"has options: {filter_criteria['has_options']}")
                if filter_criteria.get("has_stock") is not None:
                    filter_desc.append(f"has stock: {filter_criteria['has_stock']}")
                if filter_criteria.get("min_value") is not None:
                    filter_desc.append(
                        f"min value: {format_currency(filter_criteria['min_value'])}"
                    )
                if filter_criteria.get("max_value") is not None:
                    filter_desc.append(
                        f"max value: {format_currency(filter_criteria['max_value'])}"
                    )

                console.print(f"[italic]Filtered by: {'; '.join(filter_desc)}[/italic]")
                console.print(
                    f"[italic]Showing {len(display_groups)} of {len(position_groups)} positions[/italic]"
                )

        else:
            # Fall back to the old method
            # Filter the portfolio groups
            filtered_groups = filter_portfolio_groups(
                state["portfolio_groups"], filter_criteria
            )

            # Sort the groups
            sort_by = parsed_args["sort"].lower()
            if sort_by == "value":
                filtered_groups = sorted(
                    filtered_groups, key=lambda g: g.net_exposure, reverse=True
                )
            elif sort_by == "beta":
                filtered_groups = sorted(
                    filtered_groups, key=lambda g: g.beta, reverse=True
                )
            else:  # Default to ticker
                filtered_groups = sorted(filtered_groups, key=lambda g: g.ticker)

            # Store the filtered groups in state
            state["filtered_groups"] = filtered_groups

            # Create a table of positions
            table = Table(title="Portfolio Positions", box=ROUNDED)
            table.add_column("Ticker", style="cyan")
            table.add_column("Beta", style="yellow", justify="right")
            table.add_column("Net Exposure", style="green", justify="right")
            table.add_column("Stock Value", style="green", justify="right")
            table.add_column("Option Value", style="green", justify="right")
            table.add_column("Options", style="magenta", justify="right")

            # Add rows for each position
            for group in filtered_groups:
                stock_value = (
                    group.stock_position.market_value if group.stock_position else 0
                )
                option_value = (
                    sum(op.market_value for op in group.option_positions)
                    if group.option_positions
                    else 0
                )
                option_count = (
                    len(group.option_positions) if group.option_positions else 0
                )

                table.add_row(
                    group.ticker,
                    f"{group.beta:.2f}",
                    format_currency(group.net_exposure),
                    format_currency(stock_value),
                    format_currency(option_value),
                    f"{option_count}",
                )

            console.print(table)

            # Print filter summary
            if filter_criteria:
                filter_desc = []
                if filter_criteria.get("tickers"):
                    filter_desc.append(
                        f"tickers: {', '.join(filter_criteria['tickers'])}"
                    )
                if filter_criteria.get("has_options") is not None:
                    filter_desc.append(f"has options: {filter_criteria['has_options']}")
                if filter_criteria.get("has_stock") is not None:
                    filter_desc.append(f"has stock: {filter_criteria['has_stock']}")
                if filter_criteria.get("min_value") is not None:
                    filter_desc.append(
                        f"min value: {format_currency(filter_criteria['min_value'])}"
                    )
                if filter_criteria.get("max_value") is not None:
                    filter_desc.append(
                        f"max value: {format_currency(filter_criteria['max_value'])}"
                    )

                console.print(f"[italic]Filtered by: {'; '.join(filter_desc)}[/italic]")
                console.print(
                    f"[italic]Showing {len(filtered_groups)} of {len(state['portfolio_groups'])} positions[/italic]"
                )

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error listing portfolio:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())


def portfolio_summary(args: list[str], state: dict[str, Any], console):  # noqa: ARG001
    """Show a summary of the portfolio.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio_summary") and not state.get("portfolio"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Display the portfolio summary
    if state.get("portfolio_summary"):
        display_portfolio_summary(state["portfolio_summary"], console)
    else:
        # This should not happen since we always create a portfolio_summary in load_portfolio
        console.print(
            "[bold yellow]Warning:[/bold yellow] Portfolio loaded but summary not available."
        )
        console.print("Try reloading the portfolio with 'portfolio load'.")


def portfolio_load(args: list[str], state: dict[str, Any], console):
    """Load a portfolio from a CSV file.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Get the path if provided
    path = args[0] if args else None

    # If no path is provided, inform the user we'll try the default
    if not path:
        console.print(
            "[bold yellow]No path provided.[/bold yellow] Trying default portfolio locations..."
        )

    try:
        # Load the portfolio
        load_portfolio(path, state, console)

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
        if not path:
            console.print("\n[bold yellow]Usage:[/bold yellow] portfolio load <path>")
            console.print("Type 'help portfolio load' for more information.")
    except Exception as e:
        console.print(f"[bold red]Error loading portfolio:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())
