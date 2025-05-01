# Folio Library (folib) Redesign Plan

## 1. Introduction

This document outlines a plan to redesign the core data structures and services for the Folio project, creating a new, reusable library named `folib`. The goal is to establish a robust, testable, and scalable foundation based on functional programming principles, thin data models, and composition over inheritance. This new library will eventually serve as the backend for both the `focli` CLI tool and a future FastAPI/React web application, replacing the current Dash implementation.

## 2. Current State Analysis

Based on the provided codebase:

### Project Structure
The project is currently split into `src/folio` (Dash app logic, core calculations, UI components) and `src/focli` (CLI tool). There's also `src/stockdata.py` and `src/yfinance.py` for data fetching. This structure leads to potential code duplication and tight coupling between core logic and presentation layers.

### Data Models (`src/folio/data_model.py`)
- Uses `@dataclass` for primary data representation (e.g., `StockPosition`, `OptionPosition`, `PortfolioGroup`, `PortfolioSummary`), which aligns partially with the "thin models" goal.
- **Inheritance**: `StockPosition` and `OptionPosition` inherit from a base `Position` class, violating the "composition over inheritance" goal.
- **Methods in Models**: Some data classes contain calculation logic (e.g., `recalculate_with_price`), which deviates from the "thin models" principle. Logic should ideally reside in separate functions or services.
- `ExposureBreakdown` appears somewhat complex, potentially mixing calculation results with data representation.

### Data Flow & Core Logic
- **Loading**: Primarily CSV-based, handled within `src/folio/portfolio.py` (`process_portfolio_data`). This function seems monolithic, mixing parsing, data fetching (prices, beta), calculations, and grouping.
- **Calculations**: Core calculations (options pricing/Greeks via QuantLib, P&L, exposures, beta) are spread across `options.py`, `pnl.py`, `portfolio_value.py`, and `portfolio.py`.
- **Simulation**: Logic exists in `simulator.py` and `simulator_v2.py`.
- **Data Fetching**: Abstracted via `src/stockdata.py` (interface) and `src/yfinance.py` (implementation), which is a good pattern.
- **Coupling**: Core logic is tightly coupled with the folio (Dash) application structure and data loading mechanisms. `focli` likely re-imports or duplicates logic from folio.

### Goal Alignment
- **Functional First**: Current implementation is more object-oriented with logic embedded in data models and large processing functions.
- **Thin Models**: Partially met, but some models contain calculation logic.
- **Composition**: Violated by the `Position` inheritance hierarchy.
- **API-Ready**: Core logic needs significant decoupling from data loading and the Dash framework to be easily exposed via an API.
- **Expand Scope**: A central library (`folib`) is clearly needed to consolidate logic for folio and focli.

## 3. Current User Scenarios

This section describes the core capabilities currently offered to users through the existing folio web application and the focli command-line tool. `folib` must eventually support these scenarios.

### Portfolio Loading
Users can load their portfolio data from a CSV file (either via upload in the web app or file path in the CLI). A sample portfolio can also be loaded.

### Portfolio Overview (Web & CLI)
- View high-level summary metrics (Total Value, Net Exposure, Beta-Adjusted Exposure, Long/Short/Options Exposure, Cash).
- See a list of all portfolio positions, grouped by underlying security.

### Position Analysis (Web & CLI)
- Drill down into specific position groups (e.g., AAPL stock and options).
- View detailed metrics for stock and option components.
- Analyze potential Profit & Loss scenarios for a position group across a range of underlying prices (P&L charts available in web app).
- Assess risk metrics for a specific position (CLI).

### Portfolio Visualization (Web App)
- Visualize market exposure breakdown (Net, Beta-Adjusted).
- View position sizing using a treemap based on exposure.
- See overall portfolio allocation across asset types (Long/Short/Cash).

### Portfolio Simulation (CLI)
- Simulate overall portfolio performance based on hypothetical changes in the SPY index.
- Analyze how individual positions contribute to portfolio P&L under different SPY scenarios.
- Filter simulations to focus on specific tickers or position types (stock/option).

### AI Interaction (Web App)
- Engage with an AI assistant to ask questions and receive analysis about the loaded portfolio.

## 4. Recommended Approach: Functional Core with Data Classes

We will proceed with the "Functional Core with Data Classes" approach.

**Description**: Create `folib` with pure functions for calculations. Use simple data classes (e.g., dataclasses, pydantic) strictly for data representation (no methods, no inheritance). Separate data fetching and portfolio loading into distinct modules within `folib`. Refactor `folio` and `focli` to use `folib`.

**Rationale**: This approach directly addresses the primary goals: functional-first programming, thin data models, and composition over inheritance. It mandates the necessary refactoring for improved structure and testability, creating a reusable core. It provides a solid, decoupled foundation for future API development (FastAPI) and UI work (React).

**Error Handling Strategy**: We follow a "fail fast" approach with minimal explicit error handling. See [error-handling.md](error-handling.md) for details on our error handling philosophy.

## 5. Staged Implementation Plan

This plan breaks down the implementation into manageable stages, focusing on building the core library first and then integrating existing applications.

### Stage 1: Define Core Data Structures (`folib/domain.py`)

**Goal**: Establish the fundamental, immutable data representations in a single module. These structures will be plain data holders with no associated behavior (methods).

**Tasks**:
1. Create `folib/domain.py`.
2. Define `StockPosition`, `OptionPosition` using dataclasses or pydantic. Ensure these classes contain only data fields and remove all calculation methods and inheritance hierarchies present in the current `data_model.py`.
3. Define `PortfolioHolding` to represent a single row/entry from the raw input source (e.g., CSV).
4. Define `Portfolio` as the primary container for the processed portfolio, holding lists of `StockPosition` and `OptionPosition` objects, along with summary metrics.
5. Define clear input/output data structures for calculation functions if complex data needs to be passed (can also reside in `domain.py`).

**Outcome**: A well-defined `folib/domain.py` module containing simple, reusable data classes, forming the vocabulary for the rest of the `folib` library.

### Stage 2: Create Core Calculation Functions (`folib/calculations/`)

**Goal**: Isolate all business logic and mathematical calculations into pure, independently testable functions within a dedicated package.

**Tasks**:
1. Create the `folib/calculations/` directory and `__init__.py`.
2. Create modules like `beta.py`, `exposure.py`, `options.py`, `pnl.py`.
3. Migrate calculation logic from existing modules (`options.py`, `portfolio.py`, `pnl.py`, `portfolio_value.py`) into pure functions within these modules (e.g., `calculate_beta`, `calculate_option_price`, `calculate_option_greeks`, `calculate_position_pnl`, `calculate_group_exposure`).
4. Ensure functions operate on the data classes defined in `folib.domain` or primitive types.
5. Minimize dependencies between functions; pass data explicitly.
6. Develop comprehensive unit tests for each calculation function.

**Outcome**: A robust, well-tested `folib.calculations` package containing the core mathematical engine of Folio.

### Stage 3: Implement Data Fetching & Loading (`folib/data/`)

**Goal**: Abstract all interactions with external data sources (market data APIs, files) into a dedicated package, simplifying the structure.

**Tasks**:
1. Create the `folib/data/` directory and `__init__.py`.
2. **Market Data** (`folib/data/stockdata.py`): Consolidate logic from `src/stockdata.py` and `src/yfinance.py`. Define functions like `fetch_prices(tickers)`, `fetch_historical_data(ticker, period)`, `fetch_beta(ticker)`. Include caching logic here. Define the `DataFetcherInterface` and `YFinanceDataFetcher` class (or just functions if only one implementation is needed initially).
3. **Portfolio Loaders** (`folib/data/csv_loader.py`): Create this module. Define functions like `load_portfolio_from_csv(file_path)` responsible for reading, parsing, validating, and sanitizing portfolio files (migrate logic from `src/folio/security.py` and `src/folio/portfolio.py`). Loaders should return data in the raw `PortfolioHolding` format from `folib.domain`.

**Outcome**: A `folib.data` package that handles all external data I/O, providing clean interfaces.

### Stage 4: Implement Core Services/Workflows (`folib/services/`)

**Goal**: Orchestrate the data structures, calculations, and data fetching/loading modules to perform the high-level tasks required by the applications (`focli`, future API).

**Tasks**:
1. Create the `folib/services/` directory and `__init__.py`.
2. Create modules like `portfolio_service.py`, `simulation_service.py`, `pnl_service.py`.
3. **Portfolio Processing Service** (`portfolio_service.process_portfolio`):
   - Input: List of raw `PortfolioHolding` objects.
   - Orchestration: Calls `folib.data.stockdata` to fetch necessary prices and betas. Uses `folib.calculations` to compute metrics for each holding. Groups holdings into `StockPosition` and `OptionPosition` objects. Aggregates results into a final `Portfolio` object (from `folib.domain`).
   - Output: A fully processed `Portfolio` object.
4. **Simulation Service** (`simulation_service.simulate_portfolio`):
   - Input: A processed `Portfolio` object, simulation parameters (e.g., SPY changes).
   - Orchestration: Iterates through scenarios. Uses `folib.calculations` to determine new position values and portfolio P&L.
   - Output: A structured representation of the simulation results.
5. **P&L Curve Service** (`pnl_service.generate_pnl_curve`):
   - Input: A specific `StockPosition` or list of `OptionPosition`, price range parameters.
   - Orchestration: Uses `folib.calculations` (`calculate_position_pnl`) across the specified price range.
   - Output: Data points for plotting the P&L curve.

**Outcome**: A `folib.services` package containing high-level functions that represent the core features of Folio.

### Stage 5: Integrate focli with folib

**Goal**: Refactor the existing `focli` tool to use the new `folib` library exclusively for its backend logic, serving as the first integration test.

**Tasks**:
1. Identify all places where `focli` currently imports or calls logic directly from `src/folio`.
2. Replace these calls with corresponding calls to functions and services within `folib` (e.g., `folib.data.csv_loader.load_portfolio_from_csv`, `folib.services.portfolio_service.process_portfolio`, `folib.services.simulation_service.simulate_portfolio`).
3. Update `focli` to use the data structures defined in `folib.domain`.
4. Ensure presentation logic (formatting results using rich) remains within `focli` (specifically `focli.formatters`). Keep formatting utilities needed by `focli` here.
5. Conduct thorough testing of all `focli` commands to ensure they function correctly with the `folib` backend.

**Outcome**: A functional `focli` tool powered entirely by the new `folib` library.

### Stage 6: (Future) API and New UI

**Goal**: Expose `folib` functionality via a web API and build a modern web UI using React.

**Tasks**:
1. Develop a FastAPI application. Create API endpoints that wrap the functions in `folib.services`.
2. Define request and response models for the API (potentially reusing `folib.domain` data classes if using Pydantic).
3. Build a React frontend application that interacts with the FastAPI backend.
4. Plan the gradual migration or replacement of the existing Dash application (`src/folio`) with the new React application.

**Outcome**: A modern, scalable, API-driven web application providing the Folio dashboard functionality, built on the robust `folib` foundation.

## 6. Target folib Structure

This section outlines the proposed simplified file and class structure for the `folib` library, representing the intended outcome of this redesign plan.

```
src/
├── folib/                     # The core library
│   ├── __init__.py
│   ├── domain.py              # All data classes (StockPosition, OptionPosition, PortfolioHolding, Portfolio, PortfolioSummary)
│   ├── calculations/          # Pure calculation functions
│   │   ├── __init__.py
│   │   ├── beta.py            # calculate_beta()
│   │   ├── exposure.py        # calculate_exposure(), calculate_beta_adjusted_exposure()
│   │   ├── options.py         # calculate_option_price(), calculate_option_greeks()
│   │   └── pnl.py             # calculate_position_pnl(), calculate_strategy_pnl()
│   ├── data/                  # Data fetching and loading
│   │   ├── __init__.py
│   │   ├── stock.py          # StockOracle, fetch_prices(), fetch_historical_data(), caching logic
│   │   └── loader.py      # load_portfolio_from_csv(), validation/sanitization logic
│   └── services/              # Orchestration layer / Use cases
│       ├── __init__.py
│       ├── portfolio_service.py # process_portfolio()
│       ├── simulation_service.py # simulate_portfolio()
│       └── pnl_service.py     # generate_pnl_curve()
```

- **`folib/domain.py`**: Contains all core data classes. Simple, focused data representation.
- **`folib/calculations/`**: Holds pure functions for all mathematical and financial logic, organized by topic (beta, exposure, options, pnl).
- **`folib/data/`**: Manages external data interactions. `stockdata.py` handles market data fetching and caching. `csv_loader.py` handles portfolio file loading and validation.
- **`folib/services/`**: Orchestrates the lower layers to fulfill specific use cases. These are the primary entry points for applications.
- **Consumers** (`focli`, future API/UI): Use `folib.services` and `folib.domain`. Formatting utilities needed by consumers (like `focli`) reside within the consumer's package (e.g., `focli/formatters.py`).

## 7. Conclusion

This revised plan emphasizes simplicity in the initial structure of `folib` while adhering to the core principles of functional design and separation of concerns. The staged implementation provides a clear path forward, starting with the foundational domain and calculations, then building data access and service layers, and finally integrating `focli` as the first consumer. This approach creates a maintainable and extensible library ready for future development.
