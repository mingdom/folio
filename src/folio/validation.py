"""
Validation utilities for the Folio application.

This module provides functions for validating and cleaning data used throughout
the application, particularly for portfolio and option data.
"""

from collections.abc import Callable
from typing import Any

import pandas as pd

from .exceptions import DataError
from .logger import logger
from .utils import clean_currency_value


def validate_option_data(
    option_row: pd.Series,
    description_field: str = "Description",
    quantity_field: str = "Quantity",
    price_field: str = "Last Price",
    row_index: int | None = None,
) -> tuple[str, int, float]:
    """
    Validate option data and return cleaned values.

    Args:
        option_row: DataFrame row containing option data
        description_field: Name of the field containing the option description
        quantity_field: Name of the field containing the option quantity
        price_field: Name of the field containing the option price
        row_index: Optional index of the row for error reporting

    Returns:
        Tuple of (description, quantity, price)

    Raises:
        DataError: If any required field is missing or invalid
    """
    # Extract row identifier for error messages
    row_id = f"row {row_index}" if row_index is not None else "option"

    # Validate description
    description = option_row.get(description_field)
    if pd.isna(description) or description == "--":
        raise DataError(f"Missing description for {row_id}")

    # Validate quantity
    quantity_raw = option_row.get(quantity_field)
    if pd.isna(quantity_raw) or quantity_raw == "--":
        raise DataError(f"Missing quantity for option '{description}'")

    try:
        quantity = int(float(quantity_raw))
    except (ValueError, TypeError) as e:
        raise DataError(
            f"Invalid quantity format '{quantity_raw}' for option '{description}': {e}"
        ) from e

    # Validate price
    price_raw = option_row.get(price_field)
    if pd.isna(price_raw) or price_raw in ("--", ""):
        raise DataError(f"Missing price for option '{description}'")

    try:
        price = clean_currency_value(price_raw)
    except ValueError as e:
        raise DataError(
            f"Invalid price format '{price_raw}' for option '{description}': {e}"
        ) from e

    return description, quantity, price


def extract_option_data(
    option_df: pd.DataFrame,
    filter_func: Callable | None = None,
    include_row_index: bool = True,
) -> list[dict[str, Any]]:
    """
    Extract and validate option data from a DataFrame.

    Args:
        option_df: DataFrame containing option data
        filter_func: Optional function to filter rows (takes a row and returns a boolean)
        include_row_index: Whether to include the row index in the extracted data

    Returns:
        List of dictionaries containing validated option data
    """
    options_data = []

    for idx, row in option_df.iterrows():
        if filter_func and not filter_func(row):
            continue

        try:
            description, quantity, price = validate_option_data(row, row_index=idx)

            option_data = {
                "description": description,
                "symbol": row.get("Symbol", ""),
                "quantity": quantity,
                "price": price,
                "current_value": row.get("Current Value"),
            }

            if include_row_index:
                option_data["row_index"] = idx

            options_data.append(option_data)

        except DataError as e:
            logger.warning(f"{e}. Skipping option.")
            continue

    return options_data


def validate_dataframe(
    df: pd.DataFrame | None,
    required_columns: list[str],
    name: str = "dataframe",
) -> pd.DataFrame:
    """
    Validate that a DataFrame exists and has the required columns.

    Args:
        df: DataFrame to validate
        required_columns: List of column names that must be present
        name: Name of the DataFrame for error messages

    Returns:
        The validated DataFrame

    Raises:
        DataError: If the DataFrame is None, empty, or missing required columns
    """
    if df is None:
        raise DataError(f"{name} is None")

    if df.empty:
        raise DataError(f"{name} is empty")

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise DataError(
            f"{name} is missing required columns: {', '.join(missing_columns)}"
        )

    return df


def clean_numeric_value(
    value: Any,
    default: int | float | None = None,
    allow_zero: bool = True,
    allow_negative: bool = True,
) -> int | float | None:
    """
    Clean and validate a numeric value.

    Args:
        value: Value to clean and validate
        default: Default value to return if cleaning fails
        allow_zero: Whether to allow zero values
        allow_negative: Whether to allow negative values

    Returns:
        Cleaned numeric value or default if cleaning fails

    Raises:
        ValueError: If the cleaned value doesn't meet the constraints and no default is provided
    """
    if pd.isna(value):
        if default is not None:
            return default
        raise ValueError("Value is NaN or None")

    # First convert to numeric value
    try:
        # Handle string values that might contain currency symbols or commas
        if isinstance(value, str):
            # Remove currency symbols, commas, and whitespace
            cleaned = value.replace("$", "").replace(",", "").replace(" ", "")
            # Handle parentheses for negative numbers
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            numeric_value = float(cleaned)
        else:
            numeric_value = float(value)
    except (ValueError, TypeError) as e:
        if default is not None:
            return default
        raise ValueError(f"Could not convert '{value}' to a numeric value") from e

    # Then apply constraints
    if not allow_zero and numeric_value == 0:
        if default is not None:
            return default
        raise ValueError("Zero value not allowed")

    if not allow_negative and numeric_value < 0:
        if default is not None:
            return default
        raise ValueError("Negative value not allowed")

    return numeric_value
