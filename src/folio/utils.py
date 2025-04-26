"""Misc utility functions
TODO: eventually should be split into smaller modular pieces
"""

import os

import pandas as pd
import yaml

from src.stockdata import get_data_fetcher

# Import cash detection functions
from .cash_detection import is_cash_or_short_term
from .logger import logger


# Load configuration from folio.yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "folio.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(
                f"Failed to load folio.yaml: {e}. Using default configuration."
            )
    return {}


# Get configuration
config = load_config()

# Get the singleton data fetcher instance
data_fetcher = get_data_fetcher(config=config)


def get_beta(ticker: str, description: str = "") -> float:
    # TODO: move to stockdata.py?
    """Calculates the beta (systematic risk) for a given financial instrument.

    Beta measures the volatility of an instrument in relation to the overall market.
    Returns 0.0 when beta cannot be meaningfully calculated (e.g., for money market funds,
    or instruments with insufficient price history).

    Args:
        ticker: The instrument's symbol
        description: Description of the security, used to identify cash-like positions

    Returns:
        float: The calculated beta value, or 0.0 if beta cannot be meaningfully calculated

    Raises:
        RuntimeError: If the DataFetcher has not been initialized or fails to fetch data
        ValueError: If the data is invalid or calculations result in invalid values
        KeyError: If the data format is invalid (missing required columns)
    """
    # For cash-like instruments, return 0 without calculation
    if is_cash_or_short_term(ticker, beta=None, description=description):
        logger.debug(f"Using default beta of 0.0 for cash-like position: {ticker}")
        return 0.0

    if not data_fetcher:
        raise RuntimeError("DataFetcher not initialized - check API key configuration")

    # Fetch required data
    stock_data = data_fetcher.fetch_data(ticker)
    market_data = data_fetcher.fetch_market_data()

    if stock_data is None:
        raise RuntimeError(f"Failed to fetch data for ticker {ticker}")
    if market_data is None:
        raise RuntimeError("Failed to fetch market index data")

    try:
        # Calculate returns - let KeyError propagate if 'Close' column missing
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

    except (ValueError, pd.errors.InvalidIndexError) as e:
        # Only catch calculation-related errors
        if "No historical data found" in str(e):
            # This is not a critical error - just log a warning
            logger.warning(
                f"Error calculating beta for {ticker}: {e}. Unable to determine beta."
            )
            # Re-raise with a more specific message
            raise ValueError(
                f"No historical data available for beta calculation: {ticker}"
            ) from e
        else:
            # Log other calculation errors as errors
            logger.error(f"Error calculating beta for {ticker}: {e}")
            raise


def clean_currency_value(value_str: str) -> float:
    """Converts a formatted currency string into a float.
    TODO: this belongs in formatting.py

    Handles various common currency formats:
    - Removes dollar signs ($)
    - Removes comma separators (,)
    - Handles empty strings or double dashes ("--") by returning 0.0
    - Interprets values enclosed in parentheses, e.g., "(123.45)", as negative numbers

    Args:
        value_str: The currency string to clean (e.g., "$1,234.56", "(500.00)", "--")

    Returns:
        The numerical float representation of the currency string

    Raises:
        TypeError: If input is not a string or string-convertible type
        ValueError: If the string cannot be converted to a float after cleaning
    """
    if not isinstance(value_str, str | int | float):
        raise TypeError(f"Expected string or numeric input, got {type(value_str)}")

    value_str = str(value_str)

    # Handle empty or dash values
    if value_str in ("--", ""):
        return 0.0

    # Remove currency symbols and commas
    cleaned_str = value_str.replace("$", "").replace(",", "")

    # Handle negative values in parentheses like (123.45)
    is_negative = False
    if cleaned_str.startswith("(") and cleaned_str.endswith(")"):
        cleaned_str = cleaned_str[1:-1]
        is_negative = True

    try:
        value = float(cleaned_str)
        return -value if is_negative else value
    except ValueError as e:
        raise ValueError(
            f"Could not convert '{value_str}' to float: invalid format"
        ) from e


def is_option(symbol: str) -> bool:
    # TODO: Move to options.py or portfolio.py?
    """Determines if a financial symbol likely represents an option contract.

    This function checks if the provided symbol string starts with a hyphen ('-').
    This is a common convention used by some brokers (like Fidelity) in exported
    data files to distinguish options from their underlying stocks.

    Args:
        symbol: The financial symbol string to check.

    Returns:
        True if the symbol starts with '-', False otherwise or if the input is not a string.

    Note:
        This method is based on a specific formatting convention and might not be
        universally applicable to all data sources. A more robust approach might involve
        parsing the option's description string. See `is_option_desc`.
    """
    if not isinstance(symbol, str):
        return False
    return symbol.strip().startswith("-")
