---
last-updated: 2025-05-01
---
## Folio CLI (`focli/`) Detailed Specifications

**1. Target Users & Goals:**

* **Target Users:** Developers, financial analysts, quantitative traders, power users comfortable with command-line interfaces seeking rapid, focused portfolio analysis.
* **Primary Goals:**
    * Load, view, and analyze portfolio composition and performance quickly.
    * Simulate portfolio behavior under various market scenarios (primarily SPY changes).
    * Drill down into specific position details and risk characteristics.
    * Identify key performance drivers and detractors within the portfolio.
    * Integrate analysis into scripts or automated workflows (potential future use).

**2. Core Experience (Interactive Shell):**

* **Startup & Initialization:**
    * Launches via `python src/focli/focli.py` or potentially a build script (`make focli`).
    * Initializes an application state (`state` dictionary) to hold portfolio data, simulation results, history, etc.
    * Attempts to automatically load a default portfolio (e.g., `private-data/portfolio-private.csv`). Reports success or failure.
    * Presents a `folio>` prompt using `prompt_toolkit`.
    * Loads command history from `~/.folio_history`.
* **Command Input & Parsing:**
    * Accepts user input line by line.
    * Provides command auto-completion based on registered commands and subcommands (`NestedCompleter`).
    * Parses commands and arguments (e.g., `portfolio list --options --sort value`).
    * Handles flags (`--detailed`), options with values (`--ticker AAPL`), and positional arguments (`load <path>`).
    * Uses a central command registry (`focli/commands/__init__.py`) to dispatch to appropriate handler functions.
* **State Management:**
    * Maintains the loaded portfolio data (`portfolio_groups`, `portfolio_summary`) in the `state` dictionary.
    * Stores results of recent operations (e.g., `last_simulation`, `last_position`, `filtered_groups`).
    * Manages simulation presets (`simulation_presets`).
    * Keeps a history of executed commands (`command_history`).
* **Output Formatting:**
    * Utilizes the `rich` library for visually appealing and structured output in the terminal.
    * Displays data primarily through formatted tables (`rich.table.Table`) with defined columns, styles, and alignment.
    * Uses color and text styling (bold, italics) to highlight important information (e.g., P&L, errors).
    * Formats currency, percentages, and beta values consistently (`focli/formatters.py`, `folio/formatting.py`).

**3. Command Specifications:**

* **`portfolio`**: View and manage the portfolio.
    * **`portfolio load <path>`**:
        * **Goal:** Load portfolio data into the application state.
        * **Input:** Filesystem path to a portfolio CSV file.
        * **Action:** Reads the CSV, processes it using `folib` (`process_portfolio_data`), updates `state['portfolio_groups']` and `state['portfolio_summary']`. Handles file not found and processing errors.
        * **Output:** Confirmation message or error.
    * **`portfolio summary`** (or just `portfolio`):
        * **Goal:** Display high-level portfolio metrics.
        * **Action:** Reads `state['portfolio_summary']`.
        * **Output:** Displays formatted tables showing Portfolio Overview (Total Value, Stock/Option/Cash Value, Beta, Net Exposure) and Exposure Breakdown (Long, Short, Options, Cash as % of portfolio). Requires portfolio to be loaded.
    * **`portfolio list [options]`**:
        * **Goal:** List positions with filtering and sorting.
        * **Action:** Reads `state['portfolio_groups']`, applies filters and sorting, updates `state['filtered_groups']`.
        * **Options:**
            * `--focus <TICKERS>`: Comma-separated tickers (e.g., `SPY,AAPL`).
            * `--options`: Show only positions containing options.
            * `--stocks`: Show only positions containing stocks.
            * `--min-value <VALUE>`: Filter by minimum position net exposure.
            * `--max-value <VALUE>`: Filter by maximum position net exposure.
            * `--sort <COLUMN>`: Sort by `ticker`, `value` (Net Exposure), `beta`. Default is `ticker`.
        * **Output:** Displays a table listing filtered/sorted positions with columns: Ticker, Beta, Net Exposure, Stock Value, Option Value, Option Count. Shows filter summary if filters applied. Requires portfolio to be loaded.

* **`position <TICKER>`**: Analyze a specific position group.
    * **`position <TICKER> [details] [--detailed]`**:
        * **Goal:** View detailed information about a specific stock/option group.
        * **Action:** Finds the `PortfolioGroup` for the `<TICKER>` in `state['portfolio_groups']`, updates `state['last_position']`.
        * **Options:** `--detailed` shows individual option leg details.
        * **Output:** Displays summary table (Beta, Net Exposure, Stock details) and optionally a detailed options table (Type, Strike, Expiry, Qty, Delta, Value). Requires portfolio to be loaded.
    * **`position <TICKER> risk [--detailed]`**:
        * **Goal:** Analyze the risk metrics of a position group.
        * **Action:** Finds the `PortfolioGroup`, calculates/retrieves risk metrics.
        * **Options:** `--detailed` shows option Greeks (if available - currently placeholders).
        * **Output:** Displays table with Risk Metrics (Beta, Beta-Adjusted Exposure, Option Delta Exposure, Stock Exposure, Option/Stock Ratio). Optionally displays option Greeks table. Requires portfolio to be loaded.
    * **`position <TICKER> simulate [--range <PCT>] [--steps <NUM>]`**:
        * **Goal:** Simulate the P&L of a specific position group under SPY changes.
        * **Action:** Finds the `PortfolioGroup`, runs simulation using `folio/simulator.py`. Stores results in `state['position_simulations']`.
        * **Options:** `--range <PCT>` (default 20), `--steps <NUM>` (default 13).
        * **Output:** Displays summary table (Current Value, Min/Max Value & SPY Change) and a detailed table showing Position Value, Change, % Change for each SPY Change step. Requires portfolio to be loaded.

* **Simulation Commands**: Simulate portfolio performance.
    * **`simulate [options]`** (Older Simulator - `folio/simulator.py`):
        * **Goal:** Simulate the entire (potentially filtered) portfolio against SPY changes.
        * **Action:** Uses `state['portfolio_groups']` (or `state['filtered_groups']`). Calculates portfolio value at different SPY changes. Stores result in `state['last_simulation']`.
        * **Options:** `--range <PCT>`, `--steps <NUM>`, `--focus <TICKERS>`, `--detailed` (shows position-level P&L tables), `--filter [options|stocks]`, `--min-value <VAL>`, `--max-value <VAL>`, `--preset <NAME>`, `--save-preset <NAME>`.
        * **Output:** Displays Portfolio Summary (Current, Min, Max Value) and a table of Portfolio Values/Changes/% Changes at each SPY step. If `--detailed`, also shows P&L tables for focused/filtered positions. Requires portfolio to be loaded.
    * **`sim [options]`** (Newer Simulator - `folio/simulator_v2.py` via `focli/commands/sim.py`):
        * **Goal:** Simulate portfolio performance using the improved V2 simulator with potentially more accurate option pricing.
        * **Action:** Uses `state['portfolio_groups']`. Calls `folio/simulator_v2.py`. Calculates portfolio value and P&L relative to 0% SPY change baseline.
        * **Options:**
            * `--min-spy-change <DECIMAL>` (e.g., -0.2)
            * `--max-spy-change <DECIMAL>` (e.g., 0.2)
            * `--steps <NUM>`
            * `--ticker <TICKER>`: Simulate only for a specific ticker.
            * `--detailed`: Show detailed results for each position group.
            * `--position-type [stock|option]`: Simulate only stock or option components.
            * `--analyze-correlation` or `--analyze`: Analyze how positions perform when SPY increases, identifying negative correlations.
        * **Output:** Displays a table with SPY Change, SPY Price, Portfolio Value, P&L, P&L %, P&L % of Original Value. If `--detailed`, shows tables for individual ticker results. If `--analyze-correlation`, shows analysis table ranking positions by performance during positive SPY changes. Requires portfolio to be loaded.
    * **`analyze <FILE_PATH> [options]`** (`focli/commands/analyze.py` - Standalone Typer App):
        * **Goal:** Perform in-depth analysis of portfolio contributions to P&L across SPY changes, focusing on identifying problematic positions.
        * **Action:** Runs as a separate script invoked via `make analyze` or directly. Loads portfolio from `<FILE_PATH>`. Uses `simulator_v2`. Calculates position contributions to P&L at each SPY step. Identifies key SPY levels (max/min P&L, inflection points, declining in rising market).
        * **Options:** `--min-spy-change`, `--max-spy-change`, `--steps`, `--focus-spy <DECIMAL>` (focus analysis on a specific SPY level), `--top-n <NUM>` (number of contributors to show).
        * **Output:** Displays Key Portfolio Insights table, tables showing Top N Contributors at key SPY levels (or focused level), and a table highlighting Positions Contributing to Negative Performance in Rising Markets.

* **`help [COMMAND]`**:
    * **Goal:** Provide usage information.
    * **Action:** Accesses command registry and pre-defined help text/examples.
    * **Output:** Without arguments, lists all commands, descriptions, and subcommands. With a command argument, shows detailed help, usage examples, and subcommands for that specific command.

* **`exit`**:
    * **Goal:** Terminate the application.
    * **Action:** Breaks the main REPL loop.
    * **Output:** Exits the shell.

**4. Data Flow:**

* **Input:** Primarily Portfolio CSV files. Assumes a specific format (derived from `portfolio-private.csv`).
* **Processing:** Uses `folib` library for loading (`folib.data.loader`), parsing (`folib.data.loader`), identifying positions (`folib.services.portfolio_service`), fetching market data (`folib.data.stock`, `folib.data.provider_yfinance`/`_fmp`), and performing calculations (`folib.calculations`).
* **State:** In-memory `state` dictionary holds loaded data and results between commands.
* **Output:** Formatted text and tables printed to the console using `rich`.

**5. UI/UX Principles:**

* **Efficiency:** Fast execution, minimal TTY overhead, keyboard-centric interaction.
* **Clarity:** Structured, readable output using tables and consistent formatting.
* **Discoverability:** Comprehensive `help` system.
* **Composability:** Focused commands suitable for scripting (though interactive shell is primary).
* **Focus:** Allows deep dives into specific data points without GUI distractions.
