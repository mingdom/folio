"""
Simulation commands for the Folio CLI.

This module provides commands for simulating portfolio performance under different scenarios.
"""

import copy
from typing import Any

from src.focli.formatters import display_simulation_results
from src.focli.utils import filter_portfolio_groups, parse_args
from src.folio.simulator import (
    generate_spy_changes,
    simulate_portfolio_with_spy_changes,
)


def simulate_command(args: list[str], state: dict[str, Any], console):
    """Simulate portfolio performance with SPY changes.

    Args:
        args: Command arguments
        state: Application state
        console: Rich console for output
    """
    # Check if a portfolio is loaded
    if not state.get("portfolio_groups"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Check if we have a subcommand or arguments
    if not args:
        # Default to SPY simulation with default parameters
        simulate_spy([], state, console)
        return

    # Check if the first argument is a subcommand
    first_arg = args[0].lower()
    if first_arg in ["spy", "scenario"]:
        # It's a subcommand
        subcommand = first_arg
        subcommand_args = args[1:]

        if subcommand == "spy":
            simulate_spy(subcommand_args, state, console)
        elif subcommand == "scenario":
            console.print(
                "[bold yellow]Note:[/bold yellow] Scenario simulation is not yet implemented."
            )
    else:
        # No subcommand specified, assume SPY simulation with the provided arguments
        simulate_spy(args, state, console)


def simulate_spy(args: list[str], state: dict[str, Any], console):
    """Simulate portfolio performance with SPY changes.

    Args:
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
        "focus": {
            "type": str,
            "default": None,
            "help": "Comma-separated list of tickers to focus on",
            "aliases": ["-f", "--focus"],
        },
        "detailed": {
            "type": bool,
            "default": False,
            "help": "Show detailed analysis for all positions",
            "aliases": ["-d", "--detailed"],
        },
        "preset": {
            "type": str,
            "default": None,
            "help": "Use a parameter preset (default, detailed, quick)",
            "aliases": ["-p", "--preset"],
        },
        "save_preset": {
            "type": str,
            "default": None,
            "help": "Save current parameters as a preset",
            "aliases": ["--save-preset"],
        },
        "filter": {
            "type": str,
            "default": None,
            "help": "Filter positions by type (options, stocks)",
            "aliases": ["--filter"],
        },
        "min_value": {
            "type": float,
            "default": None,
            "help": "Minimum position value to include",
            "aliases": ["--min-value"],
        },
        "max_value": {
            "type": float,
            "default": None,
            "help": "Maximum position value to include",
            "aliases": ["--max-value"],
        },
    }

    try:
        # Parse arguments
        parsed_args = parse_args(args, arg_specs)

        # Check if we're using a preset
        if parsed_args["preset"]:
            preset_name = parsed_args["preset"].lower()
            if preset_name in state["simulation_presets"]:
                # Load preset parameters
                preset = state["simulation_presets"][preset_name]
                console.print(f"[bold]Using preset:[/bold] {preset_name}")

                # Apply preset parameters (only if not explicitly specified)
                for key, value in preset.items():
                    if key not in parsed_args or parsed_args[key] is None:
                        parsed_args[key] = value
            else:
                console.print(f"[bold red]Unknown preset:[/bold red] {preset_name}")
                console.print(
                    f"Available presets: {', '.join(state['simulation_presets'].keys())}"
                )
                return

        # Get parameters
        range_pct = parsed_args["range"]
        steps = parsed_args["steps"]
        focus = parsed_args["focus"]
        detailed = parsed_args["detailed"]

        # Save preset if requested
        if parsed_args["save_preset"]:
            preset_name = parsed_args["save_preset"].lower()
            preset = {"range": range_pct, "steps": steps, "detailed": detailed}
            if focus:
                preset["focus"] = focus

            state["simulation_presets"][preset_name] = preset
            console.print(f"[bold green]Saved preset:[/bold green] {preset_name}")

        # Parse focus tickers if provided
        focus_tickers = None
        if focus:
            focus_tickers = [ticker.strip().upper() for ticker in focus.split(",")]

        # Apply filtering if requested
        portfolio_groups = state["portfolio_groups"]
        filter_criteria = {}

        if parsed_args["filter"]:
            filter_type = parsed_args["filter"].lower()
            if filter_type == "options":
                filter_criteria["has_options"] = True
            elif filter_type == "stocks":
                filter_criteria["has_stock"] = True

        if parsed_args["min_value"] is not None:
            filter_criteria["min_value"] = parsed_args["min_value"]

        if parsed_args["max_value"] is not None:
            filter_criteria["max_value"] = parsed_args["max_value"]

        if focus_tickers:
            filter_criteria["tickers"] = focus_tickers

        # Apply filters if any criteria are set
        if filter_criteria:
            filtered_groups = filter_portfolio_groups(portfolio_groups, filter_criteria)

            # Print filter summary
            filter_desc = []
            if filter_criteria.get("tickers"):
                filter_desc.append(f"tickers: {', '.join(filter_criteria['tickers'])}")
            if filter_criteria.get("has_options") is not None:
                filter_desc.append(f"has options: {filter_criteria['has_options']}")
            if filter_criteria.get("has_stock") is not None:
                filter_desc.append(f"has stock: {filter_criteria['has_stock']}")
            if filter_criteria.get("min_value") is not None:
                filter_desc.append(f"min value: ${filter_criteria['min_value']:,.2f}")
            if filter_criteria.get("max_value") is not None:
                filter_desc.append(f"max value: ${filter_criteria['max_value']:,.2f}")

            console.print(f"[italic]Filtered by: {'; '.join(filter_desc)}[/italic]")
            console.print(
                f"[italic]Using {len(filtered_groups)} of {len(portfolio_groups)} positions[/italic]"
            )

            # Use filtered groups for simulation
            portfolio_groups = filtered_groups

            # Store filtered groups in state
            state["filtered_groups"] = filtered_groups

        # Generate SPY changes
        spy_changes = generate_spy_changes(range_pct, steps)

        # Run the simulation
        console.print(
            f"[bold]Running simulation with range ±{range_pct}% and {steps} steps...[/bold]"
        )

        results = simulate_portfolio_with_spy_changes(
            portfolio_groups=portfolio_groups,
            spy_changes=spy_changes,
            cash_like_positions=state["portfolio_summary"].cash_like_positions,
            pending_activity_value=state["portfolio_summary"].pending_activity_value,
        )

        # Store results for future reference
        state["last_simulation"] = results

        # Add to simulation history (keep last 5)
        simulation_copy = copy.deepcopy(results)
        simulation_copy["parameters"] = {
            "range": range_pct,
            "steps": steps,
            "detailed": detailed,
            "focus": focus,
            "timestamp": "now",  # In a real implementation, use actual timestamp
        }
        state["simulation_history"].append(simulation_copy)
        if len(state["simulation_history"]) > 5:
            state["simulation_history"].pop(0)

        # Display the results
        display_simulation_results(results, detailed, focus_tickers, console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error running simulation:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())
