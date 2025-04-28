# Simulator V2 Test Plan

## Overview

This document outlines the test plan for the new simulator_v2 implementation, which provides improved portfolio simulation capabilities with more accurate calculations, especially for option positions. This test plan is designed for manual testing to verify the functionality, accuracy, and usability of the new simulator.

## Background

The simulator_v2 implementation is a ground-up rewrite of the portfolio simulation functionality, focusing on:

1. **Atomic functions** with clean interfaces
2. **Type-specific calculations** rather than generic ones
3. **Improved option pricing** using Black-Scholes model
4. **Consistent P&L calculations** across all SPY change levels
5. **Better handling of edge cases**, particularly the SPY > 3.3% issue

The new implementation is accessible through the `sim` command in the Folio CLI and the `make sim` target in the Makefile.

## Test Environment Setup

### Prerequisites

1. Clone the repository and set up the development environment:
   ```bash
   git clone <repository-url>
   cd folio
   make env
   make install
   ```

2. Ensure you have a test portfolio file. You can use:
   - `@private-data/private-portfolio.csv` (if available)
   - `src/folio/assets/sample-portfolio.csv` (included in the repository)
   - Or create your own test portfolio with a mix of stocks and options

### Running the Simulator

There are two main ways to run the simulator:

1. **Using the Makefile target**:
   ```bash
   make sim
   ```

   With options:
   ```bash
   make sim ticker=SPY detailed=1
   ```

2. **Using the CLI directly**:
   ```bash
   poetry run python -m src.focli.commands.sim path/to/portfolio.csv
   ```

   Or through the interactive shell:
   ```bash
   make focli
   folio> portfolio load path/to/portfolio.csv
   folio> sim
   ```

## Test Scenarios

### Basic Functionality Tests

#### Test Case 1: Basic Portfolio Simulation
1. **Action**: Run `make sim` with the default parameters
2. **Expected Result**:
   - The simulator should run without errors
   - A table showing portfolio values at different SPY change levels should be displayed
   - The table should include SPY change, SPY price, portfolio value, P&L, P&L %, and P&L % of original
   - The 0% SPY change row should show $0.00 P&L

#### Test Case 2: Detailed Position-Level Results
1. **Action**: Run `make sim detailed=1`
2. **Expected Result**:
   - In addition to the portfolio-level table, position-level tables should be displayed
   - Each position should show its values at different SPY change levels
   - For positions with both stocks and options, individual component details should be shown
   - Values should be properly formatted with colors (green for gains, red for losses)

#### Test Case 3: Focus on Specific Ticker
1. **Action**: Run `make sim ticker=SPY` (replace SPY with a ticker in your portfolio)
2. **Expected Result**:
   - Only the specified ticker should be included in the simulation
   - The portfolio values should reflect only this position
   - The simulation should run without errors

### Advanced Functionality Tests

#### Test Case 4: Correlation Analysis
1. **Action**: In the interactive CLI, run:
   ```
   folio> portfolio load path/to/portfolio.csv
   folio> sim --analyze-correlation
   ```
2. **Expected Result**:
   - After the regular simulation results, a correlation analysis table should be displayed
   - The table should show how each position performs when SPY increases
   - Positions should be sorted from worst to best performance in up markets
   - Positions that consistently lose money when SPY increases should be highlighted

#### Test Case 5: Custom SPY Change Range
1. **Action**: In the interactive CLI, run:
   ```
   folio> portfolio load path/to/portfolio.csv
   folio> sim --min-spy-change -0.1 --max-spy-change 0.1 --steps 11
   ```
2. **Expected Result**:
   - The simulation should run with the specified SPY change range (-10% to +10%)
   - The table should show 11 rows (steps) of SPY changes
   - The values should be calculated correctly for each SPY change level

### Edge Case Tests

#### Test Case 6: SPY > 3.3% Issue
1. **Action**: Run `make sim` and focus on the rows where SPY change is greater than 3.3%
2. **Expected Result**:
   - Portfolio values should continue to change appropriately as SPY increases beyond 3.3%
   - There should be no unexpected drops or jumps in portfolio value
   - P&L should be consistent with the portfolio's beta and composition

#### Test Case 7: Portfolio with Options
1. **Action**: Ensure your test portfolio includes option positions, then run `make sim detailed=1`
2. **Expected Result**:
   - Option positions should be properly valued at each SPY change level
   - The Black-Scholes model should be used for option pricing
   - Delta-adjusted exposure should be reflected in the results
   - Options should show appropriate sensitivity to underlying price changes

#### Test Case 8: Empty or Invalid Portfolio
1. **Action**: Try to run the simulator with an empty or invalid portfolio file
2. **Expected Result**:
   - The simulator should handle the error gracefully
   - An appropriate error message should be displayed
   - The application should not crash

## Comparison Tests

#### Test Case 9: Compare with Original Simulator
1. **Action**:
   - Run the original simulator: `folio> simulate spy`
   - Run the new simulator: `folio> sim`
   - Compare the results
2. **Expected Result**:
   - The new simulator should produce more accurate results, especially for option positions
   - The SPY > 3.3% issue should be fixed in the new simulator
   - The new simulator should provide more detailed and useful information

## Usability Tests

#### Test Case 10: Help and Documentation
1. **Action**: In the interactive CLI, run:
   ```
   folio> help sim
   ```
2. **Expected Result**:
   - Comprehensive help information should be displayed
   - All available options and parameters should be documented
   - Examples of usage should be provided

#### Test Case 11: Error Handling
1. **Action**: Try various invalid inputs:
   - Invalid ticker: `make sim ticker=INVALID`
   - Invalid SPY range: `folio> sim --min-spy-change 0.5 --max-spy-change 0.1`
   - Missing portfolio: `folio> sim` (without loading a portfolio first)
2. **Expected Result**:
   - Clear error messages should be displayed for each case
   - The application should not crash
   - Guidance on correct usage should be provided

## Reporting Issues

When reporting issues with the simulator, please include:

1. The exact command you ran
2. The portfolio file you used (or a sanitized version if it contains sensitive information)
3. The expected vs. actual results
4. Any error messages or unexpected behavior
5. Screenshots if applicable

## Success Criteria

The simulator_v2 implementation will be considered successfully tested when:

1. All test cases pass without errors
2. The simulator produces accurate results for all portfolio types
3. The SPY > 3.3% issue is verified to be fixed
4. The user interface is clear and informative
5. Error handling is robust and user-friendly

## Additional Notes

- The simulator_v2 implementation uses atomic functions that can be reused in other parts of the application
- The implementation is designed to be maintainable and extensible
- Future enhancements may include more sophisticated option pricing models and additional analysis tools

Happy testing!
