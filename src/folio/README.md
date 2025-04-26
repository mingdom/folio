# Folio - Portfolio Dashboard

## Overview

Folio is a web-based dashboard for analyzing and visualizing investment portfolios. It provides a comprehensive view of your portfolio's composition, risk metrics, and exposure analysis with a focus on stocks and options.

## Features

- **Portfolio Analysis**: View your entire portfolio with key metrics like value, beta, and exposure
- **Position Grouping**: Automatically groups stocks with their related options
- **Risk Metrics**: Calculates beta and beta-adjusted exposure for all positions
- **Options Analysis**: Provides delta exposure and other option-specific metrics
- **Interactive UI**: Filter, sort, and search your portfolio with real-time updates
- **Position Details**: Drill down into specific positions for detailed analysis
- **CSV Import**: Upload portfolio data from CSV exports (compatible with Fidelity exports)
- **Auto-Refresh**: Periodically refreshes data to keep metrics current

## Getting Started

### Prerequisites

- Python 3.9+
- Required packages (see `requirements.txt` in the project root)

### Running the Dashboard

```bash
# From the project root directory:

# Start with default settings (will prompt for file upload)
make folio

# Start with a specific portfolio file
make folio portfolio=path/to/portfolio.csv

# Or run directly with Python
python -m src.folio --portfolio path/to/portfolio.csv --port 8051
```

The dashboard will be available at http://127.0.0.1:8051/ (or your specified port).

## Project Structure

```
src/folio/
├── __init__.py         # Package initialization
├── __main__.py         # Entry point for running as a module
├── app.py              # Main Dash application setup and callbacks
├── components/         # UI components
│   ├── __init__.py
│   ├── portfolio_table.py  # Portfolio table component
│   └── position_details.py # Position details modal
├── data_model.py       # Data models and type definitions
├── logger.py           # Logging configuration
└── utils.py            # Utility functions for data processing
```

## Data Model

The application uses the following key data structures:

- **Position**: Base class for all positions (stocks and options)
- **StockPosition**: Represents a stock position
- **OptionPosition**: Represents an option position with strike, expiry, etc.
- **PortfolioGroup**: Groups a stock with its related options
- **PortfolioSummary**: Contains aggregated metrics for the entire portfolio
- **ExposureBreakdown**: Detailed breakdown of exposure metrics

## Development Guide

### Adding New Features

1. **UI Components**: Add new components in the `components/` directory
2. **Data Processing**: Extend the data model in `data_model.py` and processing logic in `utils.py`
3. **Callbacks**: Add new callbacks in `app.py` to handle user interactions

### Coding Standards

- Use type hints for all functions and methods
- Document functions with docstrings (Google style)
- Log important operations and errors using the logger
- Handle exceptions gracefully with appropriate error messages
- Follow the existing pattern for callback registration

### Testing

While there's no formal test suite yet, you can test your changes by:

1. Running the application with a sample portfolio
2. Verifying that all UI components render correctly
3. Checking that calculations produce expected results
4. Testing edge cases (empty portfolio, invalid data, etc.)

## Troubleshooting

### Common Issues

- **Missing Data**: Ensure your CSV has all required columns (Symbol, Description, Quantity, etc.)
- **Port Conflicts**: If the default port is in use, specify a different port with `--port`
- **Data Fetching Errors**: Check network connectivity for beta data retrieval

### Logging

Logs are stored in the `logs/` directory with timestamps. Check these logs for detailed error information.

## Future Improvements

- Add unit tests for core functionality
- Implement additional portfolio metrics (Sharpe ratio, VaR, etc.)
- Add visualization components (charts, graphs)
- Support for additional data sources beyond CSV
- Enhanced options analytics with Greeks (gamma, theta, vega)

## Contributing

1. Follow the existing code style and patterns
2. Document your changes thoroughly
3. Test your changes with various portfolio data
4. Submit a pull request with a clear description of your changes
