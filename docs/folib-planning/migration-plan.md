# Folib Migration Plan

## Strategy: Smallest Chunk Approach

Our migration strategy follows the "smallest chunk" approach:

1. **Identify the smallest self-contained piece** of functionality that can be fully migrated
2. **Implement it completely** in the new architecture
3. **Integrate it immediately** with the CLI for testing
4. **Verify functionality** through manual CLI testing
5. **Move to the next chunk** only after the current one is fully working

This approach allows us to:
- Discover issues early when they're easier to fix
- Maintain a working system throughout the migration
- Get immediate feedback on design decisions
- Adjust our approach based on what we learn
- Make steady, measurable progress

## Prioritization

We'll prioritize based on the natural data flow of the application:

1. **Portfolio Loading (E2E)** - First priority
   - This is the foundation everything else depends on
   - Includes CSV parsing, position creation, and portfolio structure

2. **Portfolio Summary & Risk Calculations** - Second priority
   - Basic portfolio metrics and risk analysis
   - Exposure calculations and beta adjustments

3. **Simulations** - Final core functionality
   - Portfolio and position simulations
   - P&L analysis across different scenarios

4. **CLI Integration** - First integration target
   - We'll use the CLI for manual testing throughout
   - Each chunk will be integrated with the CLI as it's completed

5. **Web App Integration** - Final phase
   - Only after all functionality is working in the CLI
   - May involve additional UI-specific adaptations

## Testing Strategy

- **Manual CLI Testing**: We'll use the CLI as our primary testing tool during migration
- **No Automated Tests Initially**: We'll defer writing automated tests until after CLI integration
- **Comparison Testing**: We'll compare outputs between old and new implementations
- **Regression Prevention**: We'll ensure no functionality is lost during migration

## Task Tracking

### Phase 1: Portfolio Loading E2E
- [ ] **Domain Models**
  - [ ] Implement `Position` base structure
  - [ ] Implement `StockPosition` with properties
  - [ ] Implement `OptionPosition` with properties
  - [ ] Implement `PortfolioGroup` container
  - [ ] Implement `Portfolio` container
  - [ ] Implement `PortfolioSummary` structure

- [ ] **Data Access**
  - [ ] Implement `StockOracle.get_price()`
  - [ ] Implement `StockOracle.get_beta()`
  - [ ] Implement `load_portfolio_from_csv()`
  - [ ] Implement `parse_portfolio_holdings()`
  - [ ] Implement `detect_cash_positions()`
  - [ ] Implement `detect_pending_activity()`

- [ ] **Portfolio Processing**
  - [ ] Implement `process_portfolio()`
  - [ ] Implement `create_portfolio_groups()`
  - [ ] Implement `create_portfolio_summary()` (basic version)

- [ ] **CLI Integration**
  - [ ] Update CLI portfolio loading command
  - [ ] Update CLI portfolio display command
  - [ ] Verify E2E functionality

### Phase 2: Portfolio Summary & Risk Calculations
- [ ] **Exposure Calculations**
  - [ ] Implement `calculate_stock_exposure()`
  - [ ] Implement `calculate_option_exposure()`
  - [ ] Implement `calculate_beta_adjusted_exposure()`
  - [ ] Implement `calculate_position_exposure()`

- [ ] **Beta Calculations**
  - [ ] Implement `calculate_beta()`
  - [ ] Implement `calculate_portfolio_beta()`

- [ ] **Portfolio Analysis**
  - [ ] Enhance `create_portfolio_summary()` with risk metrics
  - [ ] Implement `get_portfolio_exposures()`

- [ ] **CLI Integration**
  - [ ] Update CLI risk analysis command
  - [ ] Update CLI exposure breakdown command
  - [ ] Verify risk calculation functionality

### Phase 3: Simulations
- [ ] **Option Pricing**
  - [ ] Implement `calculate_option_price()`
  - [ ] Implement `calculate_option_delta()`
  - [ ] Implement `calculate_implied_volatility()`

- [ ] **P&L Calculations**
  - [ ] Implement `calculate_stock_pnl()`
  - [ ] Implement `calculate_option_pnl()`
  - [ ] Implement `calculate_position_pnl()`
  - [ ] Implement `calculate_strategy_pnl()`

- [ ] **Simulation Service**
  - [ ] Implement `generate_spy_changes()`
  - [ ] Implement `simulate_position()`
  - [ ] Implement `simulate_position_group()`
  - [ ] Implement `simulate_portfolio()`

- [ ] **P&L Service**
  - [ ] Implement `generate_pnl_curve()`
  - [ ] Implement `analyze_position_risk()`
  - [ ] Implement `calculate_breakeven_points()`

- [ ] **CLI Integration**
  - [ ] Update CLI simulation command
  - [ ] Update CLI P&L analysis command
  - [ ] Verify simulation functionality

### Phase 4: Web App Integration
- [ ] **Adapter Creation**
  - [ ] Create adapters for web app integration
  - [ ] Ensure compatibility with Dash components

- [ ] **Component Updates**
  - [ ] Update portfolio loading components
  - [ ] Update portfolio display components
  - [ ] Update risk analysis components
  - [ ] Update simulation components

- [ ] **Testing**
  - [ ] Verify web app functionality
  - [ ] Address any web-specific issues

### Phase 5: Cleanup and Optimization
- [ ] **Automated Testing**
  - [ ] Write unit tests for core functionality
  - [ ] Write integration tests for key workflows

- [ ] **Code Cleanup**
  - [ ] Remove deprecated code
  - [ ] Remove temporary adapters
  - [ ] Refactor for consistency

- [ ] **Performance Optimization**
  - [ ] Identify performance bottlenecks
  - [ ] Optimize critical paths
  - [ ] Add caching where beneficial

## Implementation Details

### Domain Models

The domain models are the foundation of our migration. We'll implement them first, focusing on:

- **Immutability**: Using frozen dataclasses to prevent accidental state changes
- **Type Safety**: Using comprehensive type hints to catch errors early
- **Minimal Properties**: Including only essential computed properties
- **Clear Interfaces**: Designing interfaces that are easy to understand and use

### Data Access

The data access layer provides the raw data for our application. Key considerations:

- **Caching**: Implementing efficient caching to minimize API calls
- **Error Handling**: Following our "fail fast" approach for invalid inputs
- **Abstraction**: Providing a clean interface that hides implementation details
- **Flexibility**: Allowing for different data sources in the future

### Portfolio Processing

Portfolio processing ties together the domain models and data access. We'll focus on:

- **Pure Functions**: Implementing stateless functions that transform data
- **Clear Dependencies**: Making dependencies explicit through function parameters
- **Composition**: Building complex functionality from simple parts
- **Separation of Concerns**: Keeping data loading separate from business logic

### CLI Integration

For each chunk of functionality, we'll integrate with the CLI to enable manual testing:

- **Command Updates**: Updating one command at a time to use the new library
- **Parallel Implementation**: Keeping the old implementation available as a fallback
- **Comparison Testing**: Comparing outputs between old and new implementations
- **Gradual Transition**: Moving commands to the new implementation one by one

## Migration Challenges and Mitigations

### Challenge: Interface Incompatibility

**Mitigation**:
- Create temporary adapter functions to bridge old and new interfaces
- Document breaking changes clearly
- Update calling code incrementally

### Challenge: Missing Functionality

**Mitigation**:
- Audit existing code thoroughly before implementation
- Compare outputs between old and new implementations
- Address gaps immediately when discovered

### Challenge: Performance Regression

**Mitigation**:
- Monitor performance during manual testing
- Optimize critical paths early
- Add caching for expensive operations

### Challenge: Integration Issues

**Mitigation**:
- Integrate each chunk immediately after implementation
- Test thoroughly with real-world data
- Keep old implementation available as a fallback

## Conclusion

By following this smallest chunk approach and prioritizing based on the natural data flow of the application, we'll achieve a smooth migration to the new architecture. The focus on immediate CLI integration and manual testing will provide quick feedback and help us identify issues early.

This plan provides a clear roadmap for the migration, with specific tasks and progress tracking to ensure we stay on course. The emphasis on completing each chunk fully before moving on will help us maintain a working system throughout the migration process.
