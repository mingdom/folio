---
description: This document explains the system architecture and data flow of the Folio application
globs: *
alwaysApply: true
---

# Folio Project Design

This document outlines how the Folio codebase is structured and how data flows through the application. Folio is a web-based dashboard for analyzing and visualizing investment portfolios, with a focus on stocks and options.

## Application Overview

Folio is a Python-based web application built with Dash that provides comprehensive portfolio analysis capabilities. The primary domain entities for this app are outlined below. For an authoritative overview of the data model, [data_model.py](src/folio/data_model.py) is the source of truth.

## Deployment Modes

Folio can run in multiple deployment environments:

- **Local Development**: Running directly on a developer's machine
- **Docker Container**: Running in a containerized environment
- **Hugging Face Spaces**: Deployed as a Hugging Face Space for public access

The application detects its environment and adjusts settings accordingly, such as cache directories and logging behavior.

## Core Data Model

The core data model consists of several key classes that represent portfolio components:

- **Position**: Base class for all positions
  - **StockPosition**: Represents a stock position with quantity, price, beta, etc.
  - **OptionPosition**: Represents an option position with strike, expiry, option type, delta, etc.
- **PortfolioGroup**: Groups a stock with its related options (e.g., AAPL stock with AAPL options)
- **PortfolioSummary**: Contains aggregated metrics for the entire portfolio
- **ExposureBreakdown**: Detailed breakdown of exposure metrics by category

These classes are defined in [data_model.py](src/folio/data_model.py) and provide the foundation for all portfolio analysis.

## Data Flow

The data flow in Folio follows these main steps:

1. **Data Input**: User uploads a portfolio CSV file or loads a sample portfolio
2. **Data Processing**: The CSV is parsed, validated, and transformed into structured portfolio data
3. **Position Grouping**: Stocks and their related options are grouped together
4. **Metrics Calculation**: Exposure, beta, and other metrics are calculated for each position and group
5. **Visualization**: The processed data is displayed in the dashboard with charts and tables
6. **Interactivity**: User interactions trigger callbacks that update the displayed data

### CSV Processing

When a user uploads a CSV file, the following process occurs:

1. The file is validated for security in [security.py](src/folio/security.py)
2. The CSV is parsed into a pandas DataFrame
3. The DataFrame is processed by `process_portfolio_data()` in [portfolio.py](src/folio/portfolio.py)
4. Stock positions are identified and processed
5. Option positions are parsed and matched to their underlying stocks
6. Cash-like positions are identified using [cash_detection.py](src/folio/cash_detection.py)
7. Portfolio groups and summary metrics are calculated

### Stock Data Fetching

Folio uses a pluggable data fetching system to retrieve stock data:

1. A `DataFetcherInterface` defined in [stockdata.py](src/stockdata.py) provides a common interface
2. Concrete implementations include `YFinanceDataFetcher` and `FMP` (Financial Modeling Prep) fetchers
3. A singleton pattern ensures only one data fetcher is created throughout the application
4. The data source can be configured at runtime through the `folio.yaml` configuration file
5. Data is cached to improve performance and reduce API calls

### Options Processing

Option positions require special processing:

1. Option descriptions are parsed in [options.py](src/folio/options.py) to extract strike, expiry, and option type
2. QuantLib is used for option pricing and Greeks calculations
3. Delta exposure is calculated as delta * notional value
4. Options are matched to their underlying stocks to form portfolio groups
5. Option metrics are aggregated into the portfolio summary

### Portfolio Metrics Calculation

Portfolio metrics are calculated in several steps:

1. Individual position metrics are calculated first (market value, beta, exposure)
2. Positions are grouped by underlying ticker
3. Group-level metrics are calculated (net exposure, beta-adjusted exposure)
4. Portfolio-level metrics are calculated (total exposure, portfolio beta, etc.)
5. Exposure breakdowns are created for visualization

The canonical implementations for these calculations are in [portfolio_value.py](src/folio/portfolio_value.py).

## UI Components

The UI is built with Dash and consists of several key components:

1. **Summary Cards**: Display high-level portfolio metrics
2. **Charts**: Visualize portfolio allocation and exposure
3. **Portfolio Table**: Display all positions with key metrics
4. **Position Details**: Show detailed information for a selected position
5. **P&L Chart**: Visualize profit/loss scenarios for options strategies

Each component is defined in the [components](src/folio/components) directory and registered with callbacks in [app.py](src/folio/app.py).

### Component Interaction

Components interact through Dash callbacks:

1. Data is stored in `dcc.Store` components that act as a client-side state
2. User interactions trigger callbacks that update the stored data
3. Components subscribe to changes in the stored data and update accordingly
4. This pattern allows for a reactive UI without page reloads

## Key Modules

### Data Processing

- **portfolio.py**: Core portfolio processing logic
- **portfolio_value.py**: Canonical implementations of portfolio value calculations
- **options.py**: Option pricing and Greeks calculations
- **cash_detection.py**: Identification of cash-like positions

### Data Fetching

- **stockdata.py**: Common interface for data fetchers
- **yfinance.py**: Yahoo Finance data fetcher
- **fmp.py**: Financial Modeling Prep data fetcher

### UI Components

- **components/**: UI components for the dashboard
  - **charts.py**: Portfolio visualization charts
  - **portfolio_table.py**: Table of portfolio positions
  - **position_details.py**: Detailed view of a position
  - **pnl_chart.py**: Profit/loss visualization
  - **summary_cards.py**: High-level portfolio metrics

### Application Core

- **app.py**: Main Dash application setup and callbacks
- **data_model.py**: Core data structures
- **logger.py**: Logging configuration
- **security.py**: Security utilities for validating user inputs

## Configuration

Folio uses a YAML configuration file (`folio.yaml`) for runtime settings:

- **Data Source**: Configure which data source to use (Yahoo Finance or FMP)
- **Cache Settings**: Configure cache directories and TTL
- **UI Settings**: Configure dashboard appearance and behavior

The configuration is loaded at startup and can be overridden by environment variables.

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

## Development Workflow

To add new features to Folio:

1. **UI Components**: Add new components in the `components/` directory
2. **Data Processing**: Extend the data model in `data_model.py` and processing logic in `utils.py`
3. **Callbacks**: Add new callbacks in `app.py` to handle user interactions
4. **Testing**: Add tests for new functionality

## Conclusion

Folio is designed with a clean separation of concerns:

- Data fetching is abstracted behind interfaces
- Data processing is separated from UI components
- UI components are modular and reusable
- Configuration is externalized for flexibility

This architecture makes the codebase maintainable, testable, and extensible, allowing for easy addition of new features and improvements.
