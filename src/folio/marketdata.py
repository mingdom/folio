"""
Market data utilities for fetching stock prices and other market data.
"""

import logging

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
    raise NotImplementedError(
        "This method has been deprecated. Use StockOracle instead."
    )
