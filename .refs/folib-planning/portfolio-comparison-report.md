---
description: Portfolio Implementation Comparison Report
date: "2023-11-15"
status: "IN PROGRESS"
---

# Portfolio Implementation Comparison Report

This document analyzes the discrepancies between the old portfolio implementation in `src/folio/portfolio.py` and the new implementation in `src/folib/`. It identifies key differences, root causes, and provides a plan for fixing these issues to ensure consistent portfolio calculations.

## Summary of Findings

A comprehensive comparison between the old and new portfolio implementations reveals significant discrepancies in portfolio values, position identification, and exposure calculations. The most notable differences are:

| Metric | Old Implementation | New Implementation | Difference | % Diff |
|--------|-------------------|-------------------|------------|--------|
| Total Value | $2,667,042.91 | $4,021,648.87 | $1,354,605.96 | 50.79% |
| Stock Value | $1,785,391.40 | $2,822,382.88 | $1,036,991.48 | 58.08% |
| Option Value | -$158,807.00 | $158,807.00 | $317,614.00 | 200.00% |
| Net Market Exposure | $1,256,874.68 | $699,495.37 | -$557,379.31 | -44.35% |
| Long Exposure | $3,874,919.31 | $3,679,641.58 | -$195,277.73 | -5.04% |
| Short Exposure | $2,618,044.64 | $2,980,146.22 | $362,101.58 | 13.83% |

These discrepancies are significant and must be addressed before proceeding to the next phase of the project.

## Detailed Analysis

### 1. Portfolio Value Differences

The new implementation shows significantly higher values for both total portfolio value and stock value, with the most dramatic difference in option value:

- **Option Value**: The old implementation shows a negative value (-$158,807.00), while the new implementation shows a positive value ($158,807.00). This 200% difference suggests a fundamental issue in how option values are calculated or aggregated.

- **Stock Value**: The new implementation shows a 58.08% higher stock value, which may indicate differences in how stock positions are identified or valued.

### 2. Position Differences

Six stock positions (CRM, QCOM, SNOW, PDD, LULU, ANET) are present in the old implementation but missing in the new implementation:

- These positions have a market value of $0.00 in the old implementation, suggesting they might be placeholder positions for options.
- The new implementation doesn't include these placeholder positions, which may affect how options are grouped and analyzed.

### 3. Exposure Differences

The exposure calculations show significant differences:

- **Net Exposure**: 44.35% lower in the new implementation
- **Long Exposure**: 5.04% lower in the new implementation
- **Short Exposure**: 13.83% higher in the new implementation

### 4. Exposure Component Breakdown

| Component | Old Implementation | New Implementation | Difference |
|-----------|-------------------|-------------------|------------|
| Long Stock Exposure | $2,298,326.67 | $2,309,447.61 | $11,120.94 |
| Long Option Exposure | $1,576,592.65 | $1,370,193.97 | -$206,398.68 |
| Short Stock Exposure | $512,935.27 | $512,935.27 | $0.00 |
| Short Option Exposure | $2,105,109.37 | $2,467,210.95 | $362,101.58 |

The most significant differences are in option exposures, particularly short option exposure.

## Root Causes of Discrepancies

Based on the analysis, the following root causes have been identified:

1. **Option Value Calculation**:
   - Different approaches to calculating option values
   - Potential sign issues with option quantities or values
   - Inconsistent handling of contract multipliers (100 shares per contract)

2. **Option Delta Calculation**:
   - Different methods or parameters for calculating option delta
   - Inconsistent application of delta in exposure calculations

3. **Stock Position Identification**:
   - Different approaches to handling placeholder stock positions for options
   - Inconsistent grouping of positions by ticker

4. **Exposure Calculation**:
   - Different formulas for calculating long and short exposures
   - Inconsistent application of beta in exposure adjustments

## Recommendations for Fixing Discrepancies

Assuming the old implementation's calculations are correct, the following changes are needed in the new implementation:

### 1. Fix Option Value Calculation

- Review and update how option values are calculated in `OptionPosition` class
- Ensure consistent handling of contract multipliers (100 shares per contract)
- Verify sign conventions for option quantities and values

### 2. Align Delta Calculation

- Update delta calculation in `calculate_option_delta` to match the old implementation
- Ensure consistent parameters for QuantLib calculations
- Verify how delta is applied in exposure calculations

### 3. Standardize Position Identification

- Update position processing to handle placeholder stock positions consistently
- Ensure options are correctly associated with their underlying stocks
- Maintain consistent grouping of positions by ticker

### 4. Align Exposure Calculation

- Update exposure calculations to match the old implementation
- Ensure consistent formulas for long and short exposures
- Verify beta adjustment in exposure calculations

## Implementation Plan

The implementation will proceed in phases, with testing after each phase to verify that the discrepancies are being resolved:

### Phase 1: Fix Option Value Calculation

- Update the `OptionPosition` class in `src/folib/domain.py`
- Verify option market value calculation
- Test with sample portfolio to confirm option values match

### Phase 2: Align Delta Calculation

- Update `calculate_option_delta` in `src/folib/calculations/options.py`
- Ensure consistent parameters for QuantLib
- Test delta values against old implementation

### Phase 3: Standardize Position Identification

- Update `process_portfolio` in `src/folib/services/portfolio_service.py`
- Ensure consistent handling of placeholder positions
- Test position identification against old implementation

### Phase 4: Align Exposure Calculation

- Update `get_portfolio_exposures` in `src/folib/services/portfolio_service.py`
- Ensure consistent exposure calculations
- Test exposure values against old implementation

## Conclusion

The discrepancies between the old and new portfolio implementations are significant and must be addressed before proceeding with further development. By systematically addressing each issue, we can ensure that the new implementation produces results consistent with the old implementation, providing a solid foundation for future enhancements.

The implementation plan will focus on fixing one issue at a time, with testing after each change to verify that the discrepancies are being resolved. This approach will ensure that we maintain the correctness of the portfolio calculations while transitioning to the new implementation.
