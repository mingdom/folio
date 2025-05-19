Subject: Refactor: Improve Options Calculations and CLI Display

This pull request introduces a significant refactoring of the options calculation engine and enhances the command-line interface (CLI) display. The primary goals of these changes are to improve the accuracy of options pricing and greeks, robustly handle edge cases (such as expired and near-expiry options), and provide a more informative portfolio summary in the CLI.

Key changes include:

**Core Financial Logic (`folib`)**:

*   **`folib.calculations.options`**: This module has undergone a major overhaul.
    *   Implied volatility and Greeks (Delta, Gamma, Vega, Theta) calculations are significantly revised.
    *   All time-sensitive calculations now explicitly require a `calculation_date` parameter, removing ambiguity related to "current time."
    *   The module aims for a "fail-fast" approach by introducing `OptionCalculationError` for problematic calculations. However, pragmatic fallbacks to default volatility or approximations for greeks are implemented in certain near-expiry or low-volatility scenarios, accompanied by warnings, to ensure calculations can proceed where appropriate.
*   **`folib.services.position_service`**:
    *   Now calculates implied volatility via the updated `options.py` module and passes this to the greeks calculation functions.
    *   The `calculation_date` is propagated throughout the service.
    *   Handles `OptionCalculationError` from the calculation layer by logging the error and setting the greeks and exposure for the problematic option to zero, allowing portfolio-level analysis to continue.
*   **`folib.services.portfolio_service`**:
    *   Requires `calculation_date` for all summary and exposure calculations.
    *   The `net_exposure_pct` field has been removed from `PortfolioSummary`. Consumers of this object are now responsible for calculating this percentage if needed, typically `net_market_exposure / total_value`.

**Command-Line Interface (`cli`)**:

*   **`cli.formatters`**:
    *   The portfolio summary table now includes a "% of Total" column for major components.
    *   The exposures table now includes "% of Portfolio" and "Beta Adjusted %" columns.
    *   These percentages are calculated directly within the formatter.

**Supporting Changes**:

*   **Introduction of `calculation_date`**: A `calculation_date` parameter has been integrated throughout the calculation pipeline (services, calculations, and tests) to ensure that all time-dependent values are computed consistently as of a specific date.
*   **Documentation**:
    *   New design plan documents have been added for the "Options Calculation Improvements" and "CLI Portfolio Summary Percent Column" features.
    *   New `.github/copilot-instructions.md` provides guidelines for AI-assisted development.
*   **Testing**:
    *   Unit tests in `test_options_calculations.py` have been extensively rewritten and expanded to cover new logic and edge cases, including expiry and near-expiry scenarios.
    *   Critical portfolio calculation tests in `test_portfolio_calculations_optimized.py` have been updated with new expected values reflecting the changes in logic and the use of `calculation_date`.
    *   The `MockMarketDataService` has been updated to support mocking beta values and option market prices, and to accept `calculation_date` in its methods.
    *   The test asset CSV (`test_portfolio.csv`) has been modified, changing some "NULL" placeholders to "0".

This refactoring aims to provide more reliable and accurate financial calculations while improving the user experience of the CLI.
