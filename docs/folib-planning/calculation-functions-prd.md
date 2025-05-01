---
description: PRD for implementing folib calculation functions
date: "2025-04-30"
status: "DRAFT"
---

# Calculation Functions Implementation PRD

## Overview

This document outlines the implementation plan for the core calculation functions in `folib`, focusing on options statistics and exposure calculations needed for CLI integration.

## Goals

1. Implement core options calculations (Greeks)
2. Implement exposure calculations for all position types
3. Enable portfolio-level aggregation
4. Support CLI integration for basic portfolio analysis

## Success Metrics

1. All calculations match existing implementation in legacy codebase
2. Unit test coverage > 90% for calculation modules
3. CLI can successfully:
   - Load a portfolio
   - Display position-level exposures
   - Show portfolio-level summary

## Technical Requirements

### 1. Options Calculations (`calculations/options.py`)

#### Core Functions

```python
def calculate_option_delta(
    strike: float,
    expiry: date,
    underlying_price: float,
    option_type: Literal["CALL", "PUT"],
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate the delta of an option using the Black-Scholes model.

    Args:
        strike: The strike price of the option
        expiry: Expiration date of the option
        underlying_price: Current price of the underlying stock
        option_type: Either "CALL" or "PUT"
        volatility: Implied or historical volatility (default 30%)
        risk_free_rate: Risk-free rate (default 5%)

    Returns:
        float: The option's delta (-1.0 to 1.0)
    """
```

```python
def calculate_option_gamma(
    strike: float,
    expiry: date,
    underlying_price: float,
    option_type: Literal["CALL", "PUT"],
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate the gamma of an option using the Black-Scholes model.
    """
```

```python
def calculate_option_theta(
    strike: float,
    expiry: date,
    underlying_price: float,
    option_type: Literal["CALL", "PUT"],
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate the theta of an option using the Black-Scholes model.
    """
```

```python
def calculate_option_vega(
    strike: float,
    expiry: date,
    underlying_price: float,
    option_type: Literal["CALL", "PUT"],
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate the vega of an option using the Black-Scholes model.
    """
```

#### Helper Functions

```python
def calculate_days_to_expiry(expiry: date) -> float:
    """Calculate trading days remaining until expiry."""
```

```python
def is_option_in_the_money(
    strike: float,
    underlying_price: float,
    option_type: Literal["CALL", "PUT"]
) -> bool:
    """Determine if an option is in the money."""
```

### 2. Exposure Calculations (`calculations/exposure.py`)

#### Stock Exposure

```python
def calculate_stock_exposure(
    quantity: float,
    price: float,
    include_sign: bool = True
) -> float:
    """
    Calculate the market exposure of a stock position.

    Args:
        quantity: Number of shares (negative for short positions)
        price: Current market price per share
        include_sign: If True, return signed exposure (default True)

    Returns:
        float: Market exposure in dollars
    """
```

#### Option Exposure

```python
def calculate_option_exposure(
    quantity: float,
    underlying_price: float,
    delta: float,
    include_sign: bool = True
) -> float:
    """
    Calculate the market exposure of an option position.

    Args:
        quantity: Number of contracts (negative for short positions)
        underlying_price: Price of underlying stock
        delta: Option delta (-1.0 to 1.0)
        include_sign: If True, return signed exposure (default True)

    Returns:
        float: Market exposure in dollars
    """
```

#### Portfolio-Level Calculations

```python
def aggregate_exposures(
    exposures: list[float],
    weights: list[float] | None = None
) -> float:
    """
    Aggregate multiple exposures, optionally with weights.

    Args:
        exposures: List of position exposures
        weights: Optional list of weights (e.g., betas)

    Returns:
        float: Total exposure
    """
```

## Integration Example

Here's how these functions will be used in the CLI:

```python
# In focli/commands/analyze.py
def analyze_position(position: Union[StockPosition, OptionPosition]) -> dict:
    """Analyze a single position."""
    if position.position_type == "stock":
        exposure = calculate_stock_exposure(
            quantity=position.quantity,
            price=position.price
        )
        return {
            "type": "stock",
            "exposure": exposure,
            "value": position.quantity * position.price
        }
    else:  # option
        delta = calculate_option_delta(
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=position.underlying_price,
            option_type=position.option_type
        )
        exposure = calculate_option_exposure(
            quantity=position.quantity,
            underlying_price=position.underlying_price,
            delta=delta
        )
        return {
            "type": "option",
            "exposure": exposure,
            "delta": delta,
            "gamma": calculate_option_gamma(...),
            "theta": calculate_option_theta(...),
            "days_to_expiry": calculate_days_to_expiry(position.expiry)
        }
```

## Integration Plan

### 1. Services Layer Integration (`folib/services/`)

The calculation functions will be integrated into the service layer through two main services:

#### PositionService (`services/position_service.py`)
```python
def analyze_position(
    position: Union[StockPosition, OptionPosition],
    market_data: MarketData,
) -> PositionAnalysis:
    """
    Analyze a single position, calculating all relevant metrics.

    Returns:
        PositionAnalysis containing:
        - Market value
        - Exposure (delta/beta-adjusted)
        - Greeks (for options)
        - P&L metrics
    """
    if isinstance(position, StockPosition):
        return {
            "exposure": calculate_stock_exposure(
                position.quantity,
                position.price
            ),
            "beta_adjusted_exposure": calculate_stock_exposure(
                position.quantity,
                position.price,
                market_data.get_beta(position.ticker)
            ),
            "market_value": position.quantity * position.price,
        }
    else:  # OptionPosition
        greeks = calculate_option_greeks(
            strike=position.strike,
            expiry=position.expiry,
            underlying_price=market_data.get_price(position.ticker),
            option_type=position.option_type
        )
        return {
            "delta": greeks["delta"],
            "exposure": calculate_option_exposure(
                position.quantity,
                market_data.get_price(position.ticker),
                greeks["delta"]
            ),
            "beta_adjusted_exposure": calculate_option_exposure(
                position.quantity,
                market_data.get_price(position.ticker),
                greeks["delta"],
                market_data.get_beta(position.ticker)
            ),
            "market_value": position.quantity * position.price * 100,
        }
```

#### PortfolioService (`services/portfolio_service.py`)
```python
def calculate_portfolio_exposures(
    portfolio: Portfolio,
    market_data: MarketData,
) -> PortfolioExposure:
    """
    Calculate portfolio-level exposure metrics.
    """
    position_exposures = [
        analyze_position(pos, market_data)
        for pos in portfolio.positions
    ]

    return {
        "total_exposure": aggregate_exposures(
            [p["exposure"] for p in position_exposures]
        ),
        "beta_adjusted_exposure": aggregate_exposures(
            [p["beta_adjusted_exposure"] for p in position_exposures]
        ),
        "position_exposures": position_exposures,
    }
```

### 2. CLI Integration (`focli/commands/`)

The CLI will access the calculation functions through the service layer:

#### analyze.py
```python
@click.command()
@click.argument("position_id")
def analyze(position_id: str):
    """Analyze a specific position."""
    position = portfolio_service.get_position(position_id)
    analysis = position_service.analyze_position(
        position,
        market_data
    )

    # Format output
    click.echo(f"Position Analysis for {position_id}")
    click.echo(f"Exposure: ${analysis['exposure']:,.2f}")
    if "delta" in analysis:
        click.echo(f"Delta: {analysis['delta']:.3f}")
```

#### portfolio.py
```python
@click.command()
def summary():
    """Show portfolio summary."""
    portfolio = portfolio_service.get_current_portfolio()
    exposure = portfolio_service.calculate_portfolio_exposures(
        portfolio,
        market_data
    )

    # Format output
    click.echo(f"Total Exposure: ${exposure['total_exposure']:,.2f}")
    click.echo(f"Beta-Adjusted: ${exposure['beta_adjusted_exposure']:,.2f}")
```

### 3. Integration Testing

Two levels of integration tests will be needed:

1. **Service Layer Tests** (`tests/test_services/`)
   - Test position analysis with market data
   - Test portfolio aggregation
   - Test edge cases (expired options, missing data)

2. **CLI Tests** (`tests/test_cli/`)
   - Test command output formatting
   - Test error handling
   - Test data loading flows

### 4. Implementation Steps

1. ✅ Complete calculation function implementations
2. ✅ Add unit tests for calculations
3. Create service layer integration
   - [ ] Implement PositionService
   - [ ] Implement PortfolioService
   - [ ] Add service layer tests
4. Integrate with CLI
   - [ ] Add position analysis command
   - [ ] Add portfolio summary command
   - [ ] Add CLI tests
5. Documentation
   - [ ] Add service layer API docs
   - [ ] Update CLI usage docs
   - [ ] Add integration examples

### 5. Success Criteria

The integration will be considered successful when:

1. All calculation functions are accessible through the service layer
2. CLI can display position-level Greeks and exposures
3. CLI can show portfolio-level exposure aggregation
4. All integration tests pass
5. Documentation is complete and up-to-date

## Implementation Phases

### Phase 1: Core Calculations (Current)
- [ ] Implement base Black-Scholes functions
- [ ] Implement delta calculation
- [ ] Implement basic exposure calculations
- [ ] Add unit tests for core functions

### Phase 2: Extended Greeks
- [ ] Implement gamma calculation
- [ ] Implement theta calculation
- [ ] Implement vega calculation
- [ ] Add unit tests for Greeks

### Phase 3: Integration & Testing
- [ ] Integrate with CLI position analysis
- [ ] Add portfolio-level aggregation
- [ ] Add integration tests
- [ ] Document usage examples

## Dependencies

1. **Libraries**
   - `numpy` for numerical calculations
   - `scipy` for statistical functions
   - `pandas` for data handling

2. **Internal**
   - `domain.py` data models
   - Market data provider for prices

## Testing Strategy

1. **Unit Tests**
   - Test each Greek calculation against known values
   - Test exposure calculations with edge cases
   - Test aggregation with various weights

2. **Property Tests**
   - Delta should be between -1 and 1
   - Put/Call parity relationships
   - Exposure signs should match position direction

3. **Integration Tests**
   - Load sample portfolio
   - Calculate all Greeks
   - Verify portfolio-level aggregation

## Error Handling

Following the project's "fail fast" principle:

1. **Input Validation**
   - Validate option types
   - Check date ranges
   - Verify price > 0

2. **Edge Cases**
   - Handle deep ITM/OTM options
   - Handle very short/long expiries
   - Handle zero/negative prices

## Documentation

1. **Function Documentation**
   - Clear docstrings with examples
   - Type hints for all functions
   - Edge case documentation

2. **Usage Examples**
   - Basic usage patterns
   - Portfolio-level calculations
   - Common error cases

## Success Criteria

The implementation will be considered successful when:

1. All calculations match market standards
2. CLI can successfully analyze positions
3. Test coverage exceeds 90%
4. Documentation is complete
5. Edge cases are handled gracefully
