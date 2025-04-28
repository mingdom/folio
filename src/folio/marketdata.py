"""
Market data utilities for fetching stock prices and other market data.
"""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def get_stock_price(ticker: str) -> float:
    """
    Get the current stock price for a ticker using YFinance.

    Args:
        ticker: The ticker symbol to get the price for

    Returns:
        The current stock price

    Raises:
        ValueError: If the ticker is invalid or the price cannot be retrieved
    """
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    try:
        # Fetch the latest data for the ticker
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period="1d")

        if df.empty:
            raise ValueError(f"No price data available for {ticker}")

        # Get the latest close price
        price = df.iloc[-1]["Close"]

        if price <= 0:
            raise ValueError(f"Invalid stock price ({price}) for {ticker}")

        logger.debug(f"Retrieved price for {ticker}: {price}")
        return price
    except Exception as e:
        # No fallback logic - just propagate the error with context
        logger.error(f"Error fetching price for {ticker}: {e}")
        raise ValueError(f"Failed to get stock price for {ticker}") from e
