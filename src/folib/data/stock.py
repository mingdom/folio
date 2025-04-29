"""
Market data access.

This module provides access to market data through the StockOracle class.
It serves as a central point for fetching stock prices, beta values, and historical data.

The StockOracle is implemented as a Singleton to ensure only one instance exists
throughout the application. Use StockOracle.get_instance() to get the singleton instance.

Example usage:
    oracle = StockOracle.get_instance()
    price = oracle.get_price("AAPL")
    beta = oracle.get_beta("MSFT")

Migration Plan Notes:
---------------------
This module is part of Phase 1 of the folib migration plan, focusing on Portfolio Loading E2E.
It consolidates market data functionality from src/stockdata.py and src/yfinance.py into a
cleaner, more maintainable design with a single entry point for all market data needs.

Key differences from the old implementation:
- Uses a Singleton StockOracle class instead of separate DataFetcherInterface and YFinanceDataFetcher
- Provides direct methods for common operations (get_price, get_beta) instead of generic fetch_data
- Simplifies the API by hiding implementation details
- Implements the Singleton pattern for consistent access throughout the application

Old Codebase References:
------------------------
- src/stockdata.py: Contains the DataFetcherInterface
- src/yfinance.py: Contains the YFinanceDataFetcher implementation
- src/folio/utils.py: Contains the get_beta function
- src/folio/marketdata.py: Contains the get_stock_price function

Potential Issues:
----------------
- Yahoo Finance API may have rate limits or change its interface
- Beta calculation requires sufficient historical data
- Some tickers may not have data available
- Market data fetching can be slow
"""

import logging

import pandas as pd

import yfinance as yf

# Set up logging
logger = logging.getLogger(__name__)


class StockOracle:
    """
    Central service for accessing market data.

    This class provides a unified interface for accessing market data
    from various sources. It is implemented as a Singleton to ensure
    only one instance exists throughout the application.

    Usage:
        oracle = StockOracle.get_instance()
        price = oracle.get_price("AAPL")
    """

    # Singleton instance
    _instance = None

    # Default period for beta calculations (3 months provides more current market behavior)
    beta_period = "3m"
    # Default market index for beta calculations
    market_index = "SPY"

    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of StockOracle.

        Returns:
            The singleton StockOracle instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Initialize the StockOracle.

        Note:
            This should not be called directly. Use StockOracle.get_instance() instead.
        """
        # Check if an instance already exists to enforce singleton pattern
        if StockOracle._instance is not None:
            logger.warning(
                "StockOracle instance already exists. Use StockOracle.get_instance() instead."
            )

    def get_price(self, ticker: str) -> float:
        """
        Get the current price for a ticker.

        This method fetches the latest closing price for the given ticker
        using the Yahoo Finance API.

        Args:
            ticker: The ticker symbol

        Returns:
            The current price

        Raises:
            ValueError: If the ticker is empty
            ValueError: If no price data is available
            ValueError: If the price is invalid (<=0)
            Any exceptions from yfinance are propagated directly
        """
        if not ticker:
            raise ValueError("Ticker cannot be empty")

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

    def get_beta(self, ticker: str, description: str = "") -> float:
        """
        Get the beta for a ticker.

        This method calculates the beta (systematic risk) for a given ticker
        by comparing its price movements to a market index (default: SPY).

        Beta measures the volatility of a security in relation to the overall market.
        A beta of 1 indicates the security's price moves with the market.
        A beta less than 1 means the security is less volatile than the market.
        A beta greater than 1 indicates the security is more volatile than the market.

        Returns 0.0 when beta cannot be meaningfully calculated (e.g., for cash-like instruments,
        instruments with insufficient price history, or when market variance is near-zero).

        Args:
            ticker: The ticker symbol
            description: Description of the security, used to identify cash-like positions

        Returns:
            The calculated beta value, or 0.0 if beta cannot be meaningfully calculated

        Raises:
            ValueError: If market variance or covariance calculations result in NaN
            ValueError: If beta calculation results in NaN
            Any exceptions from get_historical_data() are propagated directly
        """
        # For cash-like instruments, return 0 without calculation
        if self.is_cash_like(ticker, description):
            logger.debug(f"Using default beta of 0.0 for cash-like position: {ticker}")
            return 0.0

        # Get historical data for the ticker and market index
        stock_data = self.get_historical_data(ticker, period=self.beta_period)
        market_data = self.get_historical_data(
            self.market_index, period=self.beta_period
        )

        # Calculate returns
        stock_returns = stock_data["Close"].pct_change(fill_method=None).dropna()
        market_returns = market_data["Close"].pct_change(fill_method=None).dropna()

        # Align data by index
        aligned_stock, aligned_market = stock_returns.align(
            market_returns, join="inner"
        )

        if aligned_stock.empty or len(aligned_stock) < 2:
            logger.debug(
                f"Insufficient overlapping data points for {ticker}, cannot calculate meaningful beta"
            )
            return 0.0

        # Calculate beta components
        market_variance = aligned_market.var()
        covariance = aligned_stock.cov(aligned_market)

        if pd.isna(market_variance):
            raise ValueError(
                f"Market variance calculation resulted in NaN for {ticker}"
            )

        if abs(market_variance) < 1e-12:
            logger.debug(
                f"Market variance is near-zero for {ticker}, cannot calculate meaningful beta"
            )
            return 0.0

        if pd.isna(covariance):
            raise ValueError(f"Covariance calculation resulted in NaN for {ticker}")

        beta = covariance / market_variance
        if pd.isna(beta):
            raise ValueError(f"Beta calculation resulted in NaN for {ticker}")

        logger.debug(f"Calculated beta of {beta:.2f} for {ticker}")
        return beta

    def get_historical_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """
        Get historical price data for a ticker.

        This method fetches historical price data for the given ticker
        using the Yahoo Finance API.

        Args:
            ticker: The ticker symbol
            period: Time period (e.g., "1d", "1m", "1y")

        Returns:
            DataFrame with historical price data (columns: Open, High, Low, Close, Volume)

        Raises:
            ValueError: If the ticker is empty
            ValueError: If no historical data is available
            Any exceptions from yfinance are propagated directly
        """
        if not ticker:
            raise ValueError("Ticker cannot be empty")

        # Fetch historical data for the ticker
        ticker_data = yf.Ticker(ticker)
        df = ticker_data.history(period=period)

        if df.empty:
            raise ValueError(f"No historical data available for {ticker}")

        logger.debug(f"Retrieved {len(df)} historical data points for {ticker}")
        return df

    def is_cash_like(
        self, ticker: str, description: str = "", beta: float | None = None
    ) -> bool:
        """
        Determine if a position should be considered cash or cash-like.

        This function checks if a position is likely cash or a cash-like instrument
        based on its ticker, beta, and description. Cash-like instruments include
        money market funds, short-term bond funds, and other low-volatility assets.

        Args:
            ticker: The ticker symbol to check
            description: The description of the security (optional)
            beta: The calculated beta value for the position (optional)

        Returns:
            True if the position is likely cash or cash-like, False otherwise
        """
        if not ticker:
            return False

        # Convert to uppercase for case-insensitive matching
        ticker_upper = ticker.upper()
        description_upper = description.upper() if description else ""

        # 1. Check if it's a cash symbol
        if ticker_upper in ["CASH", "USD"]:
            logger.debug(f"Identified {ticker} as cash based on symbol")
            return True

        # 2. Check common patterns for cash-like instruments in ticker
        cash_patterns = [
            "MM",
            "CASH",
            "MONEY",
            "TREASURY",
            "GOVT",
            "GOV",
            "SPAXX",
            "FDRXX",
            "SPRXX",
            "FZFXX",
            "FDIC",
            "BANK",
        ]

        if any(pattern in ticker_upper for pattern in cash_patterns):
            logger.debug(f"Identified {ticker} as cash-like based on ticker pattern")
            return True

        # 3. Check for money market terms in description
        if description:
            money_market_terms = [
                "MONEY MARKET",
                "CASH RESERVES",
                "TREASURY ONLY",
                "GOVERNMENT LIQUIDITY",
                "CASH MANAGEMENT",
                "LIQUID ASSETS",
                "CASH EQUIVALENT",
                "TREASURY FUND",
                "LIQUIDITY FUND",
                "CASH FUND",
                "RESERVE FUND",
            ]

            if any(term in description_upper for term in money_market_terms):
                logger.debug(f"Identified {ticker} as cash-like based on description")
                return True

        # 4. Check for very low beta (near zero)
        if beta is not None and abs(beta) < 0.1:
            logger.debug(f"Identified {ticker} as cash-like based on low beta: {beta}")
            return True

        return False
