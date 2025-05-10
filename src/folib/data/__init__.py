"""
Data access functions and classes.

This package contains functions and classes for accessing external data sources
and loading portfolio data from files. It handles all external I/O operations
and provides a clean interface for the rest of the library.

Module Overview:
--------------
- market_data.py: Unified market data access
  - MarketDataProvider: Primary interface for accessing market data
  - market_data_provider: Pre-initialized instance for convenience
  - Key functions: get_price, get_beta
  - Key features: in-session caching, direct FMP API integration

- provider_fmp.py: Financial Modeling Prep provider implementation
  - FMPProvider: Implementation using the FMP API
  - Used internally by MarketDataProvider

- ticker_data.py: Data structures for ticker-related data
  - TickerData: Class representing all data associated with a ticker
  - Key properties: is_cash_like, effective_beta, effective_price

- loader.py: Portfolio loading and parsing
  - load_portfolio_from_csv: Load portfolio data from CSV files
  - parse_portfolio_holdings: Parse raw portfolio data into domain objects
  - validate_portfolio_data: Validate portfolio data structure

Configuration:
------------
The data layer can be configured using environment variables:
- FMP_API_KEY: API key for the FMP provider (required)

Usage:
-----
The data layer is typically accessed through the service layer rather than directly.
For market data, use the MarketDataProvider which provides a unified interface for
accessing stock prices and beta values.

Example:
    from src.folib.data.market_data import market_data_provider

    # Get stock price
    price = market_data_provider.get_price("AAPL")

    # Get beta value
    beta = market_data_provider.get_beta("AAPL")
"""
