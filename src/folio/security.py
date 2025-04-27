"""
Security utilities for the Folio application.

This module provides security-related functions for validating and sanitizing
user inputs, particularly for CSV file uploads.
"""

import base64
import io
import re
from typing import Any

import pandas as pd

from .logger import logger

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Required columns for portfolio CSV files
REQUIRED_COLUMNS = ["Symbol", "Quantity", "Last Price"]

# Columns that might contain formulas and need sanitization
FORMULA_RISK_COLUMNS = [
    "Symbol",
    "Description",
    "Type",
    "Current Value",
    "Last Price",
    "Last Price Change",
    "Today's Gain/Loss Dollar",
    "Today's Gain/Loss Percent",
    "Total Gain/Loss Dollar",
    "Total Gain/Loss Percent",
    "Percent Of Account",
    "Cost Basis Total",
    "Average Cost Basis",
]

# Regex patterns for detecting potentially malicious content
DANGEROUS_PATTERNS = [
    # Excel formula injection patterns
    r"^=",
    r"^@",
    # Removed r'^[+-]' and r'^-\d' as they flag legitimate financial data
    r"^DDE\(",
    r"^EMBED\(",
    r"^HYPERLINK\(",
    r"^MSEXCEL\|",
    # HTML/JavaScript injection patterns
    r"<script",
    r"javascript:",
    r"<iframe",
    r"<img",
    r"onerror=",
    r"onload=",
    r"onclick=",
    # Command injection patterns - modified to exclude common financial data patterns
    r"[|;`]",  # Removed & to allow S&P in stock names
    r"\$\([^)]*\)",  # Modified to only match $() pattern, not just $ signs
    r"`.*`",
]

# Compiled regex patterns for performance
DANGEROUS_REGEX = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)


def validate_csv_upload(
    contents: str, filename: str | None = None
) -> tuple[pd.DataFrame, str | None]:
    """
    Validate and sanitize a CSV file upload.

    Args:
        contents: Base64-encoded contents of the uploaded file
        filename: Name of the uploaded file (optional, defaults to None for sample data)

    Returns:
        Tuple containing:
        - Validated and sanitized DataFrame
        - Error message (if validation fails, otherwise None)

    Raises:
        ValueError: If validation fails
    """
    # Validate file extension if filename is provided
    if filename is not None and not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported")

    # Decode base64 content
    try:
        # Split the content string and ignore the content type part
        _, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
    except Exception as e:
        logger.error(f"Error decoding file content: {e}")
        raise ValueError(f"Invalid file format: {e!s}") from e

    # Check file size
    if len(decoded) > MAX_FILE_SIZE:
        logger.warning(f"File too large: {len(decoded)} bytes (max {MAX_FILE_SIZE})")
        raise ValueError(f"File too large (max {MAX_FILE_SIZE / 1024 / 1024:.1f}MB)")

    # Parse CSV
    try:
        df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        raise ValueError(f"Invalid CSV format: {e!s}") from e

    # Check for required columns
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        logger.warning(f"Missing required columns: {missing_columns}")
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Sanitize data to prevent CSV injection
    df = sanitize_dataframe(df)

    return df, None


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize a DataFrame to prevent CSV injection and other attacks.

    Args:
        df: DataFrame to sanitize

    Returns:
        Sanitized DataFrame
    """
    # Create a copy to avoid modifying the original
    df_safe = df.copy()

    # Sanitize all string columns
    for col in df_safe.columns:
        if df_safe[col].dtype == "object":
            df_safe[col] = df_safe[col].apply(
                lambda x: sanitize_cell(x) if pd.notna(x) else x
            )

    # Additional sanitization for columns that might contain formulas
    for col in FORMULA_RISK_COLUMNS:
        if col in df_safe.columns and df_safe[col].dtype == "object":
            df_safe[col] = df_safe[col].apply(
                lambda x: sanitize_formula(x) if pd.notna(x) else x
            )

    return df_safe


def sanitize_cell(value: Any) -> str:
    """
    Sanitize a cell value to prevent injection attacks.

    Args:
        value: Cell value to sanitize

    Returns:
        Sanitized value
    """
    # Convert to string if not already
    if not isinstance(value, str):
        return str(value)

    # Check if this is a financial value with currency symbol (e.g., $123.45, -$123.45)
    if re.match(r"^[+-]?\$\d+(\.\d+)?$", value) or re.match(
        r"^\$[+-]?\d+(\.\d+)?$", value
    ):
        # This is a financial value with currency, leave it as is
        return value

    # Check if this is a percentage value (e.g., -12.34%, +12.34%)
    if re.match(r"^[+-]?\d+(\.\d+)?%$", value):
        # This is a percentage value, leave it as is
        return value

    # Check if this is a stock name with ampersand (e.g., "S&P 500")
    if "&" in value and not any(char in value for char in "|;`"):
        # Contains ampersand but no other dangerous chars, leave it as is
        return value

    # Check for dangerous patterns
    if DANGEROUS_REGEX.search(value):
        logger.warning(f"Potentially dangerous content detected: {value}")
        # Remove or neutralize the dangerous content
        return sanitize_dangerous_content(value)

    return value


def sanitize_formula(value: Any) -> str:
    """
    Specifically sanitize formula-like content in cells.

    Args:
        value: Cell value to sanitize

    Returns:
        Sanitized value
    """
    # Convert non-string values to string
    if not isinstance(value, str):
        return str(value)

    # Initialize result with the original value
    result = value

    # Flag to track if we need to neutralize the value
    needs_neutralizing = False

    # Check if this is a financial value with currency symbol (e.g., $123.45, -$123.45)
    is_financial = re.match(r"^[+-]?\$\d+(\.\d+)?$", value) or re.match(
        r"^\$[+-]?\d+(\.\d+)?$", value
    )

    # Check if this is a percentage value (e.g., -12.34%, +12.34%)
    is_percentage = re.match(r"^[+-]?\d+(\.\d+)?%$", value)

    # Check if it's a negative number (integer or float)
    is_negative_number = value.startswith("-") and re.match(r"^-\d+(\.\d+)?$", value)

    # Check if it's a negative dollar amount (e.g., -$123.45)
    is_negative_dollar = value.startswith("-") and re.match(r"^-\$\d+(\.\d+)?$", value)

    # Check if it's a negative percentage (e.g., -12.34%)
    is_negative_percentage = value.startswith("-") and re.match(
        r"^-\d+(\.\d+)?%$", value
    )

    # Determine if we need to neutralize the value
    if value.startswith(("=", "+", "@")):
        needs_neutralizing = True
    elif value.startswith("-") and not (
        is_negative_number or is_negative_dollar or is_negative_percentage
    ):
        needs_neutralizing = True

    # Don't neutralize financial values, percentages, or negative numbers
    if (
        is_financial
        or is_percentage
        or is_negative_number
        or is_negative_dollar
        or is_negative_percentage
    ):
        needs_neutralizing = False

    # Apply neutralization if needed
    if needs_neutralizing:
        result = "'" + value

    return result


def sanitize_dangerous_content(value: str) -> str:
    """
    Sanitize content identified as potentially dangerous.

    Args:
        value: Content to sanitize

    Returns:
        Sanitized content
    """
    # Check if this is a financial value with currency symbol (e.g., $123.45, -$123.45)
    if re.match(r"^[+-]?\$\d+(\.\d+)?$", value) or re.match(
        r"^\$[+-]?\d+(\.\d+)?$", value
    ):
        # This is a financial value with currency, leave it as is
        return value

    # Check if this is a percentage value (e.g., -12.34%, +12.34%)
    if re.match(r"^[+-]?\d+(\.\d+)?%$", value):
        # This is a percentage value, leave it as is
        return value

    # Check if this is a stock name with ampersand (e.g., "S&P 500")
    if "&" in value and not any(char in value for char in "|;`"):
        # Contains ampersand but no other dangerous chars, leave it as is
        return value

    # Replace formula triggers
    value = re.sub(r"^=", "'=", value)
    value = re.sub(r"^@", "'@", value)
    value = re.sub(r"^[+]", "'+", value)

    # Don't modify negative numbers that are actually numbers
    if not re.match(r"^-\d+(\.\d+)?$", value):
        value = re.sub(r"^-", "'-", value)

    # Remove HTML/script tags
    value = re.sub(
        r"<script.*?>.*?</script>", "[REMOVED]", value, flags=re.IGNORECASE | re.DOTALL
    )
    value = re.sub(
        r"<iframe.*?>.*?</iframe>", "[REMOVED]", value, flags=re.IGNORECASE | re.DOTALL
    )
    value = re.sub(r"javascript:", "[REMOVED]", value, flags=re.IGNORECASE)

    # Remove event handlers
    value = re.sub(r"on\w+\s*=", "[REMOVED]=", value, flags=re.IGNORECASE)

    # Remove command injection characters, but preserve ampersands in stock names
    value = re.sub(r"[|;`]", "", value)
    value = re.sub(r"\$\([^)]*\)", "[REMOVED]", value)  # Only match $() pattern
    value = re.sub(r"`.*?`", "", value, flags=re.DOTALL)

    return value
