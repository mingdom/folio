"""
Script to fetch sample data from the FMP API for testing purposes.

This script fetches data for a few representative tickers and saves it to JSON files
for reference when creating mock data and tests.
"""

import json
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from src.fmp import DataFetcher

# Create output directory
OUTPUT_DIR = "tests/test_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# List of tickers to fetch data for
TICKERS = [
    "SPY",    # S&P 500 ETF (market benchmark)
    "AAPL",   # High beta tech stock
    "GOOGL",  # Another high beta tech stock
    "SO",     # Low volatility utility stock
    "TLT",    # Treasury ETF (negative correlation with market)
    "BIL",    # Short-term treasury (very low volatility)
    "EFA",    # International ETF
    "EEM",    # Emerging markets ETF
]

# Periods to fetch
PERIODS = ["1y", "5y"]

def main():
    """Fetch sample data and save to files."""

    # Initialize data fetcher
    fetcher = DataFetcher()

    # Fetch data for each ticker and period
    for ticker in TICKERS:
        for period in PERIODS:
            try:

                # Fetch data
                df = fetcher.fetch_data(ticker, period=period)

                if df is not None and not df.empty:
                    # Save to CSV
                    csv_path = os.path.join(OUTPUT_DIR, f"{ticker}_{period}.csv")
                    df.to_csv(csv_path)

                    # Save first 5 rows to JSON for reference
                    json_path = os.path.join(OUTPUT_DIR, f"{ticker}_{period}_sample.json")
                    sample_data = df.head(5).reset_index().to_dict(orient="records")
                    with open(json_path, "w") as f:
                        json.dump(sample_data, f, indent=2, default=str)
                else:
                    pass

            except Exception:
                pass

    # Calculate and save beta values
    betas = {}

    # Use 5-year data for more accurate beta calculation
    market_data = fetcher.fetch_market_data("SPY", period="5y")
    market_returns = market_data["Close"].pct_change().dropna()

    for ticker in TICKERS:
        try:
            # Skip SPY (beta = 1.0 by definition)
            if ticker == "SPY":
                betas[ticker] = 1.0
                continue

            # Fetch data and calculate beta
            stock_data = fetcher.fetch_data(ticker, period="5y")
            stock_returns = stock_data["Close"].pct_change().dropna()

            # Align data
            common_dates = stock_returns.index.intersection(market_returns.index)
            if len(common_dates) < 30:  # Require at least 30 data points
                continue

            aligned_stock = stock_returns.loc[common_dates]
            aligned_market = market_returns.loc[common_dates]

            # Calculate beta
            covariance = aligned_stock.cov(aligned_market)
            market_variance = aligned_market.var()
            beta = covariance / market_variance

            betas[ticker] = beta

        except Exception:
            pass

    # Save beta values
    beta_path = os.path.join(OUTPUT_DIR, "beta_values.json")
    with open(beta_path, "w") as f:
        json.dump(betas, f, indent=2)


if __name__ == "__main__":
    main()
