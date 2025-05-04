---
description: This document explains the system architecture and data flow of the Folio application
globs: *
alwaysApply: true
---

# Folio Project Design

This document outlines how the Folio codebase is structured and how data flows through the application. Folio provides tools for analyzing and visualizing investment portfolios, with a focus on stocks and options, through both a web-based dashboard and a command-line interface (CLI).

## Application Overview

Folio is a Python-based application that provides comprehensive portfolio analysis capabilities through multiple interfaces:

1. **Web Interface (`src/folio/`)**: A Dash-based web application for visualizing portfolio data
2. **CLI Interface (`src/cli/`)**: A command-line interface for portfolio analysis and simulation

Both interfaces leverage the core library (`src/folib/`) for business logic, following our strict separation of concerns principles. The core library provides a functional-first approach to portfolio analysis with clear boundaries between layers.

## System Architecture

The codebase is organized into three main components:

```
src/
├── folib/                  # Core library - business logic
│   ├── domain.py           # Data classes (Position, Portfolio, etc.)
│   ├── calculations/       # Pure calculation functions
│   │   ├── exposure.py     # Exposure calculations
│   │   ├── options.py      # Option pricing and Greeks
│   ├── data/               # Data access layer
│   │   ├── stock.py        # Market data access
│   │   ├── loader.py       # Portfolio loading
│   ├── services/           # Orchestration layer
│       ├── portfolio_service.py  # Portfolio processing
│       ├── position_service.py   # Position analysis
│       ├── simulation_service.py # Portfolio simulation
├── folio/                  # Web interface (Dash)
│   ├── app.py              # Main Dash application
│   ├── components/         # UI components
├── cli/                    # Command-line interface
    ├── main.py             # CLI entry point
    ├── commands/           # Command implementations
    ├── shell.py            # Interactive shell
```

## Core Library (`src/folib/`)

The core library follows a layered architecture with clear separation of concerns:

### 1. Domain Layer (`domain.py`)

Contains immutable data classes that represent the core entities:

- **Position**: Base class for all positions
  - **StockPosition**: Represents a stock position with quantity, price, etc.
  - **OptionPosition**: Represents an option position with strike, expiry, option type, etc.
  - **CashPosition**: Represents cash or cash-like positions
- **Portfolio**: Contains a collection of positions and portfolio-level data
- **PortfolioSummary**: Contains aggregated metrics for the entire portfolio
- **ExposureMetrics**: Represents exposure metrics for positions and portfolios

### 2. Calculation Layer (`calculations/`)

Pure functions for financial calculations with no side effects:

- **exposure.py**: Functions for calculating position and portfolio exposures
- **options.py**: Functions for option pricing and Greeks calculations using QuantLib

### 3. Data Layer (`data/`)

Handles external data access and portfolio loading:

- **stock.py**: Market data access with provider abstraction
  - **StockOracle**: Central class for market data retrieval
  - Supports multiple providers (Yahoo Finance, Financial Modeling Prep)
- **stock_data.py**: Stock data management with caching
  - **StockData**: Container for stock-related information
  - **StockDataService**: Service for fetching and caching stock data
- **loader.py**: Portfolio loading and parsing from CSV files
- **provider_*.py**: Implementations for different market data providers

### 4. Service Layer (`services/`)

Orchestrates the lower layers to fulfill specific use cases:

- **portfolio_service.py**: Portfolio processing and analysis
- **position_service.py**: Position analysis and calculations
- **simulation_service.py**: Portfolio simulation

## Web Interface (`src/folio/`)

The web interface is built with Dash and provides a visual dashboard for portfolio analysis:

### Components

- **app.py**: Main Dash application setup and callbacks
- **components/**: UI components for the dashboard
  - **charts.py**: Portfolio visualization charts
  - **portfolio_table.py**: Table of portfolio positions
  - **position_details.py**: Detailed view of a position
  - **pnl_chart.py**: Profit/loss visualization
  - **summary_cards.py**: High-level portfolio metrics

### Data Flow

1. User uploads a portfolio CSV file or loads a sample portfolio
2. The file is processed by the core library's portfolio service
3. The resulting portfolio data is stored in Dash's client-side state
4. UI components subscribe to changes in the state and update accordingly
5. User interactions trigger callbacks that update the state

## CLI Interface (`src/cli/`)

The CLI provides a command-line tool for portfolio analysis and simulation:

### Architecture

- **main.py**: Main entry point for the CLI
- **shell.py**: Interactive shell implementation
- **commands/**: Command implementations
  - **portfolio.py**: Portfolio commands (load, summary, list)
  - **position.py**: Position commands (details, risk)
- **formatters.py**: Output formatting utilities
- **state.py**: State management for interactive mode

### Usage Modes

1. **Interactive Shell Mode**: Provides a persistent session with command history and tab completion
2. **Direct Execution Mode**: Commands can be executed directly from the system shell

### Command Structure

The CLI follows a command-subcommand structure:

```
folio> command [subcommand] [options]
```

Key commands include:
- `portfolio`: View and manage the portfolio (load, summary, list)
- `position`: Analyze a specific position (details, risk)

## Data Flow

The data flow in Folio follows these main steps:

1. **Data Input**: User uploads a portfolio CSV file or loads a sample portfolio
2. **Data Loading**: The CSV is loaded and parsed into portfolio holdings by the data layer
3. **Portfolio Processing**: Holdings are processed into a structured portfolio by the service layer
4. **Position Analysis**: Positions are analyzed to calculate metrics (exposure, beta, etc.)
5. **Presentation**: Results are presented to the user through the web UI or CLI

### Portfolio Processing Flow

```
CSV File → load_portfolio_from_csv() → parse_portfolio_holdings() → process_portfolio() → Portfolio
```

### Market Data Flow

```
Ticker → StockDataService → StockOracle → Provider (YFinance/FMP) → Market Data
                         ↓
                    Cache (.cache_stock_data)
```

## Key Design Decisions

### 1. Functional-First Approach

The core library follows functional programming principles:
- Pure functions with no side effects
- Immutable data structures
- Explicit data flow
- Minimal dependencies between components

### 2. Provider Abstraction

Market data can be fetched from multiple providers:
- Yahoo Finance (default)
- Financial Modeling Prep (FMP)
- Providers implement a common interface
- Configuration can be changed at runtime

### 3. Caching Strategy

Market data is cached to improve performance and reduce API calls:
- Centralized caching through the StockDataService class
- In-memory caching for fast access
- File-based persistence in a single .cache_stock_data directory
- Time-based cache invalidation (default: 1 hour)
- Clear separation between data fetching (StockOracle) and caching (StockDataService)

### 4. Separation of Concerns

The codebase strictly separates concerns:
- Core library contains all business logic
- Interface layers (web UI, CLI) only handle presentation
- No business logic in interface layers
- Clear boundaries between layers

## Deployment Modes

Folio can run in multiple deployment environments:

- **Local Development**: Running directly on a developer's machine
- **Docker Container**: Running in a containerized environment
- **Hugging Face Spaces**: Deployed as a Hugging Face Space for public access

The application detects its environment and adjusts settings accordingly, such as cache directories and logging behavior.

## Error Handling

Folio implements robust error handling:

1. **Fail Fast, Fail Transparently**: Errors are raised early and clearly
2. **Graceful Degradation**: The application continues to function even if some components fail
3. **Structured Logging**: Errors are logged with context for debugging
4. **User Feedback**: Error messages are displayed to the user when appropriate

## Testing

The codebase includes comprehensive tests:

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test interactions between components
- **Mock Data**: Use mock data for testing to avoid API calls

Tests are organized to mirror the structure of the source code, with test files corresponding to source files.

## Conclusion

Folio is designed with a clean architecture that separates concerns and promotes maintainability:

- **Core Library (`src/folib/`)**: Contains all business logic in a functional-first approach
- **Web Interface (`src/folio/`)**: Provides a visual dashboard using Dash
- **CLI Interface (`src/cli/`)**: Provides a command-line tool for portfolio analysis

This architecture makes the codebase maintainable, testable, and extensible, allowing for easy addition of new features and improvements.
