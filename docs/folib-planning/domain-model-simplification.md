# Domain Model Simplification Plan

## Current Issues

The current domain model in `src/folib/domain.py` has several layers of abstraction that add complexity:

1. **Redundant Position Classes**: We have `Position` (base), `StockPosition`, `OptionPosition`, and `PortfolioHolding` with overlapping fields
2. **Complex Grouping Logic**: `PortfolioGroup` requires complex processing in `portfolio_service.py`
3. **Rigid Structure**: The current model makes it harder to work with positions directly

## Proposed Solution

We can simplify the domain model by:

1. **Eliminating `PortfolioGroup`**: Replace with a flat list of positions in the Portfolio class
2. **Consolidating Position Classes**: Create a clearer hierarchy with a base `Position` class and specific subtypes
3. **Using Dictionaries for Efficient Lookups**: Implement helper functions in `portfolio_service.py` for grouping and lookups

## Detailed Design

### 1. Revised Position Class Hierarchy

```python
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
        super().__init__(
            ticker=ticker,
            quantity=quantity,
            price=price,
            cost_basis=cost_basis,
            position_type="stock"
        )

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
        super().__init__(
            ticker=ticker,
            quantity=quantity,
            price=price,
            cost_basis=cost_basis,
            position_type="option"
        )
        self.strike = strike
        self.expiry = expiry
        self.option_type = option_type

    @property
    def market_value(self) -> float:
        """Calculate the market value of the position."""
        return self.quantity * self.price * 100  # 100 shares per contract
```

### 2. Simplified Portfolio Class

```python
@dataclass(frozen=True)
class Portfolio:
    """Container for the entire portfolio."""
    positions: list[Position]
    pending_activity_value: float = 0.0

    @property
    def stock_positions(self) -> list[StockPosition]:
        """Get all stock positions."""
        return [p for p in self.positions if isinstance(p, StockPosition)]

    @property
    def option_positions(self) -> list[OptionPosition]:
        """Get all option positions."""
        return [p for p in self.positions if isinstance(p, OptionPosition)]

    @property
    def cash_positions(self) -> list[Position]:
        """Get all cash positions."""
        return [p for p in self.positions if p.position_type == "cash"]

    @property
    def unknown_positions(self) -> list[Position]:
        """Get all unknown positions."""
        return [p for p in self.positions if p.position_type == "unknown"]
```

### 3. Helper Functions in Portfolio Service

```python
def group_positions_by_ticker(positions: list[Position]) -> dict[str, list[Position]]:
    """Group positions by ticker symbol."""
    grouped = {}
    for position in positions:
        if position.ticker not in grouped:
            grouped[position.ticker] = []
        grouped[position.ticker].append(position)
    return grouped

def get_positions_by_ticker(positions: list[Position], ticker: str) -> list[Position]:
    """Get all positions for a specific ticker."""
    return [p for p in positions if p.ticker == ticker]

def get_stock_position_by_ticker(positions: list[Position], ticker: str) -> StockPosition | None:
    """Get the stock position for a specific ticker."""
    for p in positions:
        if isinstance(p, StockPosition) and p.ticker == ticker:
            return p
    return None

def get_option_positions_by_ticker(positions: list[Position], ticker: str) -> list[OptionPosition]:
    """Get all option positions for a specific ticker."""
    return [p for p in positions if isinstance(p, OptionPosition) and p.ticker == ticker]
```

## Migration Plan

1. **Phase 1: Update Domain Models**
   - Refactor `Position`, `StockPosition`, and `OptionPosition` classes
   - Create new `Portfolio` class without `PortfolioGroup`
   - Keep `PortfolioHolding` for backward compatibility

2. **Phase 2: Update Portfolio Service**
   - Add helper functions for grouping and filtering positions
   - Update `process_portfolio` to work with the new model
   - Refactor `create_portfolio_summary` to work with flat position list

3. **Phase 3: Update Consumers**
   - Update any code that depends on `PortfolioGroup`
   - Ensure all tests pass with the new model

## Benefits

1. **Simpler Data Model**: Fewer classes and clearer relationships
2. **More Flexible**: Easier to work with positions directly
3. **Better Performance**: Dictionary-based lookups for faster access
4. **More Maintainable**: Less code to understand and modify
5. **More Extensible**: Easier to add new position types or attributes

## Potential Issues

1. **Breaking Changes**: Code that depends on `PortfolioGroup` will need updates
2. **Migration Effort**: Need to update multiple files and tests
3. **Performance Considerations**: Need to ensure efficient lookups with the new model

## Conclusion

This simplification aligns with the principles of composition over inheritance and keeps the data model lean while providing flexible ways to group and access positions. The helper functions in `portfolio_service.py` will provide the same functionality as `PortfolioGroup` but with more flexibility and less complexity.
