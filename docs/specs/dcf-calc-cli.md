## 3. DCF Calculator: CLI (`focli/`) Specific Requirements

**1. New Command:**

* Introduce a new top-level command: `dcf`.
* Usage: `dcf <TICKER> [options]`

**2. Functionality:**

* **Core Action:** Calculates the DCF intrinsic value for a given `<TICKER>`.
* **Data Fetching:** Retrieves necessary historical financial data from FMP via the `folib` data layer. Caching should be utilized.
* **Calculation:** Calls the core `folib.services.calculate_dcf` function.
* **Interactivity/Parameters:**
    * `<TICKER>`: Required argument.
    * Options (`--option value` format) should allow overriding default DCF parameters:
        * `--metric [OCF|FCF|etc]`: Specify the metric to use (default: OCF).
        * `--years <N>`: Number of years to project (default: 3 or 5).
        * `--metric-growth <RATE>`: Override calculated metric growth rate (e.g., `0.15` for 15%).
        * `--shares-growth <RATE>`: Override calculated shares outstanding growth rate.
        * `--dividend-growth <RATE>`: Override calculated dividend growth rate.
        * `--price-ratio <RATIO>`: Override calculated terminal Price/Metric ratio.
        * `--discount-rate <RATE>`: Set the discount rate (default: 0.10).
        * `--override-metric <VALUE>`: Manually set the most recent metric value (advanced).
    * If override options are *not* provided, the command should use the `folib` service to calculate historical defaults (like AutoFill in the web app).

**3. Output:**

* **Default Output:** Display a summary of the DCF calculation using `rich` formatting (potentially a table or key-value pairs):
    * Ticker
    * Current Stock Price
    * DCF Fair Value Estimate
    * Upside/Downside (%)
    * Implied CAGR
    * Key Inputs Used (Metric, Growth Rates, Discount Rate - showing defaults or user overrides)
* **Detailed Output (`--show-details` or `--verbose` flag):**
    * Optionally display the year-by-year projected values, discounted cash flows, terminal value calculation, similar to the web app's "Show Calculation". Format using `rich` tables.
* **Error Output:** Print clear error messages if the ticker is invalid, data fetching fails, or calculations encounter errors.

**4. Integration:**

* Add `dcf.py` to `focli/commands/`.
* Register the `dcf` command in `focli/commands/__init__.py`.
* Add relevant help text and examples to `focli/commands/help.py`.

**5. User Story:**

* "As a CLI user, I want to type `dcf AAPL --discount-rate 0.08` to quickly get a DCF valuation for Apple using an 8% discount rate and default growth assumptions based on historical FMP data, so I can perform rapid fundamental checks."
* "As an analyst scripting analyses, I want to run `focli dcf MSFT --metric FCF --years 5 --metric-growth 0.12 --price-ratio 20` and parse the output to automate valuation checks across multiple stocks with custom assumptions."
