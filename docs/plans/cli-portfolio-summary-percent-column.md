# Plan: Add Percent of Total Value Column to CLI Portfolio Summary Table

## WHY
The goal is to make it easier for users to see the relative size of each portfolio component (stocks, options, cash, etc.) as a percentage of the total portfolio value in the CLI summary table.

## WHAT
Currently, the CLI summary table only shows absolute values for each component. The new feature will add a column to display each component's value as a percent of the total portfolio value.

## HOW
- The CLI is display-only; all calculations must come from folib.
- The summary table is built in `src/cli/formatters.py` (`create_portfolio_summary_table`).
- The core summary data comes from `folib/services/portfolio_service.py` (`create_portfolio_summary`).
- The `PortfolioSummary` object already contains all the absolute values needed.

### Implementation Options
1. **Calculate percentages in the CLI formatter** (preferred):
   - Use the total value from the summary and compute the percent for each component (stock, option, cash, pending, etc.) directly in the formatter.
   - Minimal code change, no folib edit, keeps business logic in folib and display logic in CLI.
2. **Add percentage fields to PortfolioSummary in folib**:
   - Add percent fields for each component to the summary object in folib, and expose them to the CLI.
   - More extensible if percentages are needed elsewhere, but more code churn and not necessary for CLI-only display.

## Scope
- Trivial change.
- Only `src/cli/formatters.py` (and possibly folib/services/portfolio_service.py and PortfolioSummary) are affected.
- No business logic changes, only display.

## Assumptions
- The total value is always available in the summary.
- The CLI is not responsible for business logic, so option 1 is preferred unless percentages are needed elsewhere.

## Open Questions / Blocking Issues
- Should the percent column be shown for all rows (including pending/unknown), or only for the main components?
- Should negative values (e.g., options) show negative percentages?

## Next Steps
- Confirm requirements for which rows should display percentages.
- Implement option 1 unless future requirements dictate otherwise.
