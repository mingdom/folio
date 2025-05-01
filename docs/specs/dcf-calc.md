## 1. DCF Calculator: Overall Feature Requirements

**1. Introduction & Goal:**

* This document outlines the requirements for adding a Discounted Cash Flow (DCF) calculation feature to the Folio suite (Web App and CLI).
* The goal is to allow users to estimate the intrinsic value of a stock based on projected future cash flows (or other selected metrics), providing a fundamental valuation tool alongside existing portfolio analysis features.

**2. Core Requirements (Engine - `folib`):**

* **2.1. FMP Data Integration (`folib/data`):**
    * Integrate with the Financial Modeling Prep (FMP) API to fetch necessary historical financial data.
    * Required data points (historical, typically last 3-5 years):
        * Selected Metric (e.g., Operating Cash Flow, Free Cash Flow, Net Income)
        * Shares Outstanding (Diluted)
        * Dividends Paid
        * Stock Price (for Price/Metric ratio calculation)
    * Implement caching for FMP data to optimize performance and reduce API calls, respecting the existing caching mechanism.
    * Handle potential API errors and missing data gracefully.
* **2.2. DCF Calculation Logic (`folib/calculations`):**
    * Implement core DCF calculation steps as pure functions:
        * Calculate historical growth rates for the selected metric, shares outstanding, and dividends.
        * Calculate historical average Price/Metric ratio.
        * Project future metric values based on user-provided growth rate and years.
        * Project future dividends based on user-provided growth rate.
        * Project future share count based on user-provided growth rate.
        * Calculate Terminal Value (using a method like Perpetuity Growth or Exit Multiple/Price Ratio). The Price Ratio method seems implied by the screenshot.
        * Calculate Present Value of projected cash flows/dividends per share and terminal value per share by discounting back using the user-provided discount rate.
        * Sum Present Values to arrive at the DCF Intrinsic Value per share.
        * Calculate implied Compound Annual Growth Rate (CAGR) based on current price and estimated future value (including dividends).
* **2.3. DCF Service Layer (`folib/services`):**
    * Create a service function (e.g., `calculate_dcf`) that orchestrates the process:
        * Accepts ticker symbol and DCF parameters (Metric, Years, Growth Rates, Discount Rate, Overrides) as input.
        * Fetches required historical data from FMP via the data layer.
        * Calculates default growth rates and ratios.
        * Performs the DCF calculation using the calculation functions.
        * Returns a structured result containing:
            * Calculated Intrinsic Value.
            * Projected Future Stock Price (based on Terminal Value calculation).
            * Total Projected Dividends Paid (per share).
            * Implied CAGR.
            * Intermediate calculation steps (optional, for "Show Calculation" feature).
            * Default/historical values used for inputs (for AutoFill).

**3. Non-Functional Requirements:**

* **Maintainability:** Core logic must reside in `folib` for easy testing and reuse. Clear separation between data fetching, calculation, and presentation.
* **Performance:** API calls should be cached. Calculations should be reasonably fast for interactive use.
* **Accuracy:** Use standard DCF methodologies. Clearly state assumptions (e.g., terminal value method).
* **Extensibility:** Design should allow for adding different DCF variations (e.g., different metrics, terminal value methods) in the future.
* **Error Handling:** Gracefully handle missing FMP data, invalid user inputs, and calculation errors.
