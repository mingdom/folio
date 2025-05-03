"""
Mock stock data for testing data fetchers.

This module provides consistent mock data for testing both the FMP API and yfinance implementations.
The data is structured to match the expected output format of both data sources after processing.
"""

import json
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Path to the test data directory
TEST_DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_price_series(base_price=100.0, volatility=0.01, days=252, seed=42):
    """
    Generate a realistic price series with random walk characteristics.

    Args:
        base_price: Starting price
        volatility: Daily volatility (standard deviation of returns)
        days: Number of trading days to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(seed)

    # Generate daily returns with specified volatility
    daily_returns = np.random.normal(0, volatility, days)

    # Calculate cumulative returns and price series
    cum_returns = np.cumprod(1 + daily_returns)
    prices = base_price * cum_returns

    # Generate dates (business days only)
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [end_date - timedelta(days=i) for i in range(days)]
    dates.reverse()  # Sort ascending

    # Generate OHLCV data
    data = []
    for i, date in enumerate(dates):
        price = prices[i]
        volatility * price

        # Generate realistic OHLC based on the close price
        open_price = price * (1 + np.random.normal(0, 0.003))
        high_price = max(open_price, price) * (1 + abs(np.random.normal(0, 0.005)))
        low_price = min(open_price, price) * (1 - abs(np.random.normal(0, 0.005)))
        volume = int(np.random.normal(1000000, 300000))

        data.append({
            "date": date,
            "Open": open_price,
            "High": high_price,
            "Low": low_price,
            "Close": price,
            "Volume": max(0, volume),  # Ensure volume is positive
        })

    # Create DataFrame
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    return df


# Generate mock data for common test tickers
MOCK_DATA = {
    # S&P 500 ETF (market benchmark)
    "SPY": generate_price_series(base_price=450.0, volatility=0.008, seed=42),
    # High beta tech stock
    "AAPL": generate_price_series(base_price=175.0, volatility=0.015, seed=43),
    # Another high beta tech stock
    "GOOGL": generate_price_series(base_price=140.0, volatility=0.016, seed=44),
    # Low volatility utility stock
    "SO": generate_price_series(base_price=70.0, volatility=0.006, seed=45),
    # Treasury ETF (negative correlation with market)
    "TLT": generate_price_series(base_price=90.0, volatility=0.007, seed=46),
    # Short-term treasury (very low volatility)
    "BIL": generate_price_series(base_price=91.5, volatility=0.001, seed=47),
    # International ETF
    "EFA": generate_price_series(base_price=75.0, volatility=0.01, seed=48),
    # Emerging markets ETF
    "EEM": generate_price_series(base_price=40.0, volatility=0.012, seed=49),
}


# Add correlations to make beta calculations realistic
def apply_correlations():
    """Apply realistic correlations between assets."""
    # Get SPY returns as market benchmark
    spy_returns = MOCK_DATA["SPY"]["Close"].pct_change().dropna()

    # Define correlation targets with market
    correlations = {
        "AAPL": 0.8,  # High correlation with market
        "GOOGL": 0.75,  # High correlation with market
        "SO": 0.3,  # Low correlation with market
        "TLT": -0.4,  # Negative correlation with market
        "BIL": 0.05,  # Very low correlation with market
        "EFA": 0.7,  # Moderate-high correlation with market
        "EEM": 0.6,  # Moderate correlation with market
    }

    for ticker, target_corr in correlations.items():
        # Get original returns
        orig_returns = MOCK_DATA[ticker]["Close"].pct_change().dropna()

        # Create correlated returns using the correlation formula
        new_returns = (
            target_corr * spy_returns.values
            + np.sqrt(1 - target_corr**2) * orig_returns.values
        )

        # Reconstruct prices from new returns
        cum_returns = np.cumprod(1 + new_returns)
        base_price = MOCK_DATA[ticker]["Close"].iloc[0]
        new_prices = base_price * cum_returns

        # Update Close prices
        MOCK_DATA[ticker].loc[orig_returns.index, "Close"] = new_prices

        # Adjust other OHLC values to be consistent with new Close prices
        for i, idx in enumerate(orig_returns.index):
            price_ratio = new_prices[i] / MOCK_DATA[ticker].loc[idx, "Close"]
            MOCK_DATA[ticker].loc[idx, "Open"] *= price_ratio
            MOCK_DATA[ticker].loc[idx, "High"] *= price_ratio
            MOCK_DATA[ticker].loc[idx, "Low"] *= price_ratio


# Apply correlations to make the data more realistic
apply_correlations()


def get_mock_data(ticker, period="1y"):
    """
    Get mock data for a specific ticker and period.

    Args:
        ticker: Stock ticker symbol
        period: Time period ('1y', '5y', etc.)

    Returns:
        DataFrame with OHLCV data for the specified period
    """
    if ticker not in MOCK_DATA:
        raise ValueError(f"No mock data available for ticker: {ticker}")

    df = MOCK_DATA[ticker].copy()

    # Filter based on period
    if period.endswith("y"):
        years = int(period[:-1])
        days = years * 252  # Approximate trading days in a year
    elif period.endswith("m"):
        months = int(period[:-1])
        days = months * 21  # Approximate trading days in a month
    else:
        days = 252  # Default to 1 year

    # Return the most recent 'days' rows
    return df.iloc[-min(days, len(df)) :]


def get_beta(ticker, market_index="SPY"):
    """
    Calculate beta for a ticker against a market index using the mock data.

    Args:
        ticker: Stock ticker symbol
        market_index: Market index ticker symbol

    Returns:
        Beta value (float)
    """
    if ticker == market_index:
        return 1.0

    if ticker not in MOCK_DATA or market_index not in MOCK_DATA:
        raise ValueError(f"Missing mock data for {ticker} or {market_index}")

    # Get returns
    stock_returns = MOCK_DATA[ticker]["Close"].pct_change().dropna()
    market_returns = MOCK_DATA[market_index]["Close"].pct_change().dropna()

    # Align data
    common_dates = stock_returns.index.intersection(market_returns.index)
    stock_returns = stock_returns.loc[common_dates]
    market_returns = market_returns.loc[common_dates]

    # Calculate beta
    covariance = stock_returns.cov(market_returns)
    market_variance = market_returns.var()

    if market_variance == 0:
        return 0.0

    return covariance / market_variance


# Functions to load real data from CSV files
def load_real_data(ticker, period="1y"):
    """
    Load real data from saved CSV files.

    Args:
        ticker: Stock ticker symbol
        period: Time period ('1y', '5y', etc.)

    Returns:
        DataFrame with OHLCV data for the specified period
    """
    file_path = os.path.join(TEST_DATA_DIR, f"{ticker}_{period}.csv")

    if not os.path.exists(file_path):
        raise ValueError(f"No data file found for {ticker} with period {period}")

    # Load data from CSV
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)

    # Ensure columns match expected format
    expected_columns = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in df.columns for col in expected_columns):
        raise ValueError(f"Data file for {ticker} does not have expected columns")

    return df[expected_columns]


def get_real_data(ticker, period="1y"):
    """
    Get real data for a specific ticker and period.

    This function attempts to load real data from saved files.
    If the file doesn't exist, it falls back to synthetic data.

    Args:
        ticker: Stock ticker symbol
        period: Time period ('1y', '5y', etc.)

    Returns:
        DataFrame with OHLCV data for the specified period
    """
    try:
        return load_real_data(ticker, period)
    except Exception:
        return get_mock_data(ticker, period)


def get_mock_raw_data(ticker, period="1y"):
    """
    Get mock raw data in the format returned by the FMP API.

    Args:
        ticker: Stock ticker symbol
        period: Time period ('1y', '5y', etc.)

    Returns:
        Dictionary with raw data structure
    """
    sample_file = os.path.join(TEST_DATA_DIR, f"{ticker}_{period}_sample.json")

    if not os.path.exists(sample_file):
        raise ValueError(f"No sample file found for {ticker} with period {period}")

    # Load sample data
    with open(sample_file, encoding="utf-8") as f:
        sample_data = json.load(f)

    # Get full data
    df = get_real_data(ticker, period)

    # Convert DataFrame to FMP API format
    historical = []
    for date, row in df.iterrows():
        # Use sample data as template for additional fields
        template = sample_data[0].copy()

        # Update with actual data
        template["date"] = date.strftime("%Y-%m-%d %H:%M:%S")
        template["Open"] = row["Open"]
        template["High"] = row["High"]
        template["Low"] = row["Low"]
        template["Close"] = row["Close"]
        template["Volume"] = row["Volume"]

        # Update derived fields
        template["adjClose"] = row["Close"] * 0.995  # Approximate
        template["change"] = 0.0  # Would need previous day's close
        template["changePercent"] = 0.0  # Would need previous day's close
        template["vwap"] = (row["Open"] + row["High"] + row["Low"] + row["Close"]) / 4
        template["label"] = date.strftime("%B %d, %y")
        template["changeOverTime"] = 0.0  # Would need reference point

        historical.append(template)

    # Return in FMP API format
    return {"symbol": ticker, "historical": historical}


def get_real_beta(ticker):
    """
    Get the beta value for a ticker from real data.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Beta value (float)
    """
    # Load beta values from JSON
    beta_file = os.path.join(TEST_DATA_DIR, "beta_values.json")

    if not os.path.exists(beta_file):
        raise ValueError("Beta values file not found")

    with open(beta_file, encoding="utf-8") as f:
        betas = json.load(f)

    if ticker not in betas:
        raise ValueError(f"No beta value found for {ticker}")

    return betas[ticker]


# Expected beta values for test tickers (from real data)
EXPECTED_BETAS = {
    "SPY": 1.0,
    "AAPL": 1.20,
    "GOOGL": 1.27,
    "SO": 0.47,
    "TLT": -0.01,
    "BIL": 0.00,
    "EFA": 0.79,
    "EEM": 0.75,
}


if __name__ == "__main__":
    # Test tickers
    test_tickers = ["SPY", "AAPL", "GOOGL", "SO", "TLT", "BIL", "EFA", "EEM"]

    for ticker in test_tickers:
        try:
            df = load_real_data(ticker, "1y")

            beta = get_real_beta(ticker)
        except Exception:
            pass

    for ticker in test_tickers:
        try:
            df = get_mock_data(ticker, "1y")

            beta = get_beta(ticker)
        except Exception:
            pass

    try:
        raw_data = get_mock_raw_data("AAPL", "1y")
        for _i, record in enumerate(raw_data["historical"][:2]):
            for _key, _value in record.items():
                pass
    except Exception:
        pass
