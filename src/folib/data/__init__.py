"""
Data access functions and classes.

This package contains functions and classes for accessing external data sources
and loading portfolio data from files. It handles all external I/O operations
and provides a clean interface for the rest of the library.

Module Overview:
--------------
- stock.py: Market data access with provider abstraction
  - StockOracle: Central class for market data retrieval with caching
  - stockdata: Pre-initialized singleton instance for easier access
  - Key functions: get_price, get_historical_data, get_beta, validate_symbol

- provider.py: Base provider interface
  - BaseProvider: Abstract base class for market data providers
  - Defines the interface that all providers must implement

- provider_yfinance.py: Yahoo Finance provider implementation
  - YFinanceProvider: Implementation using the yfinance library
  - Handles rate limiting, caching, and error handling

- provider_fmp.py: Financial Modeling Prep provider implementation
  - FMPProvider: Implementation using the FMP API
  - Alternative data source with different rate limits and capabilities

- loader.py: Portfolio loading and parsing
  - load_portfolio_from_csv: Load portfolio data from CSV files
  - parse_portfolio_holdings: Parse raw portfolio data into domain objects
  - validate_portfolio_data: Validate portfolio data structure

- cache.py: Caching utilities
  - Cache: Generic caching class for market data
  - Handles file-based caching with TTL (time-to-live)

Configuration:
------------
The data layer can be configured using environment variables:
- DATA_SOURCE: Provider to use ("yfinance" or "fmp")
- FMP_API_KEY: API key for the FMP provider
- CACHE_DIR: Directory for cached data
- CACHE_TTL: Cache time-to-live in seconds

Usage:
-----
The data layer is typically accessed through the service layer rather than directly.
The StockOracle class provides a unified interface for market data access regardless
of the underlying provider.
"""
