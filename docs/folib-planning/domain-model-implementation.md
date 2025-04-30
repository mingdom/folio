# Domain Model Implementation Plan

This document provides a detailed implementation plan for the simplified domain model, including code examples and migration steps.

## 1. Refactored Domain Model

### Updated `domain.py`

```python
"""
Core domain models for the Folib library.

This module contains the fundamental data structures used throughout the library.
All classes are simple data containers with minimal methods and a clear inheritance hierarchy.

Key design principles:
- Uses frozen dataclasses for immutability
- Uses composition over inheritance where appropriate
- Provides minimal computed properties
- Uses strong type hints throughout
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, TypeVar, Generic, cast

# Type variable for position types
P = TypeVar('P', bound='Position')

@dataclass(frozen=True)
class Position:
    """Base position data with common fields for all position types."""
    ticker: str
    quantity: float
    price: float
    cost_basis: float | None = None
    position_type: Literal["stock", "option", "cash", "unknown"]

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price


@dataclass(frozen=True)
class StockPosition(Position):
    """Stock position data."""

    def __init__(self, ticker: str, quantity: float, price: float, cost_basis: float | None = None):
        object.__setattr__(self, 'ticker', ticker)
        object.__setattr__(self, 'quantity', quantity)
        object.__setattr__(self, 'price', price)
        object.__setattr__(self, 'cost_basis', cost_basis)
        object.__setattr__(self, 'position_type', "stock")


@dataclass(frozen=True)
class OptionPosition(Position):
    """Option position data."""
    strike: float
    expiry: date
    option_type: Literal["CALL", "PUT"]

    def __init__(
        self,
        ticker: str,
        quantity: float,
        price: float,
        strike: float,
        expiry: date,
        option_type: Literal["CALL", "PUT"],
        cost_basis: float | None = None
    ):
        object.__setattr__(self, 'ticker', ticker)
        object.__setattr__(self, 'quantity', quantity)
        object.__setattr__(self, 'price', price)
        object.__setattr__(self, 'cost_basis', cost_basis)
        object.__setattr__(self, 'position_type', "option")
        object.__setattr__(self, 'strike', strike)
        object.__setattr__(self, 'expiry', expiry)
        object.__setattr__(self, 'option_type', option_type)

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price * 100  # 100 shares per contract


@dataclass(frozen=True)
class CashPosition(Position):
    """Cash or cash-equivalent position."""

    def __init__(self, ticker: str, quantity: float, price: float, cost_basis: float | None = None):
        object.__setattr__(self, 'ticker', ticker)
        object.__setattr__(self, 'quantity', quantity)
        object.__setattr__(self, 'price', price)
        object.__setattr__(self, 'cost_basis', cost_basis)
        object.__setattr__(self, 'position_type', "cash")


@dataclass(frozen=True)
class UnknownPosition(Position):
    """Position that couldn't be classified as stock, option, or cash."""
    description: str

    def __init__(self, ticker: str, quantity: float, price: float, description: str, cost_basis: float | None = None):
        object.__setattr__(self, 'ticker', ticker)
        object.__setattr__(self, 'quantity', quantity)
        object.__setattr__(self, 'price', price)
        object.__setattr__(self, 'cost_basis', cost_basis)
        object.__setattr__(self, 'position_type', "unknown")
        object.__setattr__(self, 'description', description)


@dataclass(frozen=True)
class Portfolio:
    """Container for the entire portfolio."""
    positions: list[Position]
    pending_activity_value: float = 0.0

    @property
    def stock_positions(self) -> list[StockPosition]:
        """Get all stock positions."""
        return [cast(StockPosition, p) for p in self.positions if p.position_type == "stock"]

    @property
    def option_positions(self) -> list[OptionPosition]:
        """Get all option positions."""
        return [cast(OptionPosition, p) for p in self.positions if p.position_type == "option"]

    @property
    def cash_positions(self) -> list[Position]:
        """Get all cash positions."""
        return [p for p in self.positions if p.position_type == "cash"]

    @property
    def unknown_positions(self) -> list[Position]:
        """Get all unknown positions."""
        return [p for p in self.positions if p.position_type == "unknown"]


@dataclass(frozen=True)
class PortfolioHolding:
    """Raw entry from a portfolio CSV file.

    This class represents the essential data from a single row in the portfolio CSV file.
    It only includes the core fields needed for position analysis, excluding any
    private or irrelevant information.

    The source CSV format (portfolio-private.csv) contains these columns:
    - Symbol: The ticker symbol of the security
    - Description: Text description of the security
    - Quantity: Number of shares or contracts
    - Last Price: Current price per share/contract
    - Current Value: Total value of the position
    - Cost Basis Total: Total cost basis of the position
    """
    symbol: str
    description: str
    quantity: float
    price: float  # Last Price in the CSV
    value: float  # Current Value in the CSV
    cost_basis_total: float | None = None  # Cost Basis Total in the CSV


@dataclass(frozen=True)
class PortfolioSummary:
    """Summary metrics for the portfolio."""
    total_value: float
    stock_value: float
    option_value: float
    cash_value: float
    unknown_value: float
    pending_activity_value: float
    net_market_exposure: float
    portfolio_beta: float | None = None


@dataclass(frozen=True)
class ExposureMetrics:
    """Exposure metrics for a position or group."""
    market_exposure: float
    beta_adjusted_exposure: float | None = None
    delta_exposure: float | None = None  # For options only
```

## 2. Updated Portfolio Service

### Helper Functions for `portfolio_service.py`

```python
def group_positions_by_ticker(positions: list[Position]) -> dict[str, list[Position]]:
    """
    Group positions by ticker symbol.

    Args:
        positions: List of positions to group

    Returns:
        Dictionary mapping ticker symbols to lists of positions
    """
    grouped = {}
    for position in positions:
        if position.ticker not in grouped:
            grouped[position.ticker] = []
        grouped[position.ticker].append(position)
    return grouped


def get_positions_by_ticker(positions: list[Position], ticker: str) -> list[Position]:
    """
    Get all positions for a specific ticker.

    Args:
        positions: List of positions to search
        ticker: Ticker symbol to match

    Returns:
        List of positions with the specified ticker
    """
    return [p for p in positions if p.ticker == ticker]


def get_stock_position_by_ticker(positions: list[Position], ticker: str) -> StockPosition | None:
    """
    Get the stock position for a specific ticker.

    Args:
        positions: List of positions to search
        ticker: Ticker symbol to match

    Returns:
        StockPosition if found, None otherwise
    """
    for p in positions:
        if p.position_type == "stock" and p.ticker == ticker:
            return cast(StockPosition, p)
    return None


def get_option_positions_by_ticker(positions: list[Position], ticker: str) -> list[OptionPosition]:
    """
    Get all option positions for a specific ticker.

    Args:
        positions: List of positions to search
        ticker: Ticker symbol to match

    Returns:
        List of option positions with the specified ticker
    """
    return [cast(OptionPosition, p) for p in positions if p.position_type == "option" and p.ticker == ticker]


def get_positions_by_type(positions: list[Position], position_type: Literal["stock", "option", "cash", "unknown"]) -> list[Position]:
    """
    Get all positions of a specific type.

    Args:
        positions: List of positions to search
        position_type: Type of positions to return

    Returns:
        List of positions with the specified type
    """
    return [p for p in positions if p.position_type == position_type]
```

### Updated `process_portfolio` Function

```python
def process_portfolio(
    holdings: list[PortfolioHolding],
    update_prices: bool = True,  # noqa: ARG001
) -> Portfolio:
    """
    Process raw portfolio holdings into a structured portfolio.

    This function transforms raw portfolio holdings into a structured portfolio by:
    1. Identifying cash-like positions
    2. Identifying stock and option positions
    3. Identifying unknown/invalid positions
    4. Creating a portfolio object with all positions

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()
        update_prices: Whether to update prices from market data (default: True)

    Returns:
        Processed portfolio with all positions
    """
    logger.debug("Processing portfolio with %d holdings", len(holdings))

    # Extract pending activity value
    pending_activity_value = _get_pending_activity(holdings)

    # Filter out pending activity from holdings
    filtered_holdings = [h for h in holdings if not _is_pending_activity(h.symbol)]

    # Process holdings into positions
    positions = []

    for holding in filtered_holdings:
        # Check for cash-like positions
        if stockdata.is_cash_like(holding.symbol, holding.description):
            # Convert to CashPosition
            cash_position = CashPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            positions.append(cash_position)
            logger.debug(f"Identified cash-like position: {holding.symbol}")

        # Check for option positions
        elif _is_valid_option_symbol(holding.symbol, holding.description):
            # Extract option data
            option_data = _extract_option_data(holding)
            if option_data:
                ticker, strike, expiry, option_type, quantity = option_data
                option_position = OptionPosition(
                    ticker=ticker,
                    quantity=quantity,
                    price=holding.price,
                    strike=strike,
                    expiry=expiry,
                    option_type=option_type,
                    cost_basis=holding.cost_basis_total,
                )
                positions.append(option_position)
                logger.debug(f"Identified option position: {holding.symbol}")
            else:
                # If we can't parse the option data, treat it as an unknown position
                unknown_position = UnknownPosition(
                    ticker=holding.symbol,
                    quantity=holding.quantity,
                    price=holding.price,
                    description=holding.description,
                    cost_basis=holding.cost_basis_total,
                )
                positions.append(unknown_position)
                logger.warning(f"Could not parse option data for: {holding.symbol}")

        # Check for stock positions
        elif stockdata.is_valid_stock_symbol(holding.symbol):
            stock_position = StockPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                cost_basis=holding.cost_basis_total,
            )
            positions.append(stock_position)
            logger.debug(f"Identified stock position: {holding.symbol}")

        # Unknown positions
        else:
            unknown_position = UnknownPosition(
                ticker=holding.symbol,
                quantity=holding.quantity,
                price=holding.price,
                description=holding.description,
                cost_basis=holding.cost_basis_total,
            )
            positions.append(unknown_position)
            logger.warning(f"Identified unknown position: {holding.symbol}")

    # Create and return the portfolio
    portfolio = Portfolio(
        positions=positions,
        pending_activity_value=pending_activity_value,
    )

    logger.debug(
        f"Portfolio processing complete: {len(positions)} positions"
    )
    return portfolio
```

### Updated `create_portfolio_summary` Function

```python
def create_portfolio_summary(portfolio: Portfolio) -> PortfolioSummary:
    """
    Create a summary of portfolio metrics.

    This function calculates summary metrics for the portfolio, including:
    - Total value
    - Stock value
    - Option value
    - Cash value
    - Unknown position value
    - Pending activity value
    - Net market exposure
    - Portfolio beta

    Args:
        portfolio: The portfolio to summarize

    Returns:
        Portfolio summary with calculated metrics
    """
    logger.debug("Creating portfolio summary")

    # Initialize values
    total_value = 0.0
    stock_value = 0.0
    option_value = 0.0
    cash_value = 0.0
    unknown_value = 0.0
    net_market_exposure = 0.0
    weighted_beta_sum = 0.0
    total_stock_value = 0.0  # For beta calculation

    # Process positions by type
    for position in portfolio.positions:
        # Skip NaN values
        position_value = position.market_value
        if pd.isna(position_value):
            logger.warning(f"Skipping NaN market value for {position.ticker}")
            continue

        # Add to total value
        total_value += position_value

        # Process based on position type
        if position.position_type == "stock":
            stock_position = cast(StockPosition, position)
            stock_value += position_value

            # Get beta for exposure calculation
            beta = 1.0
            try:
                beta = stockdata.get_beta(stock_position.ticker)
            except Exception as e:
                logger.warning(f"Could not calculate beta for {stock_position.ticker}: {e}")

            weighted_beta_sum += beta * position_value
            total_stock_value += position_value
            net_market_exposure += position_value * beta

        elif position.position_type == "option":
            option_value += position_value
            # Options exposure is more complex and would be calculated in a separate function

        elif position.position_type == "cash":
            cash_value += position_value
            # Cash has zero beta, so no contribution to market exposure

        elif position.position_type == "unknown":
            unknown_value += position_value
            # Unknown positions don't contribute to beta or market exposure

    # Add pending activity
    total_value += portfolio.pending_activity_value

    # Calculate portfolio beta (weighted average of stock betas)
    portfolio_beta = None
    if total_stock_value > 0:
        portfolio_beta = weighted_beta_sum / total_stock_value

    # Create and return summary
    summary = PortfolioSummary(
        total_value=total_value,
        stock_value=stock_value,
        option_value=option_value,
        cash_value=cash_value,
        unknown_value=unknown_value,
        pending_activity_value=portfolio.pending_activity_value,
        net_market_exposure=net_market_exposure,
        portfolio_beta=portfolio_beta,
    )

    logger.debug(f"Portfolio summary: total value = {total_value:.2f}, beta = {portfolio_beta}")
    return summary
```

## 3. Migration Steps

### Phase 1: Update Domain Models

1. Update `domain.py` with the new class hierarchy
2. Keep `PortfolioHolding` for backward compatibility
3. Add the new `Portfolio` class without `PortfolioGroup`
4. Add type hints and docstrings

### Phase 2: Update Portfolio Service

1. Add helper functions for grouping and filtering positions
2. Update `process_portfolio` to work with the new model
3. Remove `create_portfolio_groups` function
4. Update `create_portfolio_summary` to work with flat position list

### Phase 3: Update Consumers

1. Identify all code that depends on `PortfolioGroup`
2. Update to use the new helper functions instead
3. Run tests to ensure everything works correctly

## 4. Testing Strategy

1. **Unit Tests**:
   - Test each position class
   - Test the helper functions
   - Test the updated `process_portfolio` function
   - Test the updated `create_portfolio_summary` function

2. **Integration Tests**:
   - Test the end-to-end flow from CSV to portfolio summary
   - Test with real portfolio data

3. **Performance Tests**:
   - Compare performance of the old and new implementations
   - Ensure the new implementation is at least as fast as the old one

## 5. Conclusion

This implementation plan provides a clear path to simplifying the domain model while maintaining all the functionality of the current implementation. The new model is more flexible, easier to understand, and easier to extend.

Key benefits:
- Simpler class hierarchy
- More flexible grouping options
- Better type safety with proper casting
- Clearer separation of concerns
- More maintainable codebase
