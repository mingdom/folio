---
status: DONE
---

# Simulator V2 Atomic Implementation Plan

## Core Design Philosophy

This implementation plan takes a ground-up approach, focusing on creating **atomic functions** with clean interfaces that:

1. Have a single, well-defined responsibility
2. Are type-specific rather than generic
3. Can be composed to build more complex functionality
4. Will serve as building blocks for both the simulator and future PNL refactoring

## Phase 1 Checklist

### Phase 1A: Core Calculation Functions ✅
- [x] Create basic module structure for `src/folio/simulator_v2.py`
- [x] Implement price adjustment functions
  - [x] `calculate_price_adjustment(spy_change, beta)`
  - [x] `calculate_underlying_price(current_price, adjustment_factor)`
- [x] Implement stock valuation functions
  - [x] `calculate_stock_value(quantity, price)`
  - [x] `calculate_stock_pnl(quantity, entry_price, current_price)`
- [x] Implement option valuation functions
  - [x] `prepare_contract_for_pricing(option_type, strike, expiry, underlying_price)`
  - [x] `calculate_option_value(option_type, strike, expiry, underlying_price, quantity, volatility, risk_free_rate)`
  - [x] `calculate_option_pnl(option_type, strike, expiry, underlying_price, quantity, entry_price, volatility, risk_free_rate)`
- [x] Create focused unit tests for core functions

### Phase 1B: Composition and Integration ✅
- [x] Implement position-level functions
  - [x] `simulate_stock_position(position, new_price)`
  - [x] `simulate_option_position(position, new_underlying_price)`
  - [x] `simulate_position_group(position_group, spy_change)`
- [x] Implement portfolio-level functions
  - [x] `simulate_portfolio(portfolio_groups, spy_changes, cash_value, pending_activity_value)`
- [x] Create minimal unit tests
  - [x] Basic tests for position-level functions
  - [x] Basic tests for portfolio-level functions
  - [x] Defer complex testing until CLI integration

### Phase 1C: CLI Integration ✅
- [x] Create a new `sim` command in the CLI
  - [x] Create `src/focli/commands/sim.py` using simulator_v2
  - [x] Implement clean, focused command interface
  - [x] Register the new command in the CLI shell
- [x] Implement rich output formatting
  - [x] Create formatters for position-level results
  - [x] Add detailed breakdowns of simulation results
  - [x] Implement colorized output for gains/losses
- [x] Add command options and parameters
  - [x] Support for SPY change range and steps
  - [x] Support for focusing on specific tickers
  - [x] Support for detailed position-level output
  - [x] Added `--analyze-correlation` option for identifying positions that perform poorly when SPY increases
- [x] Add `make sim` target for easy testing
  - [x] Update Makefile to add a `sim` target (as an alias to `simulate`)
  - [x] Configure target to run the `sim` command with default parameters
  - [x] Add documentation for the new target
- [x] Test with private portfolio data
  - [x] Support loading `@private-data/private-portfolio.csv` for testing
  - [x] Verify correct handling of the SPY > 3.3% issue
  - [x] Compare results with the original simulator
  - [x] Added portfolio contribution analysis
- [x] Additional features beyond original plan
  - [x] Added SPY price display at each change level
  - [x] Added P&L % of original portfolio value metric
  - [x] Added correlation analysis to identify positions that lose money when SPY increases

## Atomic Function Design

### Price Adjustment Functions

```python
def calculate_price_adjustment(spy_change: float, beta: float) -> float:
    """
    Calculate price adjustment factor based on SPY change and beta.

    Args:
        spy_change: SPY price change as a decimal (e.g., 0.05 for 5% increase)
        beta: Beta of the position

    Returns:
        Price adjustment factor (e.g., 1.05 for 5% increase)
    """
    return 1.0 + (spy_change * beta)


def calculate_underlying_price(current_price: float, adjustment_factor: float) -> float:
    """
    Calculate new underlying price based on current price and adjustment factor.

    Args:
        current_price: Current price of the underlying
        adjustment_factor: Price adjustment factor

    Returns:
        New underlying price
    """
    return current_price * adjustment_factor
```

### Stock Valuation Functions

```python
def calculate_stock_value(quantity: float, price: float) -> float:
    """
    Calculate the market value of a stock position.

    Args:
        quantity: Number of shares
        price: Price per share

    Returns:
        Market value of the stock position
    """
    return quantity * price


def calculate_stock_pnl(
    quantity: float,
    entry_price: float,
    current_price: float
) -> float:
    """
    Calculate the profit/loss for a stock position.

    Args:
        quantity: Number of shares
        entry_price: Entry price per share
        current_price: Current price per share

    Returns:
        Profit/loss amount
    """
    return quantity * (current_price - entry_price)
```

### Option Valuation Functions

```python
def calculate_option_value(
    option_type: str,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    quantity: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate the theoretical value of an option using Black-Scholes.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Expiration date
        underlying_price: Price of the underlying asset
        quantity: Number of contracts
        volatility: Implied volatility (default: 0.3)
        risk_free_rate: Risk-free interest rate (default: 0.05)

    Returns:
        Theoretical value of the option position
    """
    # Create an option contract
    contract = OptionContract(
        option_type=option_type,
        strike=strike,
        expiry=expiry,
        underlying_price=underlying_price
    )

    # Calculate option price using Black-Scholes
    option_price = calculate_bs_price(
        contract,
        underlying_price,
        risk_free_rate,
        volatility
    )

    # Calculate position value (each contract is for 100 shares)
    return option_price * quantity * 100


def calculate_option_pnl(
    option_type: str,
    strike: float,
    expiry: datetime.date,
    underlying_price: float,
    quantity: float,
    entry_price: float,
    volatility: float = 0.3,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate the profit/loss for an option position.

    Args:
        option_type: "CALL" or "PUT"
        strike: Strike price
        expiry: Expiration date
        underlying_price: Price of the underlying asset
        quantity: Number of contracts
        entry_price: Entry price per contract
        volatility: Implied volatility (default: 0.3)
        risk_free_rate: Risk-free interest rate (default: 0.05)

    Returns:
        Profit/loss amount
    """
    # Calculate current option value
    current_value = calculate_option_value(
        option_type,
        strike,
        expiry,
        underlying_price,
        quantity,
        volatility,
        risk_free_rate
    )

    # Calculate entry value
    entry_value = entry_price * quantity * 100

    # Calculate P&L
    return current_value - entry_value
```

### Position Simulation Functions

```python
def simulate_stock_position(
    position: StockPosition,
    new_price: float
) -> Dict[str, Any]:
    """
    Simulate a stock position with a new price.

    Args:
        position: Stock position to simulate
        new_price: New price of the underlying

    Returns:
        Dictionary with simulation results
    """
    # Calculate original value
    original_value = calculate_stock_value(position.quantity, position.price)

    # Calculate new value
    new_value = calculate_stock_value(position.quantity, new_price)

    # Calculate P&L
    pnl = calculate_stock_pnl(position.quantity, position.price, new_price)

    # Calculate P&L percentage
    pnl_percent = (pnl / original_value) * 100 if original_value else 0

    return {
        "ticker": position.ticker,
        "position_type": "stock",
        "original_price": position.price,
        "new_price": new_price,
        "original_value": original_value,
        "new_value": new_value,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
    }


def simulate_option_position(
    position: OptionPosition,
    new_underlying_price: float
) -> Dict[str, Any]:
    """
    Simulate an option position with a new underlying price.

    Args:
        position: Option position to simulate
        new_underlying_price: New price of the underlying

    Returns:
        Dictionary with simulation results
    """
    # Calculate original value
    original_value = position.market_value

    # Calculate new value
    new_value = calculate_option_value(
        position.option_type,
        position.strike,
        position.expiry,
        new_underlying_price,
        position.quantity,
        getattr(position, "implied_volatility", 0.3)
    )

    # Calculate P&L
    pnl = new_value - original_value

    # Calculate P&L percentage
    pnl_percent = (pnl / original_value) * 100 if original_value else 0

    return {
        "ticker": position.ticker,
        "position_type": "option",
        "option_type": position.option_type,
        "strike": position.strike,
        "expiry": position.expiry,
        "original_underlying_price": position.underlying_price,
        "new_underlying_price": new_underlying_price,
        "original_value": original_value,
        "new_value": new_value,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
    }


def simulate_position_group(
    position_group: PortfolioGroup,
    spy_change: float
) -> Dict[str, Any]:
    """
    Simulate a position group with a given SPY change.

    Args:
        position_group: Position group to simulate
        spy_change: SPY price change as a decimal

    Returns:
        Dictionary with simulation results
    """
    # Calculate price adjustment based on beta
    beta = position_group.beta
    price_adjustment = calculate_price_adjustment(spy_change, beta)

    # Calculate new underlying price
    current_price = position_group.price
    new_price = calculate_underlying_price(current_price, price_adjustment)

    # Initialize results
    position_results = []
    total_original_value = 0
    total_new_value = 0
    total_pnl = 0

    # Simulate stock position
    if position_group.stock_position:
        stock_result = simulate_stock_position(position_group.stock_position, new_price)
        position_results.append(stock_result)
        total_original_value += stock_result["original_value"]
        total_new_value += stock_result["new_value"]
        total_pnl += stock_result["pnl"]

    # Simulate option positions
    if position_group.option_positions:
        for option in position_group.option_positions:
            option_result = simulate_option_position(option, new_price)
            position_results.append(option_result)
            total_original_value += option_result["original_value"]
            total_new_value += option_result["new_value"]
            total_pnl += option_result["pnl"]

    # Calculate group-level metrics
    pnl_percent = (total_pnl / total_original_value) * 100 if total_original_value else 0

    return {
        "ticker": position_group.ticker,
        "beta": beta,
        "current_price": current_price,
        "new_price": new_price,
        "original_value": total_original_value,
        "new_value": total_new_value,
        "pnl": total_pnl,
        "pnl_percent": pnl_percent,
        "positions": position_results,
    }
```

### Portfolio Simulation Function

```python
def simulate_portfolio(
    portfolio_groups: List[PortfolioGroup],
    spy_changes: List[float],
    cash_value: float = 0.0,
    pending_activity_value: float = 0.0,
) -> Dict[str, Any]:
    """
    Simulate portfolio performance across different SPY price changes.

    Args:
        portfolio_groups: Portfolio groups to simulate
        spy_changes: List of SPY price change percentages as decimals
        cash_value: Value of cash positions
        pending_activity_value: Value of pending activity

    Returns:
        Dictionary with simulation results
    """
    if not portfolio_groups:
        return {
            "spy_changes": [],
            "portfolio_values": [],
            "portfolio_pnls": [],
            "position_results": {},
        }

    # Initialize results containers
    portfolio_values = []
    portfolio_pnls = []
    position_results = {group.ticker: [] for group in portfolio_groups}

    # Calculate current portfolio value
    current_portfolio_value = sum(
        (group.stock_position.market_value if group.stock_position else 0) +
        sum(op.market_value for op in group.option_positions) if group.option_positions else 0
        for group in portfolio_groups
    ) + cash_value + pending_activity_value

    # Simulate for each SPY change
    for spy_change in spy_changes:
        portfolio_value = cash_value + pending_activity_value
        portfolio_pnl = 0.0

        # Simulate each position group
        for group in portfolio_groups:
            group_result = simulate_position_group(group, spy_change)
            portfolio_value += group_result["new_value"]
            portfolio_pnl += group_result["pnl"]
            position_results[group.ticker].append(group_result)

        # Store portfolio-level results
        portfolio_values.append(portfolio_value)
        portfolio_pnls.append(portfolio_pnl)

    # Calculate portfolio-level metrics
    portfolio_pnl_percents = [
        (pnl / current_portfolio_value) * 100 if current_portfolio_value else 0
        for pnl in portfolio_pnls
    ]

    return {
        "spy_changes": spy_changes,
        "portfolio_values": portfolio_values,
        "portfolio_pnls": portfolio_pnls,
        "portfolio_pnl_percents": portfolio_pnl_percents,
        "current_portfolio_value": current_portfolio_value,
        "position_results": position_results,
    }
```

## Benefits of This Atomic Approach

1. **Single Responsibility**: Each function does exactly one thing and does it well
2. **Type Safety**: Functions are specific to the type of position they handle
3. **Composability**: Functions can be combined to build more complex functionality
4. **Reusability**: These atomic functions can be used by both the simulator and PNL modules
5. **Maintainability**: Functions are easier to understand, test, and modify
6. **Future-Proofing**: Clean interfaces that will stand the test of time

## Implementation Strategy

1. **Bottom-Up Implementation**: Start with the most atomic functions and build up
2. **Test-Driven Development**: Write tests for each function before implementing it
3. **Incremental Integration**: Gradually integrate the functions into the simulator
4. **Validation**: Verify that the simulator produces correct results, especially for the SPY > 3.3% case

## Implementation Timeline

### Phase 1A: Core Calculation Functions (3-4 days)
- Day 1: Implement price adjustment and stock valuation functions
- Day 2: Implement option valuation functions
- Day 3-4: Create and run tests, fix any issues

### Phase 1B: Composition and Integration (3-4 days)
- Day 1-2: Implement position and group-level functions
- Day 3: Implement portfolio-level functions
- Day 4: Create and run tests, fix any issues

### Phase 1C: CLI Integration (4-5 days)
- Day 1: Create new `sim` command using simulator_v2
- Day 2: Implement command options and parameters
- Day 3: Implement rich output formatting and add `make simulate` target
- Day 4: Test with private portfolio data, focusing on the SPY > 3.3% issue
- Day 5: Manual testing, refinement, and documentation

### Total Timeline: 10-13 days

This timeline ensures we have a fully functional `sim` command by the end of Phase 1, with all the necessary features to effectively test and validate the new simulator implementation.

## Future Refactoring Path

After successful CLI integration and validation, we can consider refactoring the PNL module to use these atomic functions:

1. **Identify Overlap**: Determine which parts of the PNL module can use our new functions
2. **Gradual Refactoring**: Replace PNL calculations with calls to our atomic functions
3. **Maintain Backward Compatibility**: Ensure existing code continues to work
4. **Comprehensive Testing**: Verify that the refactored PNL module produces the same results

This phased approach gives us a clear path to improving the entire codebase while ensuring that the simulator-v2 is built on a solid foundation of well-designed, atomic functions. By integrating with the CLI first, we can validate our implementation in a real-world context before attempting more complex integrations with the PNL charts.
