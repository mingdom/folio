Part of the `master-plan-v2.md`:

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
