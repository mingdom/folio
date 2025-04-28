# Data Model Refactoring Plan

## WHY: Current Issues with the Data Model

The current data model in Folio has several issues that make it difficult to work with and maintain:

1. **Duplication of Data**: There is significant duplication of data between `StockPosition`, `OptionPosition`, and `PortfolioGroup` classes. This leads to inconsistencies and makes it difficult to ensure that all related data is updated together.

2. **Awkward Inheritance Structure**: The inheritance relationship between `Position`, `StockPosition`, and `OptionPosition` adds complexity without providing significant benefits. `StockPosition` doesn't even inherit from `Position`, creating inconsistency.

3. **Missing Underlying Price in Options**: The `OptionPosition` class doesn't directly store the underlying price, which is critical for option pricing and simulation. This forces awkward workarounds in functions like `simulate_position_group`.

4. **Parallel Class Hierarchies**: We have both `OptionPosition` in `data_model.py` and `OptionContract` in `options.py`, which represent similar concepts but are used in different contexts. This creates confusion and duplication.

5. **Tight Coupling**: The current model tightly couples positions with their pricing and simulation logic, making it difficult to change one without affecting the other.

6. **Lack of a Central Oracle**: There's no central place to get basic data for a ticker, forcing each component to maintain its own copy of this data.

7. **Complex Initialization**: Classes like `OptionPosition` have complex initialization with many parameters, making them difficult to use correctly.

## WHAT: Proposed Data Model

We propose a new data model that addresses these issues by:

1. **Separating Core Data from Derived Data**: Clearly distinguish between core data (e.g., ticker, quantity) and derived data (e.g., market value, exposures).

2. **Unifying Option Representations**: Consolidate `OptionPosition` and `OptionContract` into a single class.

3. **Creating a Market Data Oracle**: Introduce a central service for accessing market data.

4. **Simplifying the Class Hierarchy**: Replace inheritance with composition where appropriate.

5. **Making Underlying Price Explicit**: Ensure that option positions always have access to their underlying price.

### Core Classes

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  MarketOracle   │     │    Position     │     │ PositionGroup   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ get_price()     │     │ ticker          │     │ ticker          │
│ get_beta()      │◄────│ quantity        │◄────│ positions       │
│ get_volatility()│     │ position_type   │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               ▲
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
        ┌─────────────────┐         ┌─────────────────┐
        │  StockPosition  │         │  OptionPosition │
        ├─────────────────┤         ├─────────────────┤
        │ cost_basis      │         │ strike          │
        │                 │         │ expiry          │
        └─────────────────┘         │ option_type     │
                                    │ cost_basis      │
                                    └─────────────────┘
```

### Calculation Services

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ ValueCalculator │     │ ExposureCalc    │     │    Simulator    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ calc_stock_val()│     │ calc_exposure() │     │ sim_position()  │
│ calc_option_val()     │ calc_beta_adj() │     │ sim_group()     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## HOW: Implementation Plan

### Phase 1: Create the Market Oracle

1. Create a `MarketOracle` class that provides access to market data:
   - `get_price(ticker)`: Get the current price for a ticker
   - `get_beta(ticker)`: Get the beta for a ticker
   - `get_volatility(ticker)`: Get the implied volatility for a ticker
   - `get_option_data(ticker, strike, expiry, option_type)`: Get data for a specific option

2. Implement caching in the `MarketOracle` to avoid repeated API calls.

3. Update existing code to use the `MarketOracle` instead of storing duplicate data.

### Phase 2: Simplify the Position Classes

1. Create a new `Position` base class with minimal core attributes:
   - `ticker`: The ticker symbol
   - `quantity`: The number of shares/contracts
   - `position_type`: "stock" or "option"

2. Create a new `StockPosition` class that extends `Position` with:
   - `cost_basis`: The cost basis per share

3. Create a new `OptionPosition` class that extends `Position` with:
   - `strike`: The strike price
   - `expiry`: The expiration date
   - `option_type`: "CALL" or "PUT"
   - `cost_basis`: The cost basis per contract

4. Ensure that all position classes have a `to_dict()` and `from_dict()` method for serialization.

### Phase 3: Create Calculation Services

1. Create a `ValueCalculator` service with methods:
   - `calculate_stock_value(position, price)`: Calculate the value of a stock position
   - `calculate_option_value(position, underlying_price)`: Calculate the value of an option position

2. Create an `ExposureCalculator` service with methods:
   - `calculate_exposure(position, price)`: Calculate the market exposure of a position
   - `calculate_beta_adjusted_exposure(position, price, beta)`: Calculate the beta-adjusted exposure

3. Create a `Simulator` service with methods:
   - `simulate_position(position, price_change)`: Simulate a position with a price change
   - `simulate_group(group, price_change)`: Simulate a group of positions with a price change

### Phase 4: Refactor the Position Group

1. Simplify the `PortfolioGroup` class to contain:
   - `ticker`: The ticker symbol
   - `positions`: A list of positions (both stock and option)

2. Remove the duplicate metrics from `PortfolioGroup` and calculate them on-demand using the calculation services.

3. Update the `create_portfolio_group` function to use the new classes.

### Phase 5: Update Dependent Code

1. Update the simulator code to use the new data model and calculation services.

2. Update the portfolio analysis code to use the new data model.

3. Update the CLI and web interface to use the new data model.

## Migration Strategy

To minimize disruption, we'll implement this refactoring in stages:

1. Create the new classes alongside the existing ones.

2. Create adapter functions that convert between the old and new data models.

3. Update one component at a time to use the new data model.

4. Once all components are updated, remove the old data model.

## Testing Strategy

1. Create comprehensive unit tests for the new classes and services.

2. Create integration tests that verify the new data model works with existing code.

3. Create end-to-end tests that verify the entire system works with the new data model.

## Benefits of the New Design

1. **Reduced Duplication**: By centralizing market data in the `MarketOracle`, we eliminate duplication and inconsistencies.

2. **Clearer Responsibilities**: Each class has a single, well-defined responsibility.

3. **Easier Simulation**: The `Simulator` service can handle any type of position without special cases.

4. **More Flexible**: The new design makes it easier to add new position types or calculation methods.

5. **Better Testability**: The separation of concerns makes it easier to test each component in isolation.

6. **Improved Developer Experience**: The simpler class hierarchy and clearer responsibilities make the code easier to understand and maintain.

## Risks and Mitigations

1. **Risk**: Breaking existing code during the refactoring.
   **Mitigation**: Implement the changes incrementally with thorough testing at each step.

2. **Risk**: Performance degradation due to additional abstraction layers.
   **Mitigation**: Profile the code before and after the refactoring to identify and address any performance issues.

3. **Risk**: Increased complexity during the transition period.
   **Mitigation**: Clearly document the migration strategy and provide adapter functions to ease the transition.

## Conclusion

This refactoring plan addresses the core issues with the current data model while providing a clear path forward. By separating core data from derived data, centralizing market data access, and simplifying the class hierarchy, we can create a more maintainable and flexible codebase.

The proposed changes will make it easier to implement new features, fix bugs, and onboard new developers. The clearer separation of concerns will also make the code more testable and robust.
