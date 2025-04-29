# Folib: Concise Project Overview

> This is a condensed version of the [full redesign plan](master-plan-v2.md).

## Problem Statement

The current Folio codebase has several structural issues that need to be addressed:

1. **Code Duplication**: Business logic is duplicated between the web app (`src/folio`) and CLI tool (`src/focli`).

2. **Tight Coupling**: Core logic is tightly coupled with presentation layers, making it difficult to reuse.

3. **Inconsistent Design**:
   - Data models use inheritance instead of composition
   - Business logic is mixed into data classes
   - Large monolithic functions handle multiple responsibilities

4. **Limited Extensibility**: The current architecture makes it difficult to add new interfaces (like a REST API).

5. **Maintenance Challenges**: Changes to core logic often require updates in multiple places.

## Core Design Principles

We're creating `folib`, a new library with these guiding principles:

1. **Functional-First Programming**:
   - Pure functions for calculations
   - Minimize state and side effects
   - Explicit dependencies

2. **Thin Data Models**:
   - Data classes for representation only
   - No methods or business logic in data classes
   - No inheritance hierarchies

3. **Composition Over Inheritance**:
   - Build complex functionality through composition
   - Avoid class hierarchies

4. **Clear Module Boundaries**:
   - Each module has a single responsibility
   - Well-defined interfaces between modules

5. **Error Handling Strategy**:
   - "Fail fast" approach with minimal explicit error handling
   - Rely on Python's type system to catch errors
   - Let exceptions propagate rather than hiding them
   - See [error-handling.md](error-handling.md) for details

## Target Structure

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

### Module Details

#### 1. `domain.py`

This module contains all core data classes with no methods or inheritance.

**Class Diagram:**
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Position     │     │ PortfolioGroup  │     │ PortfolioSummary│
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ ticker: str     │     │ ticker: str     │     │ total_value: float
│ quantity: float │◄────│ positions: list │     │ stock_value: float
│ position_type   │     │                 │     │ option_value: float
└─────────────────┘     └─────────────────┘     │ cash_value: float
       ▲                                         │ portfolio_beta  │
       │                                         └─────────────────┘
┌──────┴──────────┐
│                 │
┌─────────────────┐     ┌─────────────────┐
│  StockPosition  │     │  OptionPosition │
├─────────────────┤     ├─────────────────┤
│ price: float    │     │ strike: float   │
│ cost_basis: float     │ expiry: date    │
└─────────────────┘     │ option_type: str│
                        └─────────────────┘
```

**Key Classes:**
```python
@dataclass(frozen=True)
class Position:
    ticker: str
    quantity: float
    position_type: Literal["stock", "option"]

@dataclass(frozen=True)
class StockPosition:
    ticker: str
    quantity: float
    price: float
    cost_basis: float | None = None

    @property
    def position_type(self) -> Literal["stock"]:
        return "stock"

@dataclass(frozen=True)
class OptionPosition:
    ticker: str
    quantity: float
    strike: float
    expiry: date
    option_type: Literal["CALL", "PUT"]
    price: float
    underlying_price: float

    @property
    def position_type(self) -> Literal["option"]:
        return "option"
```

**Current Implementation:** `src/folio/data_model.py`

#### 2. `calculations/beta.py`

Pure functions for beta calculations.

**Key Functions:**
```python
def calculate_beta(ticker: str,
                  historical_data: pd.DataFrame,
                  market_data: pd.DataFrame) -> float:
    """Calculate beta for a ticker using historical price data."""

def calculate_portfolio_beta(positions: list[Position],
                            market_values: dict[str, float],
                            betas: dict[str, float]) -> float:
    """Calculate the weighted average beta for a portfolio."""
```

**Current Implementation:** `src/folio/utils.py` (get_beta function)

#### 3. `calculations/exposure.py`

Pure functions for exposure calculations.

**Key Functions:**
```python
def calculate_stock_exposure(quantity: float, price: float) -> float:
    """Calculate market exposure for a stock position."""

def calculate_option_exposure(delta: float,
                             notional_value: float) -> float:
    """Calculate market exposure for an option position."""

def calculate_beta_adjusted_exposure(exposure: float,
                                    beta: float) -> float:
    """Calculate beta-adjusted exposure."""
```

**Current Implementation:** `src/folio/portfolio_value.py`

#### 4. `calculations/options.py`

Pure functions for option pricing and Greeks calculations.

**Key Functions:**
```python
def calculate_option_price(option_type: str,
                          strike: float,
                          expiry: date,
                          underlying_price: float,
                          volatility: float = 0.3,
                          risk_free_rate: float = 0.05) -> float:
    """Calculate option price using Black-Scholes model."""

def calculate_option_delta(option_type: str,
                          strike: float,
                          expiry: date,
                          underlying_price: float,
                          volatility: float = 0.3) -> float:
    """Calculate option delta."""

def calculate_implied_volatility(option_type: str,
                                strike: float,
                                expiry: date,
                                underlying_price: float,
                                option_price: float) -> float:
    """Calculate implied volatility from option price."""
```

**Current Implementation:** `src/folio/options.py`

#### 5. `calculations/pnl.py`

Pure functions for profit and loss calculations.

**Key Functions:**
```python
def calculate_stock_pnl(quantity: float,
                       entry_price: float,
                       current_price: float) -> float:
    """Calculate P&L for a stock position."""

def calculate_option_pnl(option: OptionPosition,
                        new_underlying_price: float) -> float:
    """Calculate P&L for an option position."""
```

**Current Implementation:** `src/folio/simulator_v2.py`

#### 6. `data/market.py`

Central service for accessing market data.

**Class Diagram:**
```
┌─────────────────┐
│  StockOracle    │
├─────────────────┤
│ get_price()     │
│ get_beta()      │
│ get_volatility()│
└─────────────────┘
```

**Key Functions:**
```python
class StockOracle:
    def get_price(self, ticker: str) -> float:
        """Get current price for a ticker."""

    def get_beta(self, ticker: str) -> float:
        """Get beta for a ticker."""

    def get_historical_data(self, ticker: str,
                           period: str = "1y") -> pd.DataFrame:
        """Get historical price data for a ticker."""
```

**Current Implementation:** `src/folio/marketdata.py`, `src/stockdata.py`

#### 7. `data/csv_loader.py`

Functions for loading and parsing portfolio CSV files.

**Key Functions:**
```python
def load_portfolio_from_csv(file_path: str) -> pd.DataFrame:
    """Load portfolio data from CSV file."""

def parse_portfolio_holdings(df: pd.DataFrame) -> list[PortfolioHolding]:
    """Parse raw CSV data into portfolio holdings."""
```

**Current Implementation:** `src/folio/portfolio.py` (process_portfolio_data function)

#### 8. `services/portfolio_service.py`

High-level functions for portfolio processing.

**Key Functions:**
```python
def process_portfolio(holdings: list[PortfolioHolding],
                     market_oracle: StockOracle) -> Portfolio:
    """Process raw portfolio holdings into a structured portfolio."""

def create_portfolio_summary(portfolio: Portfolio) -> PortfolioSummary:
    """Create a summary of portfolio metrics."""
```

**Current Implementation:** `src/folio/portfolio.py`

#### 9. `services/simulation_service.py`

High-level functions for portfolio simulation.

**Key Functions:**
```python
def simulate_portfolio(portfolio: Portfolio,
                      spy_changes: list[float],
                      market_oracle: StockOracle) -> dict:
    """Simulate portfolio performance across different SPY changes."""

def generate_spy_changes(min_change: float = -0.2,
                        max_change: float = 0.2,
                        steps: int = 11) -> list[float]:
    """Generate a list of SPY changes for simulation."""
```

**Current Implementation:** `src/folio/simulator_v2.py`

### Integration Points

- **CLI Application (`focli/`)**: First consumer of the library
- **Future API**: Will expose `folib` services via REST endpoints
- **Future Web UI**: React-based UI replacing the current Dash implementation

## Implementation Approach

We're using a staged implementation:

1. Define core data structures (`domain.py`)
2. Create calculation functions (`calculations/`)
3. Implement data access layer (`data/`)
4. Build service layer (`services/`)
5. Integrate with CLI (`focli`)
6. Develop API and new UI (future)

For more details on the implementation plan, see the [full master plan](master-plan-v2.md).
