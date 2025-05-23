# Folio CLI (`src/cli`) Specification

**Version:** 1.0
**Date:** 2025-05-01
**Status:** Proposed

## 1. Overview

This document outlines the specifications for the `Folio CLI`, a command-line interface for portfolio analysis and simulation. This tool provides both an interactive shell experience and direct command-line execution capabilities for all its features. It leverages the core functionalities implemented in the `folib` library, ensuring complete decoupling from the `folio` web application.

**Goals:**

* Provide a powerful, fast, and scriptable interface for portfolio analysis.
* Serve as a primary tool for End-to-End (E2E) testing of the `folib` library's functionalities.
* Be easily maintainable and extensible with new commands and features.
* Offer an intuitive user experience for users comfortable with command-line tools.

## 2. Target Users

* **Developers:** For testing `folib` functionality, scripting analysis, and integration.
* **Financial Analysts / Quants:** For rapid analysis, scenario testing, and data exploration without a GUI.
* **Power Users:** For efficient portfolio checks, custom analysis workflows, and automation.

## 3. Architectural Principles

* **Decoupling:** The CLI depends *only* on the `folib` library for all core business logic (data fetching, calculations, portfolio processing). It MUST NOT import or depend on any code from `folio/` (the web app).
* **Maintainability:** Implement commands in a modular fashion (e.g., one file per command or command group under `src/cli/commands/`). Leverage a robust CLI framework.
* **Extensibility:** The command structure should make it straightforward to add new analysis commands or options as `folib` evolves.
* **Testability:** The requirement for direct command-line execution for every feature is paramount, enabling automated E2E testing.
* **Framework:** Utilize a modern CLI framework like `Typer` or `Click` consistently across all commands to simplify argument parsing, help generation, and support for both interactive and direct execution modes.

## 4. Core Experience

**4.1. Dual Execution Modes:**

* **Direct Execution:**
    * Every feature MUST be accessible via a direct command call from the system shell (e.g., `python -m src.cli portfolio summary --file path/portfolio.csv`).
    * Each command execution is self-contained. Required data (like portfolio file path) must be passed as arguments/options.
    * Output is printed directly to stdout/stderr, and the process exits upon completion.
    * This mode is the primary target for E2E testing.
* **Interactive Mode (Shell):**
    * Launched by running the main CLI script without specific command arguments (e.g., `python -m src.cli`).
    * Provides a persistent session (`folio> ` prompt).
    * Manages state (e.g., loaded portfolio) between commands within a session.
    * Offers command history (`~/.folio_cli_history`) and auto-completion.
    * Uses a command dispatcher to execute functions associated with user input.
    * Exited via an `exit` command or standard EOF signal (Ctrl+D).

**4.2. Output Formatting:**

* Utilize the `rich` library for all console output (both modes) to ensure clarity, readability, and consistent formatting (tables, syntax highlighting, colors).
* Implement standardized formatting functions (potentially reusing/adapting from `focli/formatters.py` or `folio/formatting.py`, but residing within `src/cli` or `folib`) for currency, percentages, beta, etc.

**4.3. Discoverability & Help:**

* Implement a comprehensive help system accessible via `--help` for the main entry point and each command/subcommand.
* The interactive shell should have a `help [COMMAND]` command.
* Help messages should be automatically generated by the chosen CLI framework based on function signatures and docstrings.

**4.4. State Management (Interactive Mode):**

* The interactive shell maintains state within a session (e.g., loaded portfolio path, last results).
* This state is primarily for user convenience in interactive mode and MUST NOT be relied upon by the core command logic, which needs to function independently for direct execution. Caching of loaded data within the shell session is acceptable.
* When starting the interactive shell, it should automatically display the portfolio summary view after loading the default portfolio to provide immediate insights to users.

## 5. Command Specifications

*(Note: All commands must support Direct Execution via CLI arguments/options AND be callable from the Interactive Shell.)*

* **`portfolio`**: View and manage the portfolio.
    * **`load <FILE_PATH>`**:
        * **Goal:** Load portfolio data from a CSV file.
        * **Direct:** `folio portfolio load <FILE_PATH>`
        * **Interactive:** `portfolio load <FILE_PATH>`
        * **Action:** Uses `folib.data.loader` and `folib.services.portfolio_service.process_portfolio`. Stores path/data in interactive state.
        * **Output:** Confirmation message or error.
    * **`summary`**:
        * **Goal:** Display high-level portfolio metrics.
        * **Direct:** `folio portfolio summary --file <FILE_PATH>`
        * **Interactive:** `portfolio summary` (uses loaded portfolio from state)
        * **Action:** Requires loaded portfolio data (from file argument or interactive state). Uses `folib.services.portfolio_service.create_portfolio_summary`.
        * **Output:** Formatted tables (via `rich`) showing Portfolio Overview and Exposure Breakdown.
    * **`list [options]`**:
        * **Goal:** List positions with filtering and sorting.
        * **Direct:** `folio portfolio list --file <FILE_PATH> [options...]`
        * **Interactive:** `portfolio list [options...]` (uses loaded portfolio from state)
        * **Action:** Requires loaded portfolio. Filters/sorts positions based on options.
        * **Options (Examples):** `--file <PATH>`, `--focus <TICKERS>`, `--type [stock|option|cash]`, `--min-value <VAL>`, `--max-value <VAL>`, `--sort [ticker|value|beta|exposure]` (Specify direction: e.g., `value:desc`).
        * **Output:** Formatted table (`rich`) of positions with key metrics. Filter summary if applicable.

* **`position <TICKER>`**: Show all positions for a ticker.
        * **Goal:** Display all stock and option positions for a ticker in a unified table.
        * **Direct:** `folio position <TICKER> --file <FILE_PATH>`
        * **Interactive:** `position <TICKER>`
        * **Action:** Requires loaded portfolio. Groups positions by ticker and displays in unified table.
        * **Options:** `--file <PATH>`
        * **Output:** Unified table showing quantity, type (Stock/CALL Option/PUT Option), value, and beta adjusted exposure for each position.
    * **`simulate [options]`**:
        * **Goal:** Simulate P&L for a specific position group against SPY changes.
        * **Direct:** `folio position <TICKER> simulate --file <FILE_PATH> [--min-spy <VAL>] [--max-spy <VAL>] [--steps <N>]`
        * **Interactive:** `position <TICKER> simulate [options...]`
        * **Action:** Requires loaded portfolio. Uses `folib.services.simulation_service`.
        * **Options:** `--file <PATH>`, `--min-spy <DECIMAL>`, `--max-spy <DECIMAL>`, `--steps <NUM>`.
        * **Output:** Formatted tables showing simulation summary (Min/Max P&L) and step-by-step P&L results.

* **`sim [options]`**: Simulate portfolio performance using the V2 simulator.
    * **Goal:** Run portfolio simulation using the preferred (`simulator_v2`) engine.
    * **Direct:** `folio sim --file <FILE_PATH> [options...]`
    * **Interactive:** `sim [options...]`
    * **Action:** Requires loaded portfolio. Uses `folib.services.simulation_service` (which should use the V2 logic).
    * **Options:** `--file <PATH>`, `--min-spy <VAL>`, `--max-spy <VAL>`, `--steps <N>`, `--ticker <TICKER>` (focus), `--type [stock|option]`, `--analyze-correlation`.
    * **Output:** Formatted table showing SPY Change, SPY Price, Portfolio Value, P&L vs 0% baseline. Optionally includes detailed position tables or correlation analysis table.

* **`dcf <TICKER> [options]`**: Perform Discounted Cash Flow valuation (New Feature).
    * **Goal:** Calculate DCF intrinsic value for a ticker.
    * **Direct:** `folio dcf <TICKER> [options...]`
    * **Interactive:** `dcf <TICKER> [options...]`
    * **Action:** Uses `folib.services.calculate_dcf` which fetches data via FMP API.
    * **Options:** `--metric <METRIC>`, `--years <N>`, `--metric-growth <RATE>`, `--shares-growth <RATE>`, `--dividend-growth <RATE>`, `--price-ratio <RATIO>`, `--discount-rate <RATE>`, `--override-metric <VALUE>`, `--show-details`.
    * **Output:** Summary table/output showing Ticker, Current Price, DCF Value, Upside/Downside, CAGR, Inputs Used. Detailed view shows year-by-year projections.

* **`help [COMMAND]`**: Display help information.
    * **Direct:** `folio --help`, `folio <COMMAND> --help`
    * **Interactive:** `help`, `help <COMMAND>`
    * **Output:** Auto-generated help text for the application or a specific command.

* **`exit`** (Interactive Mode Only):
    * **Goal:** Terminate the interactive session.
    * **Action:** Exits the shell loop.

## 6. Data Flow

* **Input:** Portfolio CSV files (via `--file` or interactive `load`). Ticker symbols and parameters via CLI arguments/options.
* **Processing:** All core logic resides in `folib`. The CLI acts as a thin layer, parsing inputs, calling `folib` services, and formatting results. Market data (stock prices, FMP financials, option data, Treasury yields) is fetched by `folib` as needed, utilizing its cache.
* **Output:** Formatted text and tables printed to standard output using `rich`. Standard error used for logging/error messages.

## 7. Maintainability & Extensibility

* Use a CLI framework (`Typer` recommended, as parts of `focli` already use it) for consistency.
* Each command/group should reside in its own file within `src/cli/commands/`.
* Command functions should primarily handle input parsing, calling the relevant `folib` service function, and formatting the result using shared formatting utilities.
* Minimize state dependence in command logic to facilitate direct execution and testing.
* Core financial logic changes should happen in `folib`, requiring minimal changes in the CLI layer itself beyond potentially adjusting parameters or output formatting.
