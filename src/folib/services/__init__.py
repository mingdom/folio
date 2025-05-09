"""
Service functions for portfolio operations.

This package contains high-level functions that orchestrate the lower-level
calculations and data access functions. The service layer is the primary
entry point for applications using the folib library.

Module Overview:
--------------
- portfolio_service.py: Portfolio processing and analysis
  - process_portfolio: Convert raw portfolio data into a structured portfolio
  - create_portfolio_summary: Generate summary metrics for a portfolio
  - group_positions_by_ticker: Group positions by underlying ticker
  - get_portfolio_exposures: Calculate exposures for a portfolio
  - get_portfolio_value: Calculate total portfolio value
  - get_portfolio_beta_exposure: Calculate beta-adjusted exposure

- position_service.py: Position analysis and calculations
  - analyze_position: Analyze a single position or position group
  - calculate_position_metrics: Calculate metrics for a position
  - get_position_exposure: Calculate exposure for a position
  - get_position_value: Calculate value of a position
  - get_position_beta: Calculate beta for a position

- ticker_service.py: Ticker data management
  - TickerService: Service for accessing ticker-related data
  - get_ticker_data: Get all data for a ticker
  - get_price: Get the price for a ticker
  - get_beta: Get the beta for a ticker
  - get_company_profile: Get the company profile for a ticker
  - ticker_service: Pre-initialized instance for convenience

- simulation_service.py: Portfolio simulation
  - simulate_portfolio: Simulate portfolio performance with market changes
  - simulate_position: Simulate position performance with market changes
  - create_simulation_scenarios: Create simulation scenarios

Design Principles:
----------------
The service layer follows these design principles:
- Orchestration: Combine lower-level components to fulfill use cases
- Statelessness: Functions don't maintain state between calls
- Explicit dependencies: Dependencies are passed as parameters
- Error handling: Proper error handling and validation

Usage:
-----
Applications should interact with the folib library primarily through
the service layer, which provides a stable, high-level API that hides
the implementation details of the lower layers.
"""
