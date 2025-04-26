# Folio CLI MVP Plan (v2)

## Project Checklist

### Phase 1: Basic Interactive Shell
- [x] Set up project structure
- [x] Install dependencies (prompt_toolkit, rich)
- [x] Create basic REPL shell with command history
- [x] Implement portfolio loading functionality
- [x] Port basic SPY simulation command
- [x] Add help and exit commands

### Phase 2: Enhanced Interactivity
- [x] Implement position-specific analysis
- [x] Add ticker filtering capability
- [x] Create state management between commands
- [x] Implement parameter customization
- [x] Add detailed position breakdowns

### Phase 3: Additional Commands and Polish
- [ ] Add portfolio summary command
- [ ] Implement "what-if" scenario analysis
- [ ] Add comprehensive help text
- [ ] Improve error handling
- [ ] Add command auto-completion
- [ ] Create tests for core functionality

## Overview

The Folio CLI MVP will create an interactive shell-like environment that leverages the existing portfolio simulation and analysis capabilities in the Folio codebase. This approach will allow users to run simulations, explore different options, and analyze portfolio data through an interactive command-line interface.

## Goals

1. Create an interactive shell for portfolio simulation and analysis
2. Reuse existing code from `src/folio` modules
3. Provide at least the same functionality as `scripts/folio-simulator.py`
4. Allow users to run multiple commands without restarting the application
5. Support detailed analysis of specific position groups

## Technology Selection

After analyzing the codebase and evaluating different options, we recommend:

### Primary Framework: Prompt Toolkit + Typer

**[Python Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/)** is ideal for our interactive shell requirements:
- Designed specifically for building interactive command-line applications
- Built-in support for REPL (Read-Eval-Print Loop) interfaces
- Excellent auto-completion capabilities
- History navigation and search
- Customizable key bindings

**[Typer](https://typer.tiangolo.com/)** will be used for command parsing within the shell:
- Modern API with type hints
- Built on Click, inheriting its stability
- Excellent documentation and growing community

**[Rich](https://rich.readthedocs.io/)** will continue to be used for output formatting:
- Already used in the existing simulator
- Excellent for tables, charts, and formatted text
- Good integration with both Prompt Toolkit and Typer

## Implementation Plan

### Phase 1: Basic Interactive Shell (1 week)

#### Tasks
- [ ] **1.1 Set up project structure**
  - Create directory structure
  - Set up package files
  - Configure dependencies

- [ ] **1.2 Create Shell Framework**
  - Set up a basic REPL using Prompt Toolkit
  - Implement command history and navigation
  - Add basic auto-completion for commands

- [ ] **1.3 Implement Portfolio Loading**
  - Create portfolio loading function
  - Add error handling for missing files
  - Implement portfolio reloading command

- [ ] **1.4 Port Core Simulator Commands**
  - Directly use `simulate_portfolio_with_spy_changes` from `src/folio/simulator.py`
  - Reuse the portfolio loading code from `src/folio/portfolio.py`
  - Maintain the same output formatting using Rich

- [ ] **1.5 Add Basic Help System**
  - Implement help command
  - Add command documentation
  - Create exit command with confirmation

#### Deliverables
- Working REPL shell
- Basic simulation command
- Portfolio loading functionality
- Help and exit commands

### Phase 2: Enhanced Interactivity (1 week)

#### Tasks
- [ ] **2.1 Add Position-Specific Analysis**
  - Implement commands to analyze specific position groups
  - Create detailed position view
  - Add option chain visualization

- [ ] **2.2 Implement Filtering Capabilities**
  - Allow filtering by ticker
  - Add sorting options
  - Implement focus mode for specific tickers

- [ ] **2.3 Create State Management**
  - Allow referencing previous simulation results
  - Maintain portfolio state between commands
  - Implement session history

- [ ] **2.4 Add Parameter Customization**
  - Add ability to modify simulation parameters incrementally
  - Create parameter presets
  - Implement parameter validation

#### Deliverables
- Position analysis commands
- Filtering and sorting capabilities
- State management between commands
- Parameter customization options

### Phase 3: Additional Commands and Polish (1 week)

#### Tasks
- [ ] **3.1 Add Supplementary Commands**
  - Portfolio viewing and basic analysis
  - "What-if" scenario analysis
  - Portfolio comparison tools

- [ ] **3.2 Enhance Command Completion**
  - Add context-aware command completion
  - Implement parameter suggestions
  - Create command aliases

- [ ] **3.3 Improve Error Handling**
  - Add comprehensive error messages
  - Implement error recovery
  - Create debugging commands

- [ ] **3.4 Add Testing and Documentation**
  - Write unit tests for core functionality
  - Create integration tests
  - Add comprehensive help text
  - Create user documentation

#### Deliverables
- Additional analysis commands
- Enhanced command completion
- Robust error handling
- Comprehensive tests and documentation

## Implementation Details

### Project Structure

```
src/
└── focli/
    ├── __init__.py         # Package initialization
    ├── shell.py            # Interactive shell implementation
    ├── commands/           # Command implementations
    │   ├── __init__.py     # Command registration
    │   ├── simulate.py     # Simulation commands
    │   ├── position.py     # Position analysis commands
    │   └── portfolio.py    # Portfolio management commands
    ├── formatters.py       # Output formatting utilities
    └── utils.py            # Utility functions
```

#### Key Files and Their Responsibilities

- **`shell.py`**: Main entry point, REPL implementation, command routing
- **`commands/__init__.py`**: Command registration and discovery
- **`commands/simulate.py`**: Portfolio simulation commands
- **`commands/position.py`**: Position-specific analysis
- **`commands/portfolio.py`**: Portfolio management and overview
- **`formatters.py`**: Rich formatting for tables, charts, and text
- **`utils.py`**: Helper functions and utilities

### Code Reuse Strategy

The implementation will directly leverage the following existing modules:

1. **`src/folio/simulator.py`**
   - `simulate_portfolio_with_spy_changes`: Core simulation function
   - `calculate_percentage_changes`: Utility for calculating changes

2. **`src/folio/portfolio.py`**
   - `process_portfolio_data`: Load and process portfolio data
   - `recalculate_portfolio_with_prices`: Recalculate with price changes
   - `calculate_portfolio_summary`: Generate portfolio summaries

3. **`src/folio/data_model.py`**
   - Data classes for portfolio representation
   - Conversion methods between objects and dictionaries

4. **`src/folio/formatting.py`**
   - Formatting utilities for currency and percentages

### Implementation Approach

#### 1. Interactive Shell Implementation

The interactive shell will be implemented using Prompt Toolkit's REPL capabilities:

```python
# src/focli/shell.py
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from rich.console import Console

from src.folio.portfolio import process_portfolio_data
from src.focli.commands import get_command_registry, execute_command

console = Console()

def create_completer():
    """Create a nested completer for command auto-completion."""
    # Build a nested completer from the command registry
    commands = get_command_registry()

    # Create completion dictionary with subcommands and parameters
    completion_dict = {}
    for cmd_name, cmd_info in commands.items():
        if cmd_info.get("subcommands"):
            completion_dict[cmd_name] = {
                subcmd: None for subcmd in cmd_info["subcommands"]
            }
        else:
            completion_dict[cmd_name] = None

    return NestedCompleter.from_nested_dict(completion_dict)

def main():
    """Main entry point for the Folio CLI."""
    console.print("[bold]Folio Interactive Shell[/bold]")
    console.print("Type 'help' for available commands.")

    # Create session with auto-completion
    session = PromptSession(completer=create_completer())

    # Initialize application state
    state = {
        "portfolio_groups": None,
        "portfolio_summary": None,
        "last_simulation": None,
        "loaded_portfolio": None,
    }

    # Try to load default portfolio
    try:
        load_portfolio("private-data/portfolio-private.csv", state)
    except Exception as e:
        console.print(f"[yellow]Could not load default portfolio: {e}[/yellow]")
        console.print("[yellow]Use 'load <path>' to load a portfolio.[/yellow]")

    # Main REPL loop
    while True:
        try:
            # Get user input
            text = session.prompt("folio> ")

            if not text.strip():
                continue

            # Handle exit command directly
            if text.strip().lower() == "exit":
                if confirm_exit():
                    break
                continue

            # Process the command
            execute_command(text, state, console)

        except KeyboardInterrupt:
            # Handle Ctrl+C
            console.print("\n[yellow]Use 'exit' to exit the application.[/yellow]")
            continue
        except EOFError:
            # Handle Ctrl+D
            console.print("\nGoodbye!")
            break
        except Exception as e:
            # Handle unexpected errors
            console.print(f"[bold red]Error:[/bold red] {str(e)}")

    console.print("Goodbye!")

def load_portfolio(path, state):
    """Load a portfolio from a CSV file."""
    import pandas as pd
    from src.folio.portfolio import process_portfolio_data

    df = pd.read_csv(path)
    groups, summary, _ = process_portfolio_data(df, update_prices=True)

    state["portfolio_groups"] = groups
    state["portfolio_summary"] = summary
    state["loaded_portfolio"] = path

    return groups, summary

def confirm_exit():
    """Confirm exit with the user."""
    from prompt_toolkit.shortcuts import confirm

    return confirm("Are you sure you want to exit?")

if __name__ == "__main__":
    main()
```

#### 2. Command Registration and Execution

Commands will be registered and executed through a central registry:

```python
# src/focli/commands/__init__.py
from typing import Dict, Any, Callable, List

# Command registry
_COMMANDS = {}

def register_command(name: str, handler: Callable, help_text: str, subcommands: List[str] = None):
    """Register a command with the command registry."""
    _COMMANDS[name] = {
        "handler": handler,
        "help": help_text,
        "subcommands": subcommands,
    }

def get_command_registry():
    """Get the command registry."""
    return _COMMANDS

def execute_command(command_line: str, state: Dict[str, Any], console):
    """Execute a command from the command line."""
    # Parse the command line
    parts = command_line.strip().split()
    if not parts:
        return

    command = parts[0].lower()
    args = parts[1:]

    # Check if the command exists
    if command not in _COMMANDS:
        console.print(f"[bold red]Unknown command:[/bold red] {command}")
        console.print("Type 'help' to see available commands.")
        return

    # Execute the command
    try:
        _COMMANDS[command]["handler"](args, state, console)
    except Exception as e:
        console.print(f"[bold red]Error executing command '{command}':[/bold red] {str(e)}")

# Import and register commands
from .simulate import simulate_command
from .position import position_command
from .portfolio import portfolio_command
from .help import help_command

# Register commands
register_command("simulate", simulate_command, "Simulate portfolio performance with SPY changes",
                ["spy", "scenario"])
register_command("position", position_command, "Analyze a specific position group")
register_command("portfolio", portfolio_command, "View and analyze portfolio",
                ["list", "summary", "load"])
register_command("help", help_command, "Show help information")
```

#### 3. Simulation Command Implementation

The simulation command will directly use the existing simulator functionality:

```python
# src/focli/commands/simulate.py
from typing import Dict, Any, List
import numpy as np

from src.folio.simulator import simulate_portfolio_with_spy_changes
from src.focli.formatters import display_simulation_results

def simulate_command(args: List[str], state: Dict[str, Any], console):
    """Simulate portfolio performance with SPY changes."""
    # Check if a portfolio is loaded
    if not state.get("portfolio_groups"):
        console.print("[bold red]Error:[/bold red] No portfolio loaded.")
        console.print("Use 'portfolio load <path>' to load a portfolio.")
        return

    # Default parameters
    range_pct = 20.0
    steps = 13
    focus_tickers = None
    detailed = False

    # Parse arguments
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "spy":
            # This is the default simulation type
            i += 1
            continue

        elif arg == "--range" or arg == "-r":
            if i + 1 < len(args):
                try:
                    range_pct = float(args[i + 1])
                    i += 2
                    continue
                except ValueError:
                    console.print(f"[bold red]Invalid range value:[/bold red] {args[i + 1]}")
                    return
            else:
                console.print("[bold red]Missing value for --range[/bold red]")
                return

        elif arg == "--steps" or arg == "-s":
            if i + 1 < len(args):
                try:
                    steps = int(args[i + 1])
                    i += 2
                    continue
                except ValueError:
                    console.print(f"[bold red]Invalid steps value:[/bold red] {args[i + 1]}")
                    return
            else:
                console.print("[bold red]Missing value for --steps[/bold red]")
                return

        elif arg == "--focus" or arg == "-f":
            if i + 1 < len(args):
                focus_tickers = [t.strip().upper() for t in args[i + 1].split(",")]
                i += 2
                continue
            else:
                console.print("[bold red]Missing value for --focus[/bold red]")
                return

        elif arg == "--detailed" or arg == "-d":
            detailed = True
            i += 1
            continue

        else:
            console.print(f"[bold red]Unknown argument:[/bold red] {arg}")
            return

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

    # Run the simulation
    console.print(f"[bold]Running simulation with range ±{range_pct}% and {steps} steps...[/bold]")

    results = simulate_portfolio_with_spy_changes(
        portfolio_groups=state["portfolio_groups"],
        spy_changes=spy_changes,
        cash_like_positions=state["portfolio_summary"].cash_like_positions,
        pending_activity_value=state["portfolio_summary"].pending_activity_value,
    )

    # Store results for future reference
    state["last_simulation"] = results

    # Display the results
    display_simulation_results(results, detailed, focus_tickers, console)
```

#### 4. Formatters Implementation

The display functions will reuse the formatting from the existing simulator script:

```python
# src/focli/formatters.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED

from src.folio.formatting import format_currency

def display_simulation_results(results, detailed=False, focus_tickers=None, console=None):
    """Display simulation results using Rich."""
    if console is None:
        console = Console()

    # Get the current value (at 0% SPY change)
    current_value = results["current_value"]

    # Get min and max values
    min_value = min(results["portfolio_values"])
    max_value = max(results["portfolio_values"])
    min_index = results["portfolio_values"].index(min_value)
    max_index = results["portfolio_values"].index(max_value)
    min_spy_change = results["spy_changes"][min_index] * 100  # Convert to percentage
    max_spy_change = results["spy_changes"][max_index] * 100  # Convert to percentage

    # Create a summary table
    console.print("\n[bold cyan]Portfolio Simulation Results[/bold cyan]")

    summary_table = Table(title="Portfolio Summary", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_column("SPY Change", style="yellow")

    summary_table.add_row("Current Value", f"${current_value:,.2f}", "0.0%")
    summary_table.add_row("Minimum Value", f"${min_value:,.2f}", f"{min_spy_change:.1f}%")
    summary_table.add_row("Maximum Value", f"${max_value:,.2f}", f"{max_spy_change:.1f}%")

    console.print(summary_table)

    # Create a detailed table with all values
    value_table = Table(title="Portfolio Values at Different SPY Changes", box=ROUNDED)
    value_table.add_column("SPY Change", style="yellow")
    value_table.add_column("Portfolio Value", style="green")
    value_table.add_column("Change", style="cyan")
    value_table.add_column("% Change", style="magenta")

    for i, spy_change in enumerate(results["spy_changes"]):
        portfolio_value = results["portfolio_values"][i]
        value_change = portfolio_value - current_value
        pct_change = (value_change / current_value) * 100 if current_value != 0 else 0

        # Format the change with color based on positive/negative
        change_str = f"${value_change:+,.2f}"
        pct_change_str = f"{pct_change:+.2f}%"

        value_table.add_row(
            f"{spy_change * 100:.1f}%",
            f"${portfolio_value:,.2f}",
            change_str,
            pct_change_str,
        )

    console.print(value_table)

    # If detailed is True, show position-level analysis
    if detailed:
        display_position_analysis(results, focus_tickers, console)

def display_position_analysis(results, focus_tickers=None, console=None):
    """Display position-level analysis."""
    if console is None:
        console = Console()

    # Get position details
    position_details = results.get("position_details", {})
    position_changes = results.get("position_changes", {})

    # Filter positions if focus_tickers is provided
    if focus_tickers:
        filtered_details = {}
        filtered_changes = {}
        for ticker in focus_tickers:
            if ticker in position_details:
                filtered_details[ticker] = position_details[ticker]
            if ticker in position_changes:
                filtered_changes[ticker] = position_changes[ticker]
        position_details = filtered_details
        position_changes = filtered_changes

    # Display position details
    console.print("\n[bold cyan]Position Analysis[/bold cyan]")

    for ticker, details in position_details.items():
        # Create a panel for each position
        position_table = Table(title=f"{ticker} Details", box=ROUNDED)
        position_table.add_column("Metric", style="cyan")
        position_table.add_column("Value", style="green")

        # Add basic position details
        position_table.add_row("Beta", f"{details.get('beta', 0):.2f}")
        position_table.add_row("Current Value", format_currency(details.get('current_value', 0)))
        position_table.add_row("Stock Value", format_currency(details.get('stock_value', 0)))
        position_table.add_row("Option Value", format_currency(details.get('option_value', 0)))

        # Add stock details if available
        if details.get('has_stock'):
            position_table.add_row("Stock Quantity", f"{details.get('stock_quantity', 0)}")
            position_table.add_row("Stock Price", format_currency(details.get('stock_price', 0)))

        # Add option details if available
        if details.get('has_options'):
            position_table.add_row("Option Count", f"{details.get('option_count', 0)}")

        console.print(position_table)

        # If we have change data, show it
        if ticker in position_changes:
            changes = position_changes[ticker]

            # Create a table for position changes
            changes_table = Table(title=f"{ticker} Changes with SPY", box=ROUNDED)
            changes_table.add_column("SPY Change", style="yellow")
            changes_table.add_column("Position Value", style="green")
            changes_table.add_column("Change", style="cyan")
            changes_table.add_column("% Change", style="magenta")

            for i, spy_change in enumerate(results["spy_changes"]):
                if i < len(changes["values"]):
                    value = changes["values"][i]
                    change = changes["changes"][i]
                    pct_change = changes["pct_changes"][i]

                    changes_table.add_row(
                        f"{spy_change * 100:.1f}%",
                        format_currency(value),
                        f"{format_currency(change, include_sign=True)}",
                        f"{pct_change:+.2f}%",
                    )

            console.print(changes_table)

def display_position_details(group, detailed=True, console=None):
    """Display detailed information about a position group."""
    if console is None:
        console = Console()

    ticker = group.ticker
    console.print(f"\n[bold cyan]Position Details: {ticker}[/bold cyan]")

    # Create a summary table
    summary_table = Table(title=f"{ticker} Summary", box=ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    # Add basic position details
    summary_table.add_row("Beta", f"{group.beta:.2f}")
    summary_table.add_row("Net Exposure", format_currency(group.net_exposure))
    summary_table.add_row("Beta-Adjusted Exposure", format_currency(group.beta_adjusted_exposure))

    # Add stock details if available
    if group.stock_position:
        stock = group.stock_position
        summary_table.add_row("Stock Quantity", f"{stock.quantity}")
        summary_table.add_row("Stock Price", format_currency(stock.price))
        summary_table.add_row("Stock Market Value", format_currency(stock.market_value))

    # Add option summary if available
    if group.option_positions:
        summary_table.add_row("Option Count", f"{len(group.option_positions)}")
        summary_table.add_row("Call Options", f"{group.call_count}")
        summary_table.add_row("Put Options", f"{group.put_count}")
        summary_table.add_row("Total Delta Exposure", format_currency(group.total_delta_exposure))

    console.print(summary_table)

    # If detailed and we have options, show option details
    if detailed and group.option_positions:
        options_table = Table(title=f"{ticker} Option Positions", box=ROUNDED)
        options_table.add_column("Type", style="cyan")
        options_table.add_column("Strike", style="green", justify="right")
        options_table.add_column("Expiry", style="yellow")
        options_table.add_column("Quantity", style="green", justify="right")
        options_table.add_column("Delta", style="magenta", justify="right")
        options_table.add_column("Value", style="green", justify="right")

        for option in group.option_positions:
            options_table.add_row(
                option.option_type,
                format_currency(option.strike),
                option.expiry,
                f"{option.quantity}",
                f"{option.delta:.2f}",
                format_currency(option.market_value),
            )

        console.print(options_table)
```

## Future Extensibility

While keeping the MVP simple, we'll ensure future extensibility by:

1. **Modular Design**
   - Separate command processing from execution
   - Use clear interfaces between components

2. **Extensible Command Structure**
   - Design for easy addition of new commands
   - Allow for command hierarchies in the future

3. **State Management**
   - Implement a simple state manager that can be expanded
   - Allow for saving and loading state

4. **Documentation**
   - Document extension points
   - Create clear examples for adding new commands

## Implementation Roadmap

### Week 1: Basic Interactive Shell
1. **Day 1-2**: Set up project structure and implement shell framework
   - Create directory structure
   - Implement basic REPL with command history
   - Set up command registration system

2. **Day 3-4**: Implement portfolio loading and basic commands
   - Create portfolio loading functionality
   - Implement help command
   - Add exit command with confirmation

3. **Day 5**: Port core simulator command
   - Implement SPY simulation command
   - Create basic formatters for simulation results
   - Test with sample portfolio

### Week 2: Enhanced Interactivity
1. **Day 1-2**: Implement position-specific analysis
   - Create position command
   - Implement detailed position view
   - Add option chain visualization

2. **Day 3-4**: Add filtering and state management
   - Implement ticker filtering
   - Create state management between commands
   - Add parameter customization

3. **Day 5**: Testing and refinement
   - Test with various portfolios
   - Refine error handling
   - Improve user feedback

### Week 3: Additional Commands and Polish
1. **Day 1-2**: Add supplementary commands
   - Implement portfolio summary command
   - Add "what-if" scenario analysis
   - Create portfolio comparison tools

2. **Day 3-4**: Enhance command completion and documentation
   - Implement context-aware command completion
   - Add comprehensive help text
   - Create user documentation

3. **Day 5**: Final testing and packaging
   - Write unit tests
   - Create integration tests
   - Package for distribution

## Conclusion

This MVP approach focuses on creating a simple but effective interactive shell for Folio portfolio analysis. By directly leveraging the existing codebase, we can quickly create a working product that provides immediate value while setting the foundation for future enhancements.

The interactive shell will allow users to run multiple simulations, explore different options, and analyze portfolio data without restarting the application, significantly improving the user experience compared to the current script-based approach.

By following the phased implementation plan and detailed roadmap, we can ensure a systematic approach to development, with clear milestones and deliverables at each stage. The modular design will facilitate future extensions and enhancements as user needs evolve.
