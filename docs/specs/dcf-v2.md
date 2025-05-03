## Product Specification: DCF Calculator (Simplified Focus)

**Version:** 1.1
**Date:** 2025-05-03
**Status:** Proposed

**1. Introduction & Goal**

* **Feature:** Discounted Cash Flow (DCF) Calculator
* **Goal:** To provide users with an interactive tool to quickly estimate the intrinsic or "fair" value of a stock using a DCF model. The primary focus is on allowing users to easily utilize historical data via AutoFill for a baseline estimate and then immediately see how adjusting key assumptions (growth rates, discount rate, etc.) impacts the calculated fair value.

**2. Target Audience**

* Individual investors performing fundamental analysis.
* Financial analysts evaluating stock valuations.
* Users who want to quickly gauge potential stock value based on adjustable fundamental assumptions.

**3. User Stories / Use Cases**

* **Quick Estimate:** "As an investor, I want to enter a stock ticker and use AutoFill to get an immediate DCF fair value estimate based on historical data, so I can get a rapid baseline valuation."
* **Assumption Sensitivity:** "As an analyst, I want to easily adjust input parameters like the metric growth rate or discount rate and instantly see the updated DCF fair value, so I can understand how sensitive the valuation is to my specific assumptions."
* **Value Comparison:** "As an investor, I want to see the calculated DCF fair value displayed clearly alongside the current market price and the percentage difference, so I can quickly assess potential under/overvaluation based on the current model inputs."
* **Understanding Inputs:** "As a user, I want clear hints or defaults for input parameters based on historical data, so I can make reasonable adjustments even if I don't have my own forecasts."
* **Calculation Transparency:** "As a user performing due diligence, I want the option to see the detailed year-by-year calculations that lead to the final fair value number, so I can understand the model's mechanics."

**4. Functional Requirements (User Perspective)**

* **4.1. Stock Selection:**
    * Users must be able to input a valid stock ticker symbol.
    * The system should provide suggestions for commonly analyzed tickers.
    * Entering/selecting a ticker automatically triggers the initial data fetch and AutoFill population.
* **4.2. Input Assumptions:** Users must be able to view and modify the following DCF parameters:
    * **Metric Selection:** Choose the financial metric (e.g., Operating Cash Flow, Free Cash Flow). Default: Operating Cash Flow.
    * **Projection Period:** Specify the number of years for internal projection (e.g., 3, 5, 10 years). Default: 3 or 5 years. (User may not need to see all projection years explicitly unless they "Show Calculation").
    * **Metric Growth Rate (%):** Define the expected annual growth rate for the chosen metric.
    * **Shares Outstanding Growth Rate (%):** Define the expected annual change in shares outstanding.
    * **Dividend Growth Rate (%):** Define the expected annual growth rate for dividends (used internally for calculation, not a primary output).
    * **Terminal Price Ratio:** Define the expected Price/Metric ratio for terminal value.
    * **Discount Rate (%):** Define the rate for discounting.
    * *(Advanced)* **Base Metric Override:** Optionally, manually enter the starting value for the chosen metric.
* **4.3. AutoFill Functionality:**
    * Provide an "AutoFill" button (and trigger on ticker selection).
    * Fetches historical data and populates Growth Rate fields and Terminal Price Ratio field with calculated historical averages/CAGRs. Hints should explain the basis (e.g., "based on last 3 years").
* **4.4. Visualization (Chart):**
    * Display an interactive time-series chart primarily focused on historical context:
        * Historical Stock Price (Line).
        * Historical Price / Selected Metric Ratio (Line/Area).
        * (Optional/De-emphasized) Projected DCF Fair Value *pathway* might be shown subtly or toggled off by default. The main output is the final Fair Value number, not the path.
    * Provide toggle buttons ("Show All", "Stock Price Ratio", "Stock Price") for historical data series visibility.
    * The chart should update dynamically if inputs change (primarily affecting the historical ratio if the metric changes).
* **4.5. Results Summary:**
    * Display a clear summary panel focused on the valuation result:
        * Current Stock Price (fetched).
        * **DCF Fair Value** (calculated result - **Primary Output**).
        * **Upside/Downside** (percentage difference between Fair Value and Current Price).
        * *(Removed: Future Stock Price, Projected Dividends, CAGR)*
* **4.6. Calculation Transparency:**
    * Provide a "Show Calculation" button or similar mechanism.
    * Activating this reveals the detailed year-by-year breakdown leading to the final DCF Fair Value (Projected Metric, Discount Factors, PV of Cash Flows, Terminal Value Calculation, PV of Terminal Value).

**5. Data Requirements (User Perspective)**

* **User Inputs:** Ticker Symbol, DCF Metric Choice, Projection Years, Growth Rates (Metric, Shares, Dividend), Terminal Price Ratio, Discount Rate, (Optional) Base Metric Override.
* **System Fetched/Displayed Data:** Historical Stock Prices, Historical Metric Values, Historical Shares Outstanding, Historical Dividends Paid, Current Stock Price, Calculated Historical Growth Rates/Ratios (for AutoFill/Hints).
* **System Calculated/Displayed Outputs:** **DCF Fair Value**, **Upside/Downside percentage**, Chart data points (historical price, historical ratio), Detailed calculation steps (optional).

**6. Non-Functional Requirements (User Perspective)**

* **Usability:** Simple input process, clear Fair Value output. AutoFill provides a quick starting point. Easy adjustment of assumptions.
* **Performance:** **Crucially, recalculations of Fair Value and updates to the result display upon changing inputs must be instantaneous or feel instantaneous.** AutoFill data fetching should be quick.
* **Accuracy:** DCF calculations must be correct. Historical data for AutoFill must be accurate.
* **Transparency:** Ability to "Show Calculation" is important for users to trust and understand the result. Tooltips explaining inputs remain valuable.

**7. Future Considerations (Optional)**

* Sensitivity Analysis tools focused on Fair Value.
* Support for different Terminal Value methods.
* Saving/loading custom assumption scenarios.
* Integration with portfolio holdings.
