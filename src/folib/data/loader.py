"""
CSV portfolio loading functions.

This module provides functions for loading and parsing portfolio CSV files.
It handles the transformation of raw CSV data into structured PortfolioHolding objects
that can be further processed by the portfolio service.

Key functions:
- load_portfolio_from_csv: Load portfolio data from a CSV file
- parse_portfolio_holdings: Parse raw CSV data into portfolio holdings

CSV Format:
----------
The module expects a CSV with these essential columns:
- Symbol: Ticker symbol
- Description: Text description of the security
- Quantity: Number of shares/contracts
- Last Price: Current price per share/contract
- Current Value: Total value of the position
- Cost Basis Total: Total cost basis (optional)
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
    if value_str in {"--", ""}:
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

            # Clean up the symbol - remove ** suffix (common in money market funds like SPAXX**)
            if "**" in symbol:
                original_symbol = symbol
                symbol = symbol.replace("**", "")
                logger.debug(
                    f"Row {index}: Cleaned up symbol from {original_symbol} to {symbol}"
                )

            # Identify pending activity rows but don't do special value extraction
            is_pending_activity = (
                symbol.upper() == "PENDING ACTIVITY" or "PENDING" in symbol.upper()
            )

            if is_pending_activity:
                logger.debug(f"Row {index}: Identified pending activity row")
                # For pending activity, we just create a basic holding with the raw data
                # Set quantity to 0 and price to 0
                quantity = 0
                price = 0

                # Try to get the value from the Current Value column for backward compatibility
                # But the comprehensive detection will happen in portfolio_service.py
                try:
                    value = clean_currency_value(row["Current Value"])
                    logger.debug(
                        f"Found pending activity value in Current Value column: {value}"
                    )
                except (ValueError, TypeError):
                    logger.debug(
                        f"Row {index}: Pending activity has no value in Current Value column. Using 0.0."
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

            # Special handling for cash-like positions
            is_cash_like = stockdata.is_cash_like(symbol, description)

            # For cash-like positions, ensure we have valid quantity and price
            if is_cash_like:
                logger.debug(
                    f"Row {index}: Identified {symbol} as a cash-like position"
                )

                # For cash positions, set quantity to 1 if it's 0 or NaN
                if quantity == 0.0 or pd.isna(quantity):
                    quantity = 1.0
                    logger.debug(
                        f"Row {index}: Set quantity to 1.0 for cash position {symbol}"
                    )

                # If we have a value but no price, calculate price from value and quantity
                if value != 0.0 and (price == 0.0 or pd.isna(price)):
                    price = value / quantity
                    logger.debug(
                        f"Row {index}: Calculated price for cash position {symbol}: {price}"
                    )

                # If we have a price but no value, calculate value from price and quantity
                elif price != 0.0 and (value == 0.0 or pd.isna(value)):
                    value = price * quantity
                    logger.debug(
                        f"Row {index}: Calculated value for cash position {symbol}: {value}"
                    )

            # For non-cash positions with a value but no price, calculate price from value and quantity
            elif price == 0.0 and value != 0.0 and quantity != 0.0:
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

            # Store the raw row data as a dictionary
            raw_data = row.to_dict()

            # Create PortfolioHolding object
            holding = PortfolioHolding(
                symbol=symbol,
                description=description,
                quantity=quantity,
                price=price,
                value=value,
                cost_basis_total=cost_basis_total,
                raw_data=raw_data,
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
