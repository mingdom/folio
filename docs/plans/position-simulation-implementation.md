# Position Simulation Implementation Plan

## Overview

This document provides a detailed implementation plan for updating the position simulation functionality to use the improved `simulator_v2.py` module instead of the old `simulator.py` module. This change is part of the larger effort to completely remove all references to the old simulator.

## Current Implementation

Currently, the position simulation functionality:

1. Uses `simulate_position_with_spy_changes` from `src.folio.simulator`
2. Displays results using `display_position_simulation` from `src.focli.formatters`
3. Shows confusing "Change" and "% Change" columns that don't provide meaningful information

## New Implementation

The new implementation will:

1. Use `simulate_portfolio` from `src.folio.simulator_v2` with a single position group
2. Display results using a new `display_position_simulation_v2` function
3. Show meaningful metrics like portfolio contribution and clear P&L values

## Implementation Steps

### Step 1: Update Imports in position.py

```python
# Old imports
from src.focli.formatters import (
    display_position_details,
    display_position_risk_analysis,
    display_position_simulation,
)
from src.focli.utils import find_position_group, parse_args
from src.folio.simulator import generate_spy_changes, simulate_position_with_spy_changes

# New imports
from src.focli.formatters import (
    display_position_details,
    display_position_risk_analysis,
)
from src.focli.utils import find_position_group, parse_args
from src.folio.simulator_v2 import generate_spy_changes, simulate_portfolio
```

### Step 2: Update the position_simulate Function

```python
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

        # Find the position group
        group = find_position_group(ticker, state["portfolio_groups"])

        if not group:
            console.print(f"[bold red]Position not found:[/bold red] {ticker}")
            return

        # Generate SPY changes
        spy_changes = generate_spy_changes(range_pct, steps)

        # Run the simulation
        console.print(
            f"[bold]Simulating {ticker} with SPY range ±{range_pct}% and {steps} steps...[/bold]"
        )

        # Simulate the position using simulator_v2
        # We use simulate_portfolio with a single position group
        simulation_result = simulate_portfolio(
            portfolio_groups=[group],
            spy_changes=spy_changes,
            cash_value=0.0,  # No cash for position simulation
        )

        # Extract position-specific results
        position_results = simulation_result["position_results"].get(ticker, [])

        # Create a simplified result structure for display
        display_results = {
            "ticker": ticker,
            "beta": group.beta,
            "spy_changes": spy_changes,
            "position_results": position_results,
            "portfolio_value": state["portfolio_summary"].portfolio_estimate_value,
        }

        # Store results in state
        if "position_simulations" not in state:
            state["position_simulations"] = {}
        state["position_simulations"][ticker] = display_results
        state["last_position"] = group

        # Display the results using our custom display function
        display_position_simulation_v2(display_results, console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
    except Exception as e:
        console.print(f"[bold red]Error simulating position:[/bold red] {e!s}")
        import traceback

        console.print(traceback.format_exc())
```

### Step 3: Implement the display_position_simulation_v2 Function

```python
def display_position_simulation_v2(results, console=None):
    """Display position simulation results using simulator_v2 output format.

    Args:
        results: Results from simulate_portfolio for a single position
        console: Rich console for output
    """
    from rich.box import ROUNDED
    from rich.console import Console
    from rich.table import Table
    from src.folio.formatting import format_currency

    if console is None:
        console = Console()

    ticker = results["ticker"]
    beta = results["beta"]
    spy_changes = results["spy_changes"]
    position_results = results["position_results"]
    total_portfolio_value = results["portfolio_value"]

    # Find the baseline (0% change) result
    baseline_index = None
    for i, spy_change in enumerate(spy_changes):
        if abs(spy_change) < 0.001:  # Close to 0%
            baseline_index = i
            break

    if baseline_index is None or not position_results:
        console.print("[yellow]Warning: No baseline (0% SPY change) found in results.[/yellow]")
        return

    # Get the baseline position value
    baseline_result = position_results[baseline_index]
    baseline_value = baseline_result["new_value"]

    # Find min and max values
    values = [result["new_value"] for result in position_results]
    min_value = min(values)
    max_value = max(values)
    min_index = values.index(min_value)
    max_index = values.index(max_value)
    min_spy_change = spy_changes[min_index] * 100  # Convert to percentage
    max_spy_change = spy_changes[max_index] * 100  # Convert to percentage

    console.print(
        f"\n[bold cyan]Position Simulation: {ticker} (Beta: {beta:.2f})[/bold cyan]"
    )

    # Create a summary table
    summary_table = Table(title=f"{ticker} Simulation Summary", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_column("SPY Change", style="yellow")

    summary_table.add_row("Current Value", format_currency(baseline_value), "0.0%")
    summary_table.add_row(
        "Minimum Value",
        format_currency(min_value),
        f"{min_spy_change:.1f}%",
    )
    summary_table.add_row(
        "Maximum Value",
        format_currency(max_value),
        f"{max_spy_change:.1f}%",
    )

    console.print(summary_table)

    # Create a detailed table with all values
    value_table = Table(title=f"{ticker} Values at Different SPY Changes", box=ROUNDED)
    value_table.add_column("SPY Change", style="yellow")
    value_table.add_column("SPY Price", style="blue")
    value_table.add_column("Position Value", style="green")
    value_table.add_column("P&L", style="cyan")
    value_table.add_column("% of Position", style="magenta")
    value_table.add_column("% of Portfolio", style="blue")

    # Get current SPY price (this would come from a real data source in production)
    current_spy_price = 450.0  # Placeholder value

    for i, result in enumerate(position_results):
        spy_change = spy_changes[i]
        value = result["new_value"]
        pnl = result["pnl"]
        pnl_percent = result["pnl_percent"]

        # Calculate SPY price at this change level
        spy_price = current_spy_price * (1 + spy_change)

        # Calculate portfolio contribution
        portfolio_percent = (value / total_portfolio_value) * 100 if total_portfolio_value else 0

        # Format values
        spy_change_str = f"{spy_change * 100:.1f}%"
        spy_price_str = f"${spy_price:.2f}"
        value_str = format_currency(value)
        pnl_str = format_currency(pnl, include_sign=True)
        pnl_percent_str = f"{pnl_percent:+.2f}%"
        portfolio_percent_str = f"{portfolio_percent:.2f}%"

        # Add row with color based on P&L
        pnl_style = "green" if pnl >= 0 else "red"
        value_table.add_row(
            spy_change_str,
            spy_price_str,
            value_str,
            f"[{pnl_style}]{pnl_str}[/{pnl_style}]",
            f"[{pnl_style}]{pnl_percent_str}[/{pnl_style}]",
            portfolio_percent_str,
        )

    console.print(value_table)
```

## Testing Plan

1. **Unit Tests**
   - Update any tests that use the old simulator
   - Add tests for the new implementation

2. **Integration Tests**
   - Test the position simulation with various position types (stock, options, mixed)
   - Test with different SPY change ranges and steps

3. **Manual Testing**
   - Run the `position simulate` command with various tickers
   - Verify that the results are consistent with the portfolio simulation
   - Check that the UI shows meaningful metrics

## Expected Output

The new position simulation output will look like:

```
Position Simulation: SPY (Beta: 1.00)
            SPY Simulation Summary
╭───────────────┬────────────────┬────────────╮
│ Metric        │ Value          │ SPY Change │
├───────────────┼────────────────┼────────────┤
│ Current Value │ $-41,449.36    │ 0.0%       │
│ Minimum Value │ $-305,478.76   │ 20.0%      │
│ Maximum Value │ $222,580.04    │ -20.0%     │
╰───────────────┴────────────────┴────────────╯
            SPY Values at Different SPY Changes
╭────────────┬───────────┬────────────────┬──────────────┬──────────────┬───────────────╮
│ SPY Change │ SPY Price │ Position Value │ P&L          │ % of Position│ % of Portfolio│
├────────────┼───────────┼────────────────┼──────────────┼──────────────┼───────────────┤
│ -20.0%     │ $360.00   │ $222,580.04    │ $+264,029.40 │ +636.75%     │ 2.22%         │
│ -16.7%     │ $375.00   │ $178,575.14    │ $+220,024.50 │ +530.59%     │ 1.79%         │
│ -13.3%     │ $390.00   │ $134,570.24    │ $+176,019.60 │ +424.42%     │ 1.35%         │
│ -10.0%     │ $405.00   │ $90,565.34     │ $+132,014.70 │ +318.26%     │ 0.91%         │
│ -6.7%      │ $420.00   │ $46,560.44     │ $+88,009.80  │ +212.09%     │ 0.47%         │
│ -3.3%      │ $435.00   │ $2,555.54      │ $+44,004.90  │ +105.92%     │ 0.03%         │
│ 0.0%       │ $450.00   │ $-41,449.36    │ $0.00        │ +0.00%       │ -0.41%        │
│ 3.3%       │ $465.00   │ $-85,454.26    │ $-44,004.90  │ -106.17%     │ -0.85%        │
│ 6.7%       │ $480.00   │ $-129,459.16   │ $-88,009.80  │ -212.33%     │ -1.29%        │
│ 10.0%      │ $495.00   │ $-173,464.06   │ $-132,014.70 │ -318.50%     │ -1.73%        │
│ 13.3%      │ $510.00   │ $-217,468.96   │ $-176,019.60 │ -424.66%     │ -2.17%        │
│ 16.7%      │ $525.00   │ $-261,473.86   │ $-220,024.50 │ -530.83%     │ -2.61%        │
│ 20.0%      │ $540.00   │ $-305,478.76   │ $-264,029.40 │ -636.99%     │ -3.05%        │
╰────────────┴───────────┴────────────────┴──────────────┴──────────────┴───────────────╯
```

This output provides:
1. Clear position values at each SPY change level
2. SPY price at each level for context
3. P&L in dollars and percentage
4. Portfolio contribution percentage
5. No confusing "Change" column that doesn't make sense

## Conclusion

This implementation plan provides a detailed roadmap for updating the position simulation functionality to use the improved `simulator_v2.py` module. By following this plan, we will ensure that all simulation functionality in the codebase uses the same underlying calculation logic, providing consistent and accurate results.
