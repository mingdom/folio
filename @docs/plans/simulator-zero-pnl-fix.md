# Simulator Zero P&L Fix Plan

## WHY
When running portfolio simulations with 0% SPY change, we expect to see zero P&L since no prices should change. However, we're currently seeing non-zero P&L values at 0% SPY change, which is confusing to users and indicates a potential issue with our simulation logic.

## WHAT
We need to identify and fix the root cause of non-zero P&L at 0% SPY change in the portfolio simulator. This will ensure that our simulation results are accurate and intuitive, with 0% SPY change representing the current portfolio state.

## HOW

### Investigation Findings

After investigating the issue, we've identified several potential causes for the non-zero P&L at 0% SPY change:

1. **Option Pricing Recalculation**:
   - Even at 0% SPY change, we're recalculating option prices using Black-Scholes
   - The recalculated prices differ from the original prices due to:
     - Different implied volatility assumptions
     - Different time-to-expiration calculations (using different reference dates)
     - Different risk-free rate assumptions
     - Rounding errors in price calculations

2. **Inconsistent Baseline Values**:
   - The baseline portfolio value used for P&L calculations may be different from the value calculated at 0% SPY change
   - The baseline is using the current portfolio value from the data model, while the 0% simulation is recalculating values

3. **Volatility Estimation Issues**:
   - The volatility used in Black-Scholes calculations might differ from what was used to determine the original option prices
   - Our volatility skew model might be introducing differences even at 0% price change

4. **Date/Time Discrepancies**:
   - The time-to-expiration calculation might be using different reference dates between the original data and the simulation
   - Even small differences in days-to-expiration can cause option price differences

### Potential Solutions

We've identified several potential solutions to address this issue:

1. **Skip Recalculation at 0% Change**:
   - For 0% SPY change, use the original position values directly without recalculation
   - This ensures that the 0% scenario exactly matches the current portfolio state

2. **Consistent Parameter Usage**:
   - Ensure that all Black-Scholes parameters (volatility, time to expiration, risk-free rate) are consistent between portfolio data and simulator
   - Store and reuse the original parameters when recalculating prices

3. **Calibrate Implied Volatility**:
   - Calibrate implied volatility for each option to match its current market price
   - Use this calibrated volatility for all simulations to ensure consistency

4. **Reference Date Consistency**:
   - Ensure that the same reference date is used for time-to-expiration calculations in both the original data and simulations

### Test Case

We've created a test case in `tests/test_simulator_v2.py` that specifically checks for zero P&L at 0% SPY change. This test will help us validate our solution and ensure that the issue doesn't recur in the future.

### Implementation Plan

Based on our investigation, we recommend implementing Solution #1 (Skip Recalculation at 0% Change) as it's the most straightforward and reliable approach:

1. Modify `simulate_position_group` function to check if `spy_change` is zero (or very close to zero)
2. If `spy_change` is zero, use the original position values without recalculation
3. Update the test case to verify that P&L is zero at 0% SPY change
4. Run the test to confirm that the issue is fixed
5. Manually test with the CLI to verify the fix works in practice

### Acceptance Criteria

- The test case `test_zero_pnl_at_zero_spy_change` passes
- When running `make simulate`, the 0% SPY change scenario shows zero P&L
- The fix doesn't affect the accuracy of simulations at non-zero SPY changes
