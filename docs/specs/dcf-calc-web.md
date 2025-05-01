## 2. DCF Calculator: Web App (`folio/`) Specific Requirements

**1. User Interface & Experience:**

* **1.1. New DCF Calculator Page/Section:**
    * Create a dedicated view accessible within the Dash application (e.g., a new tab or page).
    * Title: "DCF Calculator".
* **1.2. Ticker Input:**
    * Input field for the user to enter a stock ticker.
    * Display recently viewed/popular tickers as clickable suggestions (as shown: MSFT, AAPL, GOOG, META, TSLA).
    * Trigger DCF calculation/AutoFill upon ticker selection/entry.
* **1.3. DCF Inputs Panel:**
    * Organize all user-adjustable parameters clearly, mirroring the screenshot.
    * Use appropriate input components (Dropdown for Metric, NumberInput for Years/Rates/Ratio, potentially a toggle for Advanced Override).
    * Display current/default values in input fields.
    * Include tooltips (?) explaining each input parameter.
    * **AutoFill Button:**
        * On click, fetches historical data from FMP (via `folib` service) for the selected ticker.
        * Populates the input fields (Metric Growth Rate, Shares Outstanding Growth Rate, Dividend Growth Rate, Price Ratio) with calculated historical averages (e.g., 3-year CAGR or average).
        * Provides visual feedback during fetching (loading spinner).
    * **Metric Selection:** Dropdown menu allowing users to choose the basis for the DCF (e.g., Operating Cash Flow, Free Cash Flow). Default to Operating Cash Flow. Changing the metric should trigger AutoFill or update relevant default rates.
    * **Advanced Override:** Allow users to manually input the most recent base metric value (e.g., latest OCF) instead of relying on fetched data.
* **1.4. Chart Area:**
    * Use Plotly/Dash chart components.
    * Display Historical Stock Price.
    * Display Historical Price / Selected Metric Ratio.
    * Display Projected DCF Fair Value Price path based on calculation results.
    * Display Projected Future Stock Price path based on Terminal Value calculation.
    * Implement toggle buttons ("Show All", "Stock Price Ratio", "Stock Price") to control trace visibility.
    * Chart should update dynamically when input parameters change.
* **1.5. Results Display:**
    * Clearly display the key outputs below the chart:
        * Current Stock Price (fetched)
        * Projected Future Stock Price (calculated, with % change from current)
        * Total Projected Dividends Paid (calculated, with % yield implied)
        * DCF Fair Value (calculated, with % difference from current price)
        * Implied CAGR (calculated)
* **1.6. Show Calculation Details (Optional):**
    * A button ("Show Calculation") that reveals or opens a modal/collapsible section displaying the year-by-year projected metrics, cash flows/dividends, discounting steps, and terminal value calculation.

**2. Workflow & Data Flow:**

1.  User enters/selects a ticker.
2.  **(AutoFill/Initial Load):** Web app calls `folib` DCF service to get default historical rates/ratios for the ticker using FMP data. Input panel is populated.
3.  **(Calculation Trigger):** Any change to an input parameter OR initial AutoFill completion triggers a recalculation.
4.  Web app calls `folib` DCF service with the current ticker and all input parameters.
5.  `folib` service performs calculations.
6.  Web app receives structured results from `folib`.
7.  Web app updates the Chart Area and Results Display sections.
8.  **(Show Calculation):** If requested, the web app displays the detailed step-by-step calculation data received from `folib`.

**3. Error Handling:**

* Display clear error messages if ticker is invalid, FMP data is unavailable, or calculations fail.
* Disable calculation/show appropriate messages if essential inputs are missing or invalid.
