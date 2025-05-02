"""
Position analysis commands for the Folio CLI.

This module provides commands for analyzing specific position groups.
"""

from typing import Any

from src.focli.formatters import (
    display_position_details,
    display_position_risk_analysis,
    display_position_simulation,
)
from src.focli.utils import find_position_group, find_positions_by_ticker, parse_args
from src.folio.simulator import generate_spy_changes, simulate_position_with_spy_changes


def position_command(args: list[str], state: dict[str, Any], console):
    """Analyze a specific position group.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio_groups") and not state.get("portfolio"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Check if we have a ticker
    if not args:
        console.print("[bold yellow]Usage:[/bold yellow] position <ticker> [options]")
        console.print("Type 'help position' for more information.")
        return

    # Get the ticker
    ticker = args[0].upper()

    # Check if we have a subcommand
    if len(args) > 1 and args[1] in ["details", "risk", "simulate"]:
        subcommand = args[1]
        position_args = args[2:]

        if subcommand == "details":
            position_details(ticker, position_args, state, console)
        elif subcommand == "risk":
            position_risk(ticker, position_args, state, console)
        elif subcommand == "simulate":
            position_simulate(ticker, position_args, state, console)
    else:
        # Default to details
        position_args = args[1:]
        position_details(ticker, position_args, state, console)


def position_details(ticker: str, args: list[str], state: dict[str, Any], console):
    """Show detailed information about a position.

    Args:
        ticker: Ticker symbol
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        "detailed": {
            "type": bool,
            "default": True,
            "help": "Show detailed information",
            "aliases": ["-d", "--detailed", "--no-detailed"],
        }
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)
        detailed = parsed_args["detailed"]

        # Check if we have the new folib Portfolio object
        if state.get("portfolio"):
            # Find positions using the new folib function
            positions = find_positions_by_ticker(ticker, state["portfolio"])

            if not positions["stock_position"] and not positions["option_positions"]:
                # Try the old method as fallback
                group = find_position_group(ticker, state["portfolio_groups"])
                if not group:
                    console.print(f"[bold red]Position not found:[/bold red] {ticker}")
                    return

                # Display using the old method
                display_position_details(group, detailed, console)

                # Store the last viewed position in state
                state["last_position"] = group
            else:
                # Use the position service to analyze the positions
                from src.folib.data.stock import stockdata
                from src.folib.services.position_service import analyze_position

                position_analyses = []

                try:
                    if positions["stock_position"]:
                        stock_analysis = analyze_position(
                            positions["stock_position"], stockdata
                        )
                        position_analyses.append(stock_analysis)

                    for option_position in positions["option_positions"]:
                        try:
                            option_analysis = analyze_position(
                                option_position, stockdata
                            )
                            position_analyses.append(option_analysis)
                        except AttributeError as e:
                            # Handle missing get_volatility method
                            if "get_volatility" in str(e):
                                # Create a simplified analysis without volatility
                                option_analysis = {
                                    "type": "option",
                                    "ticker": option_position.ticker,
                                    "market_value": option_position.market_value,
                                    "beta": stockdata.get_beta(option_position.ticker),
                                    "exposure": option_position.market_value,
                                    "beta_adjusted_exposure": option_position.market_value
                                    * stockdata.get_beta(option_position.ticker),
                                    "delta": 0.5,  # Default delta as a placeholder
                                    "option_type": option_position.option_type,
                                    "strike": option_position.strike,
                                    "expiry": option_position.expiry,
                                    "quantity": option_position.quantity,
                                }
                                position_analyses.append(option_analysis)
                            else:
                                raise
                except Exception as e:
                    console.print(
                        f"[bold yellow]Warning:[/bold yellow] Error analyzing positions: {e}"
                    )
                    console.print("Falling back to legacy display method.")

                # For now, use the old display function
                # In the future, we'll create a new display function for folib data

                # Find the position group using the old method for backward compatibility
                group = find_position_group(ticker, state["portfolio_groups"])
                if group:
                    display_position_details(group, detailed, console)
                    state["last_position"] = group
                else:
                    console.print(
                        f"[bold yellow]Warning:[/bold yellow] Using legacy display for {ticker}"
                    )
                    # Create a simple display for the position
                    console.print(
                        f"\n[bold cyan]Position Details: {ticker}[/bold cyan]"
                    )

                    for analysis in position_analyses:
                        console.print(f"Type: {analysis['type']}")
                        console.print(f"Market Value: ${analysis['market_value']:,.2f}")
                        console.print(f"Beta: {analysis['beta']:.2f}")
                        console.print(f"Exposure: ${analysis['exposure']:,.2f}")
                        console.print(
                            f"Beta-Adjusted Exposure: ${analysis['beta_adjusted_exposure']:,.2f}"
                        )

                        if analysis["type"] == "option":
                            console.print(f"Delta: {analysis['delta']:.4f}")

                        if analysis.get("unrealized_pnl") is not None:
                            console.print(
                                f"Unrealized P&L: ${analysis['unrealized_pnl']:,.2f}"
                            )

                        console.print("")
        else:
            # Use the old method
            group = find_position_group(ticker, state["portfolio_groups"])

            if not group:
                console.print(f"[bold red]Position not found:[/bold red] {ticker}")
                return

            # Display detailed position information
            display_position_details(group, detailed, console)

            # Store the last viewed position in state
            state["last_position"] = group

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error analyzing position:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())


def position_risk(ticker: str, args: list[str], state: dict[str, Any], console):
    """Show risk analysis for a position.

    Args:
        ticker: Ticker symbol
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        "detailed": {
            "type": bool,
            "default": False,
            "help": "Show detailed information",
            "aliases": ["-d", "--detailed"],
        }
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)
        detailed = parsed_args["detailed"]

        # Check if we have the new folib Portfolio object
        if state.get("portfolio"):
            # Find positions using the new folib function
            positions = find_positions_by_ticker(ticker, state["portfolio"])

            if not positions["stock_position"] and not positions["option_positions"]:
                # Try the old method as fallback
                group = find_position_group(ticker, state["portfolio_groups"])
                if not group:
                    console.print(f"[bold red]Position not found:[/bold red] {ticker}")
                    return

                # Display using the old method
                display_position_risk_analysis(group, detailed, console)

                # Store the last viewed position in state
                state["last_position"] = group
            else:
                # For now, use the old display function
                # In the future, we'll create a new display function for folib data

                # Find the position group using the old method for backward compatibility
                group = find_position_group(ticker, state["portfolio_groups"])
                if group:
                    display_position_risk_analysis(group, detailed, console)
                    state["last_position"] = group
                else:
                    console.print(
                        f"[bold yellow]Warning:[/bold yellow] Using legacy risk display for {ticker}"
                    )
                    # Use the position service to analyze the positions
                    from src.folib.data.stock import stockdata
                    from src.folib.services.position_service import analyze_position

                    position_analyses = []

                    try:
                        if positions["stock_position"]:
                            stock_analysis = analyze_position(
                                positions["stock_position"], stockdata
                            )
                            position_analyses.append(stock_analysis)

                        for option_position in positions["option_positions"]:
                            try:
                                option_analysis = analyze_position(
                                    option_position, stockdata
                                )
                                position_analyses.append(option_analysis)
                            except AttributeError as e:
                                # Handle missing get_volatility method
                                if "get_volatility" in str(e):
                                    # Create a simplified analysis without volatility
                                    option_analysis = {
                                        "type": "option",
                                        "ticker": option_position.ticker,
                                        "market_value": option_position.market_value,
                                        "beta": stockdata.get_beta(
                                            option_position.ticker
                                        ),
                                        "exposure": option_position.market_value,
                                        "beta_adjusted_exposure": option_position.market_value
                                        * stockdata.get_beta(option_position.ticker),
                                        "delta": 0.5,  # Default delta as a placeholder
                                        "option_type": option_position.option_type,
                                        "strike": option_position.strike,
                                        "expiry": option_position.expiry,
                                        "quantity": option_position.quantity,
                                    }
                                    position_analyses.append(option_analysis)
                                else:
                                    raise
                    except Exception as e:
                        console.print(
                            f"[bold yellow]Warning:[/bold yellow] Error analyzing positions: {e}"
                        )
                        console.print("Falling back to legacy display method.")

                    # Create a simple display for the position risk
                    console.print(
                        f"\n[bold cyan]Position Risk Analysis: {ticker}[/bold cyan]"
                    )

                    for analysis in position_analyses:
                        console.print(f"Type: {analysis['type']}")
                        console.print(f"Beta: {analysis['beta']:.2f}")
                        console.print(f"Exposure: ${analysis['exposure']:,.2f}")
                        console.print(
                            f"Beta-Adjusted Exposure: ${analysis['beta_adjusted_exposure']:,.2f}"
                        )

                        if analysis["type"] == "option":
                            console.print(f"Delta: {analysis['delta']:.4f}")

                        console.print("")
        else:
            # Use the old method
            group = find_position_group(ticker, state["portfolio_groups"])

            if not group:
                console.print(f"[bold red]Position not found:[/bold red] {ticker}")
                return

            # Display risk analysis
            display_position_risk_analysis(group, detailed, console)

            # Store the last viewed position in state
            state["last_position"] = group

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error analyzing position risk:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())


def position_simulate(ticker: str, args: list[str], state: dict[str, Any], console):
    """Simulate a position with SPY changes.

    Args:
        ticker: Ticker symbol
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Define argument specifications
    arg_specs = {
        "range": {
            "type": float,
            "default": 20.0,
            "help": "SPY change range in percent",
            "aliases": ["-r", "--range"],
        },
        "steps": {
            "type": int,
            "default": 13,
            "help": "Number of steps in the simulation",
            "aliases": ["-s", "--steps"],
        },
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)
        range_pct = parsed_args["range"]
        steps = parsed_args["steps"]

        # For simulation, we'll continue to use the old method for now
        # The simulation service will be implemented in a future phase

        # Find the position group
        group = find_position_group(ticker, state["portfolio_groups"])

        if not group:
            # If not found in portfolio_groups, check if we have a folib Portfolio
            if state.get("portfolio"):
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Simulation using folib is not yet implemented."
                )
                console.print("Using legacy portfolio groups for simulation.")

                # Try to find the position in the folib Portfolio
                positions = find_positions_by_ticker(ticker, state["portfolio"])
                if positions["stock_position"] or positions["option_positions"]:
                    console.print(
                        f"[bold yellow]Position {ticker} found in folib Portfolio but cannot be simulated yet.[/bold yellow]"
                    )
                    console.print(
                        "Simulation service will be implemented in a future phase."
                    )
                    return

            console.print(f"[bold red]Position not found:[/bold red] {ticker}")
            return

        # Generate SPY changes
        spy_changes = generate_spy_changes(range_pct, steps)

        # Run the simulation
        console.print(
            f"[bold]Simulating {ticker} with SPY range ±{range_pct}% and {steps} steps...[/bold]"
        )

        # Simulate the position
        results = simulate_position_with_spy_changes(group, spy_changes)

        # Store results in state
        if "position_simulations" not in state:
            state["position_simulations"] = {}
        state["position_simulations"][ticker] = results
        state["last_position"] = group

        # Display the results
        display_position_simulation(results, console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error simulating position:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())
