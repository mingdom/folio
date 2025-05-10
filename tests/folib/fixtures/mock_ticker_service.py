"""
Mock ticker service for testing.

This module provides a mock implementation of the ticker service
that returns fixed values for specific tickers, ensuring consistent
and deterministic test results without making any API calls.
"""

import logging
from datetime import datetime

from src.folib.data.ticker_data import TickerData

logger = logging.getLogger(__name__)


class MockTickerService:
    """Mock implementation of the ticker service for testing."""

    def __init__(self, ticker_data: dict[str, dict[str, float]]):
        """
        Initialize the mock ticker service with predefined ticker data.

        Args:
            ticker_data: Dictionary mapping ticker symbols to dictionaries
                         containing 'price' and 'beta' values.
        """
        self._ticker_data = {}

        # Convert the simple dictionary to TickerData objects
        for ticker, data in ticker_data.items():
            price = data.get("price")
            beta = data.get("beta")
            self._ticker_data[ticker] = TickerData(
                ticker=ticker,
                price=price,
                beta=beta,
                last_updated=datetime.now(),
                description=f"Mock data for {ticker}",
            )

        logger.debug(
            f"Initialized mock ticker service with {len(self._ticker_data)} tickers"
        )

    def get_ticker_data(self, ticker: str) -> TickerData:
        """
        Get data for a ticker from the mock data.

        Args:
            ticker: The ticker symbol

        Returns:
            TickerData object containing the mock data for the ticker
        """
        ticker = ticker.upper()  # Normalize ticker to uppercase

        # Return mock data if available
        if ticker in self._ticker_data:
            return self._ticker_data[ticker]

        # For unknown tickers, return default values
        # This is important for cash-like instruments
        if ticker in ["SPAXX", "FMPXX", "FZDXX"] or "MONEY MARKET" in ticker:
            return TickerData(
                ticker=ticker,
                price=1.0,  # Cash-like instruments have a price of 1.0
                beta=0.0,  # Cash-like instruments have a beta of 0.0
                last_updated=datetime.now(),
                description=f"Cash-like instrument {ticker}",
            )

        # For other unknown tickers, log a warning and return default values
        logger.warning(f"No mock data found for ticker {ticker}, using defaults")
        return TickerData(
            ticker=ticker,
            price=100.0,  # Default price
            beta=1.0,  # Default beta
            last_updated=datetime.now(),
            description=f"Default data for {ticker}",
        )

    def get_price(self, ticker: str) -> float:
        """
        Get the price for a ticker from the mock data.

        Args:
            ticker: The ticker symbol

        Returns:
            The mock price for the ticker
        """
        ticker_data = self.get_ticker_data(ticker)
        return ticker_data.effective_price

    def get_beta(self, ticker: str) -> float:
        """
        Get the beta for a ticker from the mock data.

        Args:
            ticker: The ticker symbol

        Returns:
            The mock beta for the ticker
        """
        ticker_data = self.get_ticker_data(ticker)
        return ticker_data.effective_beta

    def prefetch_tickers(self, tickers: list[str]) -> None:
        """
        Mock implementation of prefetch_tickers.
        Does nothing in the mock service.

        Args:
            tickers: List of ticker symbols to prefetch
        """
        pass

    def clear_cache(self) -> None:
        """Mock implementation of clear_cache. Does nothing in the mock service."""
        pass


# Test portfolio ticker data captured from the current implementation
# This data was captured from the actual ticker service during test execution
TEST_PORTFOLIO_TICKER_DATA = {
    # Stocks
    "AMZN": {"price": 193.0999, "beta": 1.2},
    "APP": {"price": 343.1799, "beta": 1.8},
    "ARKK": {"price": 51.7866, "beta": 1.5},
    "ASML": {"price": 712.29, "beta": 1.3},
    "AXP": {"price": 284.48, "beta": 1.1},
    "BKNG": {"price": 5197.22, "beta": 1.2},
    "FTNT": {"price": 98.495, "beta": 1.4},
    "GOOGL": {"price": 155.75, "beta": 1.1},
    "INTU": {"price": 659.36, "beta": 1.2},
    "IONQ": {"price": 31.855, "beta": 2.0},
    "LRCX": {"price": 75.725, "beta": 1.5},
    "MA": {"price": 571.11, "beta": 1.0},
    "MELI": {"price": 2406.335, "beta": 1.4},
    "META": {"price": 603.9999, "beta": 1.2},
    "MSCI": {"price": 558.31, "beta": 1.1},
    "NVDA": {"price": 118.15, "beta": 1.6},
    "NVO": {"price": 65.41, "beta": 0.8},
    "PANW": {"price": 188.3401, "beta": 1.3},
    "QQQ": {"price": 491.145, "beta": 1.0},
    "SPGI": {"price": 512.17, "beta": 1.0},
    "SPY": {"price": 567.73, "beta": 1.0},
    "TCEHY": {"price": 64.16, "beta": 1.1},
    "TSM": {"price": 176.39, "beta": 1.2},
    "UBER": {"price": 82.7954, "beta": 1.3},
    "V": {"price": 354.16, "beta": 0.9},
    # Additional tickers found in the test portfolio
    "ANET": {"price": 100.0, "beta": 1.3},
    "CRM": {"price": 300.0, "beta": 1.2},
    "MSFT": {"price": 400.0, "beta": 1.1},
    "PDD": {"price": 150.0, "beta": 1.5},
    "SNOW": {"price": 200.0, "beta": 1.4},
    "ZS": {"price": 180.0, "beta": 1.3},
    # Cash-like instruments
    "SPAXX": {"price": 1.0, "beta": 0.0},
    "FMPXX": {"price": 1.0, "beta": 0.0},
    "FZDXX": {"price": 1.0, "beta": 0.0},
}
