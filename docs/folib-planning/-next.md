---
description: Portfolio V2 Interface Plan for folib
date: "2025-05-01"
status: "PLANNED"
---

# Folib Portfolio V2 Interface Plan

This document outlines the detailed implementation plan for creating a new version of the portfolio interface in the folib library. The goal is to create a cleaner, more streamlined interface that doesn't require backward compatibility with the old implementation, allowing for more innovative features and better performance.

## Current Architecture

The folib library has been successfully integrated with the CLI application, but the current implementation still maintains backward compatibility with the old data structures and workflows. This has led to some complexity and limitations:

```
src/folib/
├── domain.py                # Data classes (Position, Portfolio, etc.)
├── calculations/            # Pure calculation functions
│   ├── exposure.py          # Exposure calculations
│   ├── options.py           # Option pricing and Greeks
├── data/                    # Data access layer
│   ├── stock.py             # Market data access
│   ├── loader.py            # Portfolio loading
├── services/                # Orchestration layer
    ├── portfolio_service.py # Portfolio processing
    ├── position_service.py  # Position analysis
    ├── simulation_service.py # Portfolio simulation (stub)
```

The current implementation has several limitations:

1. **Backward Compatibility Overhead**: The need to maintain compatibility with the old `PortfolioGroup` structure adds complexity and limits innovation.
2. **Complex Error Handling**: The error handling is complicated by the need to fall back to old implementations when folib processing fails.
3. **Limited Validation**: The validation of input data is limited to ensure compatibility with existing workflows.
4. **Inconsistent APIs**: Some APIs are designed around the old data structures, leading to inconsistencies.

## Target Architecture

The V2 interface will provide a cleaner, more streamlined API without the constraints of backward compatibility:

```
src/folib/v2/
├── domain.py                # Enhanced data classes
├── calculations/            # Pure calculation functions (reused from v1)
├── data/                    # Enhanced data access layer
│   ├── stock.py             # Enhanced market data access
│   ├── loader.py            # Enhanced portfolio loading
├── services/                # Enhanced orchestration layer
    ├── portfolio_service.py # Enhanced portfolio processing
    ├── position_service.py  # Enhanced position analysis
    ├── simulation_service.py # Enhanced portfolio simulation
```

The CLI will be enhanced with new commands that use the V2 interface:

```
src/focli/
├── commands/                # Command handlers
│   ├── portfolio.py         # Existing commands (using folib v1)
│   ├── position.py          # Existing commands (using folib v1)
│   ├── sim.py               # Existing commands (using simulator_v2)
│   ├── portfolio_v2.py      # New commands using folib v2
│   ├── position_v2.py       # New commands using folib v2
│   ├── sim_v2.py            # New commands using folib v2
│   └── ...
├── formatters.py            # Updated for folib v2 data structures
├── utils.py                 # Updated to use folib v2
└── focli.py                 # Main CLI application
```

## Key Improvements in V2

1. **Cleaner Domain Model**:
   - Enhanced `Position` classes with better validation and more consistent APIs
   - Improved `Portfolio` class with more powerful querying and filtering capabilities
   - New `PortfolioAnalysis` class for comprehensive portfolio analysis

2. **Enhanced Data Access**:
   - Improved portfolio loading with better error handling and validation
   - Enhanced market data access with more consistent APIs and better caching
   - Support for multiple data sources and formats

3. **Advanced Services**:
   - Enhanced portfolio service with more sophisticated analysis capabilities
   - Improved position service with better risk metrics and analysis
   - Comprehensive simulation service for portfolio stress testing

4. **Better Error Handling**:
   - More consistent error handling throughout the library
   - Better validation of inputs with clear error messages
   - No need for fallback mechanisms or backward compatibility

## Implementation Plan

### Phase 1: Enhanced Domain Model

1. **Create Enhanced Position Classes**
   - Create a new `Position` base class with improved validation and more consistent APIs
   - Implement specialized position types (`StockPosition`, `OptionPosition`, etc.) with enhanced functionality
   - Add comprehensive validation for all position attributes
   - Implement better string representation and serialization methods

2. **Implement Improved Portfolio Class**
   - Create a new `Portfolio` class with more powerful querying and filtering capabilities
   - Add methods for grouping positions by various criteria (ticker, sector, asset class, etc.)
   - Implement portfolio-level metrics and analysis methods
   - Add support for portfolio comparison and historical analysis

3. **Create PortfolioAnalysis Class**
   - Implement a new `PortfolioAnalysis` class for comprehensive portfolio analysis
   - Add methods for risk analysis, exposure analysis, and performance analysis
   - Implement visualization helpers for common portfolio metrics
   - Add support for scenario analysis and stress testing

### Phase 2: Enhanced Data Access

1. **Improve Portfolio Loading**
   - Create a new `PortfolioLoader` class with better error handling and validation
   - Add support for multiple file formats (CSV, JSON, Excel, etc.)
   - Implement more sophisticated parsing and validation logic
   - Add support for loading historical portfolio data

2. **Enhance Market Data Access**
   - Create a new `MarketDataProvider` interface with more consistent APIs
   - Implement improved providers for various data sources (Yahoo Finance, FMP, etc.)
   - Add better caching mechanisms with more control over cache behavior
   - Implement more sophisticated error handling and retry logic

3. **Add Support for Multiple Data Sources**
   - Create a `DataSourceManager` class for managing multiple data sources
   - Implement fallback mechanisms for when primary data sources fail
   - Add support for combining data from multiple sources
   - Implement data validation and reconciliation logic

### Phase 3: Advanced Services

1. **Enhance Portfolio Service**
   - Create a new `PortfolioService` class with more sophisticated analysis capabilities
   - Implement methods for portfolio optimization and rebalancing
   - Add support for tax-aware portfolio analysis
   - Implement more advanced risk metrics and analysis

2. **Improve Position Service**
   - Create a new `PositionService` class with better risk metrics and analysis
   - Implement more sophisticated option analysis using QuantLib
   - Add support for position-level stress testing
   - Implement more advanced position valuation methods

3. **Develop Comprehensive Simulation Service**
   - Create a new `SimulationService` class for portfolio stress testing
   - Implement Monte Carlo simulation for portfolio analysis
   - Add support for historical scenario analysis
   - Implement more sophisticated market models for simulation

### Phase 4: CLI Integration

1. **Create New CLI Commands**
   - Implement `portfolio2` command for V2 portfolio operations
   - Implement `position2` command for V2 position operations
   - Implement `sim2` command for V2 simulation operations
   - Add comprehensive help text and examples for all new commands

2. **Enhance Display Functions**
   - Create new display functions for V2 data structures
   - Implement more sophisticated formatting and visualization
   - Add support for exporting data to various formats (CSV, JSON, etc.)
   - Implement interactive visualizations where appropriate

3. **Improve Error Handling and User Feedback**
   - Implement more user-friendly error messages
   - Add progress indicators for long-running operations
   - Implement better validation of user input
   - Add more context-sensitive help and suggestions

## Detailed Implementation Tasks

### Task 1: Enhanced Position Classes

```python
# src/folib/v2/domain.py

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum, auto
from typing import List, Optional, Union

class PositionType(Enum):
    STOCK = auto()
    OPTION = auto()
    CASH = auto()
    BOND = auto()
    ETF = auto()
    MUTUAL_FUND = auto()
    UNKNOWN = auto()

@dataclass(frozen=True)
class Position:
    """Base class for all position types."""
    ticker: str
    quantity: Decimal
    market_value: Decimal
    cost_basis: Optional[Decimal] = None
    position_type: PositionType = PositionType.UNKNOWN

    def __post_init__(self):
        """Validate position attributes."""
        if not self.ticker:
            raise ValueError("Ticker cannot be empty")
        if self.quantity == 0:
            raise ValueError("Quantity cannot be zero")

    @property
    def is_long(self) -> bool:
        """Return True if this is a long position."""
        return self.quantity > 0

    @property
    def unrealized_pnl(self) -> Optional[Decimal]:
        """Return the unrealized P&L if cost basis is available."""
        if self.cost_basis is not None:
            return self.market_value - self.cost_basis
        return None

    @property
    def unrealized_pnl_percent(self) -> Optional[Decimal]:
        """Return the unrealized P&L as a percentage if cost basis is available."""
        if self.cost_basis is not None and self.cost_basis != 0:
            return (self.market_value - self.cost_basis) / self.cost_basis
        return None

@dataclass(frozen=True)
class StockPosition(Position):
    """Stock position with additional stock-specific attributes."""
    price: Decimal
    beta: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    def __post_init__(self):
        """Validate stock position attributes."""
        super().__post_init__()
        object.__setattr__(self, 'position_type', PositionType.STOCK)
        if self.price <= 0:
            raise ValueError("Price must be positive")

    @property
    def market_value(self) -> Decimal:
        """Calculate market value based on quantity and price."""
        return self.quantity * self.price

    @property
    def beta_adjusted_exposure(self) -> Optional[Decimal]:
        """Calculate beta-adjusted exposure if beta is available."""
        if self.beta is not None:
            return self.market_value * Decimal(self.beta)
        return None

@dataclass(frozen=True)
class OptionPosition(Position):
    """Option position with additional option-specific attributes."""
    option_type: str  # 'CALL' or 'PUT'
    strike: Decimal
    expiry: date
    price: Decimal
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_volatility: Optional[float] = None
    underlying_price: Optional[Decimal] = None

    def __post_init__(self):
        """Validate option position attributes."""
        super().__post_init__()
        object.__setattr__(self, 'position_type', PositionType.OPTION)
        if self.option_type not in ('CALL', 'PUT'):
            raise ValueError("Option type must be 'CALL' or 'PUT'")
        if self.strike <= 0:
            raise ValueError("Strike must be positive")
        if self.price < 0:
            raise ValueError("Price cannot be negative")

    @property
    def market_value(self) -> Decimal:
        """Calculate market value based on quantity, price, and contract multiplier."""
        # Standard equity options have a multiplier of 100
        return self.quantity * self.price * Decimal(100)

    @property
    def days_to_expiry(self) -> int:
        """Calculate days to expiry."""
        return (self.expiry - date.today()).days

    @property
    def delta_exposure(self) -> Optional[Decimal]:
        """Calculate delta exposure if delta is available."""
        if self.delta is not None and self.underlying_price is not None:
            # Delta exposure is delta * underlying price * quantity * contract multiplier
            return Decimal(self.delta) * self.underlying_price * self.quantity * Decimal(100)
        return None
```

### Task 2: Improved Portfolio Class

```python
# src/folib/v2/domain.py (continued)

@dataclass
class Portfolio:
    """Enhanced portfolio class with powerful querying and filtering capabilities."""
    positions: List[Position] = field(default_factory=list)
    name: str = "Portfolio"
    as_of_date: date = field(default_factory=date.today)

    @property
    def total_value(self) -> Decimal:
        """Calculate the total value of the portfolio."""
        return sum(p.market_value for p in self.positions)

    @property
    def stock_positions(self) -> List[StockPosition]:
        """Return all stock positions in the portfolio."""
        return [p for p in self.positions if isinstance(p, StockPosition)]

    @property
    def option_positions(self) -> List[OptionPosition]:
        """Return all option positions in the portfolio."""
        return [p for p in self.positions if isinstance(p, OptionPosition)]

    def get_positions_by_ticker(self, ticker: str) -> List[Position]:
        """Return all positions for a given ticker."""
        return [p for p in self.positions if p.ticker.upper() == ticker.upper()]

    def get_stock_position_by_ticker(self, ticker: str) -> Optional[StockPosition]:
        """Return the stock position for a given ticker, if any."""
        for p in self.stock_positions:
            if p.ticker.upper() == ticker.upper():
                return p
        return None

    def get_option_positions_by_ticker(self, ticker: str) -> List[OptionPosition]:
        """Return all option positions for a given ticker."""
        return [p for p in self.option_positions if p.ticker.upper() == ticker.upper()]

    def filter_positions(self, **kwargs) -> List[Position]:
        """Filter positions based on various criteria."""
        result = self.positions

        if 'ticker' in kwargs:
            ticker = kwargs['ticker'].upper()
            result = [p for p in result if p.ticker.upper() == ticker]

        if 'position_type' in kwargs:
            position_type = kwargs['position_type']
            result = [p for p in result if p.position_type == position_type]

        if 'min_value' in kwargs:
            min_value = kwargs['min_value']
            result = [p for p in result if p.market_value >= min_value]

        if 'max_value' in kwargs:
            max_value = kwargs['max_value']
            result = [p for p in result if p.market_value <= max_value]

        if 'is_long' in kwargs:
            is_long = kwargs['is_long']
            result = [p for p in result if p.is_long == is_long]

        return result

    def group_positions_by_ticker(self) -> dict:
        """Group positions by ticker."""
        result = {}
        for p in self.positions:
            if p.ticker not in result:
                result[p.ticker] = []
            result[p.ticker].append(p)
        return result

    def group_positions_by_sector(self) -> dict:
        """Group stock positions by sector."""
        result = {}
        for p in self.stock_positions:
            if p.sector:
                if p.sector not in result:
                    result[p.sector] = []
                result[p.sector].append(p)
        return result
```

## Migration Strategy

The migration to the V2 interface will follow these steps:

1. **Parallel Development**: Develop the V2 interface in parallel with the existing implementation
2. **No Backward Compatibility**: The V2 interface will not maintain backward compatibility with the old implementation
3. **New CLI Commands**: Create new CLI commands that use the V2 interface, keeping the existing commands for backward compatibility
4. **Gradual Transition**: Encourage users to migrate to the new commands over time
5. **Documentation**: Provide comprehensive documentation for the V2 interface and migration guides

## Conclusion

The V2 interface will provide a cleaner, more streamlined API for portfolio management and analysis. By removing the constraints of backward compatibility, we can create a more innovative and powerful library that better meets the needs of users.

The implementation will be done in phases, starting with the enhanced domain model, then improving the data access layer, and finally developing advanced services. The CLI integration will be done in parallel, providing users with new commands that leverage the full power of the V2 interface.

This approach allows us to deliver a significantly improved user experience while maintaining backward compatibility through the existing commands. Over time, users can migrate to the new commands as they become comfortable with the new interface.
