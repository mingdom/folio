"""
CSV portfolio loading functions.

This module provides functions for loading and parsing portfolio CSV files.
It handles the transformation of raw CSV data into structured PortfolioHolding objects
that can be further processed by the portfolio service.

Migration Plan Notes:
---------------------
This module is part of Phase 1 of the folib migration plan, focusing on Portfolio Loading E2E.
It replaces the CSV loading functionality in src/folio/portfolio.py with a cleaner,
more maintainable design that separates data loading from business logic.

CSV Format:
----------
The primary source format is portfolio-private.csv, which contains the following columns:
- Account Number (private, not used)
- Account Name (private, not used)
- Symbol (used: ticker symbol)
- Description (used: text description of the security)
- Quantity (used: number of shares/contracts)
- Last Price (used: current price per share/contract)
- Last Price Change (not used)
- Current Value (used: total value of the position)
- Today's Gain/Loss Dollar (not used)
- Today's Gain/Loss Percent (not used)
- Total Gain/Loss Dollar (not used)
- Total Gain/Loss Percent (not used)
- Percent Of Account (not used)
- Cost Basis Total (used: total cost basis)
- Average Cost Basis (not used)
- Type (not used)

Only the essential columns (Symbol, Description, Quantity, Last Price, Current Value,
Cost Basis Total) are extracted and stored in PortfolioHolding objects to maintain
privacy and focus on the core position data.

Old Codebase References:
------------------------
- src/folio/portfolio.py: Contains the original CSV loading and processing logic
- src/folio/cash_detection.py: Contains logic for detecting cash-like positions
- src/folio/utils.py: Contains utility functions for cleaning currency values

Potential Issues:
----------------
- The old codebase mixed CSV loading with data processing and calculations
- Different brokers may use different CSV formats requiring adaptation
- Some securities may have missing or invalid data in the CSV
- Cash-like positions and pending activity need special detection logic
- Currency values in the CSV may need cleaning (removing '$', ',', etc.)
"""

import logging
from typing import Any

import pandas as pd

from ..data.stock import stockdata
from ..domain import PortfolioHolding

# Set up logging
logger = logging.getLogger(__name__)


def clean_currency_value(value: Any) -> float:
    """
    Convert a formatted currency string into a float.

    Handles various common currency formats:
    - Removes dollar signs ($)
    - Removes comma separators (,)
    - Handles empty strings or double dashes ("--") by returning 0.0
    - Interprets values enclosed in parentheses, e.g., "(123.45)", as negative numbers

    Args:
        value: The currency string to clean (e.g., "$1,234.56", "(500.00)", "--")

    Returns:
        The numerical float representation of the currency string

    Raises:
        TypeError: If input is not a string or string-convertible type
        ValueError: If the string cannot be converted to a float after cleaning
    """
    if value is None:
        return 0.0

    if not isinstance(value, str | int | float):
        raise TypeError(f"Expected string or numeric input, got {type(value)}")

    value_str = str(value)

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


def load_portfolio_from_csv(file_path: str) -> pd.DataFrame:
    """
    Load portfolio data from a CSV file.

    This function reads the portfolio CSV file and returns it as a pandas DataFrame.
    It handles basic file I/O errors and ensures the CSV has the expected format.

    The expected CSV format is based on portfolio-private.csv with columns:
    Symbol, Description, Quantity, Last Price, Current Value, Cost Basis Total, etc.

    Args:
        file_path: Path to the CSV file

    Returns:
        DataFrame with portfolio data

    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If the CSV file is empty or missing required columns
    """
    logger.debug(f"Loading portfolio from CSV file: {file_path}")

    try:
        # Try to read the CSV file with standard settings
        df = pd.read_csv(file_path)
    except pd.errors.ParserError:
        # Try again with more flexible quoting to handle commas in option symbols
        logger.debug("Parser error with standard settings, trying with QUOTE_NONE")
        df = pd.read_csv(file_path, quoting=3)  # QUOTE_NONE
    except FileNotFoundError as e:
        logger.error(f"Portfolio file not found: {file_path}")
        raise FileNotFoundError(f"Portfolio file not found: {file_path}") from e

    if df.empty:
        logger.error("Portfolio CSV file is empty")
        raise ValueError("Portfolio CSV file is empty")

    # Validate required columns
    required_columns = [
        "Symbol",
        "Description",
        "Quantity",
        "Last Price",
        "Current Value",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"Missing required columns: {', '.join(missing_columns)}")
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    logger.debug(f"Successfully loaded {len(df)} rows from portfolio CSV")
    return df


def parse_portfolio_holdings(df: pd.DataFrame) -> list[PortfolioHolding]:
    """
    Parse raw CSV data into portfolio holdings.

    This function transforms the raw DataFrame into a list of PortfolioHolding objects,
    extracting only the essential columns and cleaning the data as needed.

    It handles:
    - Extracting the core fields (Symbol, Description, Quantity, Last Price, Current Value, Cost Basis Total)
    - Cleaning currency values (removing '$', ',', etc.)
    - Converting data types (strings to floats, etc.)
    - Handling missing or invalid values

    Args:
        df: DataFrame with portfolio data from load_portfolio_from_csv()

    Returns:
        List of PortfolioHolding objects containing only the essential position data

    Raises:
        ValueError: If required columns are missing or data conversion fails
    """
    logger.debug("Parsing portfolio holdings from DataFrame")

    # Clean and prepare data
    df = df.copy()  # Avoid SettingWithCopyWarning
    df["Symbol"] = df["Symbol"].str.strip()
    df["Description"] = df["Description"].fillna("")  # Ensure Description is never NaN

    # Initialize list to store holdings
    holdings = []

    # Process each row
    for index, row in df.iterrows():
        try:
            symbol = row["Symbol"]

            # Skip rows with empty symbols
            if pd.isna(symbol) or not symbol.strip():
                logger.debug(f"Row {index}: Skipping row with empty symbol")
                continue

            # Special handling for pending activity rows
            is_pending_activity = (
                symbol.upper() == "PENDING ACTIVITY" or "PENDING" in symbol.upper()
            )

            if is_pending_activity:
                logger.debug(f"Row {index}: Processing Pending Activity row")
                # For pending activity, we care about the value, not quantity or price
                # Set quantity to 0 or 1 (doesn't matter) and price to 0
                quantity = 0
                price = 0

                # Make sure we get the value from the Current Value column
                try:
                    value = clean_currency_value(row["Current Value"])
                    logger.debug(f"Found pending activity value: {value}")
                except (ValueError, TypeError):
                    logger.debug(
                        f"Row {index}: Pending activity has invalid value: '{row['Current Value']}'. Using 0.0."
                    )
                    value = 0.0

            description = row["Description"]

            # Parse quantity
            try:
                quantity = float(row["Quantity"]) if pd.notna(row["Quantity"]) else 0.0
            except (ValueError, TypeError):
                logger.debug(
                    f"Row {index}: {symbol} has invalid quantity: '{row['Quantity']}'. Using 0.0."
                )
                quantity = 0.0

            # Parse price
            try:
                price = clean_currency_value(row["Last Price"])
            except (ValueError, TypeError):
                logger.debug(
                    f"Row {index}: {symbol} has invalid price: '{row['Last Price']}'. Using 0.0."
                )
                price = 0.0

            # Parse value
            try:
                value = clean_currency_value(row["Current Value"])
            except (ValueError, TypeError):
                logger.debug(
                    f"Row {index}: {symbol} has invalid value: '{row['Current Value']}'. Using 0.0."
                )
                value = 0.0

            # For cash-like positions with no price but a value, calculate the price
            if price == 0.0 and value != 0.0 and quantity != 0.0:
                price = value / quantity
                logger.debug(f"Row {index}: Calculated price for {symbol}: {price}")

            # Parse cost basis if available
            cost_basis_total = None
            if "Cost Basis Total" in row and pd.notna(row["Cost Basis Total"]):
                try:
                    cost_basis_total = clean_currency_value(row["Cost Basis Total"])
                except (ValueError, TypeError):
                    logger.debug(
                        f"Row {index}: {symbol} has invalid cost basis: '{row['Cost Basis Total']}'. Using None."
                    )

            # Create PortfolioHolding object
            holding = PortfolioHolding(
                symbol=symbol,
                description=description,
                quantity=quantity,
                price=price,
                value=value,
                cost_basis_total=cost_basis_total,
            )

            holdings.append(holding)
            logger.debug(f"Row {index}: Added holding for {symbol}")

        except Exception as e:
            # Catch unexpected errors
            logger.error(f"Row {index}: Unexpected error: {e}", exc_info=True)
            continue

    if not holdings:
        logger.warning("No valid holdings found in portfolio data")
    else:
        logger.debug(f"Successfully parsed {len(holdings)} holdings")

    return holdings


def detect_cash_positions(holdings: list[PortfolioHolding]) -> list[PortfolioHolding]:
    """
    Detect cash and cash-like positions in portfolio holdings.

    This function identifies cash and cash-equivalent positions (money market funds,
    short-term treasuries, etc.) from the list of portfolio holdings.

    Cash detection is based on:
    - Symbol patterns (e.g., symbols containing "MM", "CASH", "TREASURY")
    - Description patterns (e.g., descriptions containing "Money Market", "Cash", "Treasury")
    - Low beta and volatility characteristics

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()

    Returns:
        List of holdings that represent cash or cash-like positions
    """
    logger.debug("Detecting cash and cash-like positions")

    cash_positions = []

    for holding in holdings:
        # Use StockOracle's is_cash_like method to determine if this is a cash-like position
        if stockdata.is_cash_like(holding.symbol, holding.description):
            logger.debug(f"Identified cash-like position: {holding.symbol}")
            cash_positions.append(holding)

    logger.debug(f"Found {len(cash_positions)} cash-like positions")
    return cash_positions


def detect_pending_activity(holdings: list[PortfolioHolding]) -> float:
    """
    Detect and calculate pending activity value.

    This function identifies and calculates the total value of pending activity
    in the portfolio (e.g., unsettled trades, dividends, etc.).

    Pending activity detection is based on:
    - Symbol patterns (e.g., "PENDING", "UNSETTLED")
    - Description patterns (e.g., descriptions containing "Pending", "Unsettled", "Dividend")
    - Special account types or flags in the original CSV

    Args:
        holdings: List of portfolio holdings from parse_portfolio_holdings()

    Returns:
        Total value of pending activity (positive for incoming funds, negative for outgoing)
    """
    logger.debug("Detecting pending activity")

    # In the current implementation, pending activity is detected during CSV loading
    # and not included in the holdings list. This function is provided for future
    # enhancements where pending activity might be detected from the holdings.

    # Look for holdings with pending activity patterns
    pending_activity_value = 0.0

    pending_patterns = [
        "PENDING",
        "UNSETTLED",
        "DIVIDEND",
        "INTEREST",
        "DEPOSIT",
        "WITHDRAWAL",
    ]

    for holding in holdings:
        symbol_upper = holding.symbol.upper()
        description_upper = holding.description.upper()

        # Check if this is a pending activity position
        if (
            symbol_upper == "PENDING ACTIVITY"
            or any(pattern in symbol_upper for pattern in pending_patterns)
            or any(pattern in description_upper for pattern in pending_patterns)
        ):
            logger.debug(
                f"Found pending activity: {holding.symbol} with value {holding.value}"
            )
            pending_activity_value += holding.value

    logger.debug(f"Total pending activity value: {pending_activity_value}")
    return pending_activity_value
