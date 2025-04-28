---
status: TODO
---

# Simulator Refactoring Plan
Followup from docs/plans/sim-v2-atomic-implementation-plan.md

## Overview

This document outlines the plan to completely remove all references to the old `src/folio/simulator.py` module and ensure that all simulation functionality uses the improved `src/folio/simulator_v2.py` module instead. This refactoring is critical because the old simulator has known calculation issues, especially for option positions.

## Current State Assessment

### Files Using the Old Simulator

1. **`src/focli/commands/position.py`**
   - Imports `generate_spy_changes` and `simulate_position_with_spy_changes` from `src.folio.simulator`
   - Uses these functions for position-specific simulation

2. **`src/focli/commands/simulate.py`**
   - Imports `generate_spy_changes` and `simulate_portfolio_with_spy_changes` from `src.folio.simulator`
   - Uses these functions for portfolio simulation

3. **`src/focli/formatters.py`**
   - Contains `display_position_simulation` function that expects output from `simulate_position_with_spy_changes`
   - Contains `display_simulation_results` function that expects output from `simulate_portfolio_with_spy_changes`

### Files Already Using the New Simulator

1. **`src/focli/commands/sim.py`**
   - Imports and uses `simulate_portfolio` from `src.folio.simulator_v2`
   - Properly implements portfolio simulation using the improved simulator

2. **`src/focli/commands/analyze.py`**
   - Imports and uses `simulate_portfolio` from `src.folio.simulator_v2`

## Refactoring Plan

### Phase 1: Remove the Old Simulate Command

1. **Delete `src/focli/commands/simulate.py`**
   - This file uses the old simulator and should be completely removed
   - The functionality is already replaced by `src/focli/commands/sim.py`

2. **Update Command Registration**
   - Remove the `simulate` command registration in `src/focli/commands/__init__.py`
   - Ensure all references to the old command are removed

### Phase 2: Update Position Command to Use simulator_v2

1. **Modify `src/focli/commands/position.py`**
   - Replace imports from `src.folio.simulator` with imports from `src.folio.simulator_v2`
   - Replace `simulate_position_with_spy_changes` with a new implementation that uses `simulate_portfolio` with a single position group
   - Update the `position_simulate` function to use the new implementation

2. **Create a New Display Function**
   - Create a new `display_position_simulation_v2` function in `src/focli/formatters.py` or directly in `position.py`
   - This function should work with the output format from `simulator_v2.py`
   - Focus on showing meaningful metrics like portfolio contribution

### Phase 3: Update Help and Documentation

1. **Update Help Text**
   - Update the help text in `src/focli/commands/help.py` to reflect the changes
   - Remove references to the old `simulate` command
   - Update the help for the `position simulate` command

2. **Update Documentation**
   - Update any documentation that references the old simulator
   - Ensure all examples use the new commands

### Phase 4: Testing and Validation

1. **Run Tests**
   - Run all existing tests to ensure they pass with the new implementation
   - Update any tests that use the old simulator

2. **Manual Testing**
   - Test the `sim` command with various options
   - Test the `position simulate` command with various options
   - Verify that the results are consistent and accurate

## Implementation Details

### New Position Simulation Implementation

The new implementation for position simulation will:

1. Use `simulate_portfolio` from `simulator_v2.py` with a single position group
2. Extract position-specific results from the simulation result
3. Format the results to show:
   - Position value at each SPY change level
   - P&L in dollars and percentage
   - Contribution to the portfolio in percentage

### Output Format Changes

The new position simulation output will focus on:

1. **Dollar Contribution**: How much this position contributes to the portfolio value in dollars at each SPY change level
2. **Percentage Contribution**: What percentage of the total portfolio this position represents at each SPY change level
3. **P&L Metrics**: Clear P&L values that are easy to interpret

## Risks and Mitigations

1. **Risk**: Breaking existing functionality
   - **Mitigation**: Thorough testing before and after changes

2. **Risk**: Inconsistent results between portfolio and position simulation
   - **Mitigation**: Ensure both use the same underlying calculation logic

3. **Risk**: User confusion due to command changes
   - **Mitigation**: Update help text and documentation to clearly explain the changes

## Timeline

1. **Phase 1**: 1 day
2. **Phase 2**: 2 days
3. **Phase 3**: 1 day
4. **Phase 4**: 1 day

Total estimated time: 5 days

## Success Criteria

1. All references to `src.folio.simulator` are removed from the codebase
2. All simulation functionality uses `src.folio.simulator_v2`
3. Position simulation results are consistent with portfolio simulation results
4. UI shows meaningful metrics that help users understand position performance
5. All tests pass
6. Documentation is updated to reflect the changes
