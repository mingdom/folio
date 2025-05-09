---
date: 2025-05-03
title: Ticker Service Proposal
author: Augment Agent
---

# Ticker Service Proposal

## WHY: User's Goal

The goal is to create a cleaner separation between position-specific data and market data for tickers. Currently, market data like beta values are calculated on-demand in various places throughout the codebase, leading to inconsistencies and violations of the separation of concerns principle. We need a centralized service that manages all ticker-related data.

## WHAT: Problem Statement

We need to create a "Ticker Service" that serves as the single source of truth for all ticker-related data, including prices, beta values, company profiles, and other market data. This service will abstract away the details of data fetching, caching, and normalization, providing a clean interface for the rest of the application to access ticker data.

## HOW: Solution

We will create a new `TickerService` class that manages a dictionary of ticker data, fetches data as needed using the existing `market_data_provider`, and provides methods to access various ticker attributes. This will allow us to centralize all ticker-related logic and ensure consistent handling of special cases like cash positions.

## Scope

This proposal affects:
- How market data is accessed throughout the application
- How position objects interact with market data
- The separation between position-specific data and market data
- The caching strategy for market data

## Assumptions

- The existing `market_data_provider` will continue to be used for fetching data from external sources
- Position objects will reference tickers but not store market data directly
- We will need to migrate existing code that directly accesses market data to use the new service

## Detailed Design

### 1. Core Data Structure

We will create a `TickerData` class to represent all data associated with a ticker:

```python
@dataclass(frozen=True)
class TickerData:
    """Data associated with a ticker symbol."""

    ticker: str
    price: float | None = None
    beta: float | None = None
    company_profile: dict | None = None
    last_updated: datetime | None = None

    @property
    def is_cash_like(self) -> bool:
        """Determine if this ticker represents a cash-like instrument."""
        # Implementation based on ticker patterns, beta values, etc.
        pass
```

### 2. Ticker Service

We will create a `TickerService` class that manages a dictionary of `TickerData` objects:

```python
class TickerService:
    """Service for accessing ticker data."""

    def __init__(self, market_data_provider: MarketDataProvider):
        self._market_data_provider = market_data_provider
        self._ticker_data: dict[str, TickerData] = {}

    def get_ticker_data(self, ticker: str) -> TickerData:
        """Get data for a ticker, fetching if necessary."""
        if ticker not in self._ticker_data:
            self._fetch_ticker_data(ticker)
        return self._ticker_data[ticker]

    def get_price(self, ticker: str) -> float:
        """Get the price for a ticker."""
        ticker_data = self.get_ticker_data(ticker)
        if ticker_data.is_cash_like:
            return 1.0  # Cash-like instruments have a price of 1.0
        return ticker_data.price or 0.0

    def get_beta(self, ticker: str) -> float:
        """Get the beta for a ticker."""
        ticker_data = self.get_ticker_data(ticker)
        if ticker_data.is_cash_like:
            return 0.0  # Cash-like instruments have a beta of 0.0
        return ticker_data.beta or 1.0

    def _fetch_ticker_data(self, ticker: str) -> None:
        """Fetch data for a ticker from the market data provider."""
        # Implementation using self._market_data_provider
        pass
```

### 3. Integration with Position Objects

Position objects will no longer need to store or calculate market data. Instead, they will use the `TickerService` to access this data:

```python
# Example usage in a service function
def calculate_position_exposure(position: Position, ticker_service: TickerService) -> float:
    """Calculate exposure for a position."""
    if position.position_type == "cash":
        return 0.0

    beta = ticker_service.get_beta(position.ticker)
    price = ticker_service.get_price(position.ticker)

    # Calculate exposure based on position type, beta, and price
    # ...
```

### 4. Caching Strategy

The `TickerService` will implement caching at two levels:

1. **In-Memory Cache**: The `_ticker_data` dictionary serves as an in-memory cache
2. **Persistent Cache**: We can add a persistent cache layer that saves ticker data to disk

The caching strategy will include:
- Time-based invalidation (e.g., prices expire after 15 minutes)
- Forced refresh options for critical operations
- Bulk prefetching for known tickers in a portfolio

## Implementation Plan

### Phase 1: Core Implementation

1. Create the `TickerData` class
2. Implement the basic `TickerService` class with in-memory caching
3. Update the `Position` classes to work with the `TickerService`
4. Modify service functions to use the `TickerService` for market data

### Phase 2: Enhanced Features

1. Add persistent caching to the `TickerService`
2. Implement bulk prefetching for portfolio tickers
3. Add more ticker data attributes (dividends, sector, etc.)
4. Create a ticker data update service for background refreshes

### Phase 3: Migration

1. Identify all places in the codebase that directly access market data
2. Migrate these to use the `TickerService`
3. Remove any redundant market data handling code
4. Update tests to use the `TickerService`

## Benefits

1. **Single Source of Truth**: All ticker data comes from one place
2. **Consistent Handling**: Special cases like cash positions are handled consistently
3. **Separation of Concerns**: Position objects focus on portfolio-specific data
4. **Improved Caching**: Centralized caching strategy for all ticker data
5. **Easier Testing**: Mock the `TickerService` instead of multiple market data calls

## Open Questions

1. How should we handle tickers that don't exist in external data sources?
2. Should we implement a background refresh mechanism for frequently accessed tickers?
3. How should we handle different data sources with potentially conflicting data?
4. What is the appropriate caching strategy for different types of ticker data?

## Conclusion

The proposed `TickerService` will provide a clean, centralized way to access all ticker-related data. This will improve code organization, ensure consistent handling of special cases, and make it easier to implement features like caching. By separating position-specific data from market data, we create a more maintainable and extensible codebase.
