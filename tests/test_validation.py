"""
Tests for validation utilities.
"""

import pandas as pd
import pytest

from src.folio.exceptions import DataError
from src.folio.validation import (
    clean_numeric_value,
    extract_option_data,
    validate_dataframe,
    validate_option_data,
)


class TestValidateOptionData:
    """Tests for validate_option_data function."""

    def test_valid_option_data(self):
        """Test with valid option data."""
        option_row = pd.Series({
            "Description": "SPY JUN 15 2025 $100 CALL",
            "Quantity": "2",
            "Last Price": "5.00",
        })

        description, quantity, price = validate_option_data(option_row)

        assert description == "SPY JUN 15 2025 $100 CALL"
        assert quantity == 2
        assert price == 5.0

    def test_missing_description(self):
        """Test with missing description."""
        option_row = pd.Series({
            "Description": None,
            "Quantity": "2",
            "Last Price": "5.00",
        })

        with pytest.raises(DataError, match="Missing description"):
            validate_option_data(option_row)

    def test_missing_quantity(self):
        """Test with missing quantity."""
        option_row = pd.Series({
            "Description": "SPY JUN 15 2025 $100 CALL",
            "Quantity": None,
            "Last Price": "5.00",
        })

        with pytest.raises(DataError, match="Missing quantity"):
            validate_option_data(option_row)

    def test_invalid_quantity(self):
        """Test with invalid quantity format."""
        option_row = pd.Series({
            "Description": "SPY JUN 15 2025 $100 CALL",
            "Quantity": "not a number",
            "Last Price": "5.00",
        })

        with pytest.raises(DataError, match="Invalid quantity format"):
            validate_option_data(option_row)

    def test_missing_price(self):
        """Test with missing price."""
        option_row = pd.Series({
            "Description": "SPY JUN 15 2025 $100 CALL",
            "Quantity": "2",
            "Last Price": None,
        })

        with pytest.raises(DataError, match="Missing price"):
            validate_option_data(option_row)

    def test_invalid_price(self):
        """Test with invalid price format."""
        option_row = pd.Series({
            "Description": "SPY JUN 15 2025 $100 CALL",
            "Quantity": "2",
            "Last Price": "not a price",
        })

        with pytest.raises(DataError, match="Invalid price format"):
            validate_option_data(option_row)

    def test_custom_field_names(self):
        """Test with custom field names."""
        option_row = pd.Series({
            "OptionDesc": "SPY JUN 15 2025 $100 CALL",
            "OptionQty": "2",
            "OptionPrice": "5.00",
        })

        description, quantity, price = validate_option_data(
            option_row,
            description_field="OptionDesc",
            quantity_field="OptionQty",
            price_field="OptionPrice",
        )

        assert description == "SPY JUN 15 2025 $100 CALL"
        assert quantity == 2
        assert price == 5.0


class TestExtractOptionData:
    """Tests for extract_option_data function."""

    def test_extract_valid_options(self):
        """Test extracting valid options."""
        option_df = pd.DataFrame([
            {
                "Description": "SPY JUN 15 2025 $100 CALL",
                "Symbol": "-SPY",
                "Quantity": "2",
                "Last Price": "5.00",
                "Current Value": "1000.00",
            },
            {
                "Description": "SPY JUN 15 2025 $110 CALL",
                "Symbol": "-SPY",
                "Quantity": "-1",
                "Last Price": "2.00",
                "Current Value": "-200.00",
            },
        ])

        options_data = extract_option_data(option_df)

        assert len(options_data) == 2
        assert options_data[0]["description"] == "SPY JUN 15 2025 $100 CALL"
        assert options_data[0]["quantity"] == 2
        assert options_data[0]["price"] == 5.0
        assert options_data[0]["symbol"] == "-SPY"
        assert "row_index" in options_data[0]

        assert options_data[1]["description"] == "SPY JUN 15 2025 $110 CALL"
        assert options_data[1]["quantity"] == -1
        assert options_data[1]["price"] == 2.0

    def test_extract_with_filter(self):
        """Test extracting options with a filter function."""
        option_df = pd.DataFrame([
            {
                "Description": "SPY JUN 15 2025 $100 CALL",
                "Symbol": "-SPY",
                "Quantity": "2",
                "Last Price": "5.00",
            },
            {
                "Description": "AAPL JUN 15 2025 $200 CALL",
                "Symbol": "-AAPL",
                "Quantity": "1",
                "Last Price": "10.00",
            },
        ])

        # Filter for SPY options only
        options_data = extract_option_data(
            option_df,
            filter_func=lambda row: row["Symbol"] == "-SPY",
        )

        assert len(options_data) == 1
        assert options_data[0]["description"] == "SPY JUN 15 2025 $100 CALL"
        assert options_data[0]["symbol"] == "-SPY"

    def test_extract_with_invalid_options(self):
        """Test extracting options with some invalid data."""
        option_df = pd.DataFrame([
            {
                "Description": "SPY JUN 15 2025 $100 CALL",
                "Symbol": "-SPY",
                "Quantity": "2",
                "Last Price": "5.00",
            },
            {
                "Description": None,  # Invalid: missing description
                "Symbol": "-AAPL",
                "Quantity": "1",
                "Last Price": "10.00",
            },
            {
                "Description": "AAPL JUN 15 2025 $200 CALL",
                "Symbol": "-AAPL",
                "Quantity": "not a number",  # Invalid: bad quantity
                "Last Price": "10.00",
            },
        ])

        options_data = extract_option_data(option_df)

        # Only the first option should be extracted
        assert len(options_data) == 1
        assert options_data[0]["description"] == "SPY JUN 15 2025 $100 CALL"

    def test_extract_without_row_index(self):
        """Test extracting options without including row index."""
        option_df = pd.DataFrame([
            {
                "Description": "SPY JUN 15 2025 $100 CALL",
                "Symbol": "-SPY",
                "Quantity": "2",
                "Last Price": "5.00",
            },
        ])

        options_data = extract_option_data(option_df, include_row_index=False)

        assert len(options_data) == 1
        assert "row_index" not in options_data[0]


class TestValidateDataframe:
    """Tests for validate_dataframe function."""

    def test_valid_dataframe(self):
        """Test with a valid DataFrame."""
        df = pd.DataFrame({
            "Symbol": ["SPY", "AAPL"],
            "Quantity": [10, 20],
            "Price": [100.0, 200.0],
        })

        result = validate_dataframe(df, ["Symbol", "Quantity", "Price"])

        # Should return the original DataFrame
        assert result is df

    def test_none_dataframe(self):
        """Test with None DataFrame."""
        with pytest.raises(DataError, match="dataframe is None"):
            validate_dataframe(None, ["Symbol"])

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()

        with pytest.raises(DataError, match="dataframe is empty"):
            validate_dataframe(df, ["Symbol"])

    def test_missing_columns(self):
        """Test with missing required columns."""
        df = pd.DataFrame({
            "Symbol": ["SPY", "AAPL"],
            "Quantity": [10, 20],
        })

        with pytest.raises(DataError, match="missing required columns: Price"):
            validate_dataframe(df, ["Symbol", "Quantity", "Price"])

    def test_custom_name(self):
        """Test with custom DataFrame name."""
        with pytest.raises(DataError, match="portfolio is None"):
            validate_dataframe(None, ["Symbol"], name="portfolio")


class TestCleanNumericValue:
    """Tests for clean_numeric_value function."""

    def test_valid_numeric(self):
        """Test with valid numeric values."""
        assert clean_numeric_value(10) == 10.0
        assert clean_numeric_value(10.5) == 10.5
        assert clean_numeric_value("10") == 10.0
        assert clean_numeric_value("10.5") == 10.5

    def test_currency_format(self):
        """Test with currency formatted values."""
        assert clean_numeric_value("$10.50") == 10.5
        assert clean_numeric_value("$1,234.56") == 1234.56
        assert clean_numeric_value("($10.50)") == -10.5  # Parentheses for negative

    def test_none_value(self):
        """Test with None value."""
        with pytest.raises(ValueError, match="Value is NaN or None"):
            clean_numeric_value(None)

        # With default
        assert clean_numeric_value(None, default=0) == 0

    def test_nan_value(self):
        """Test with NaN value."""
        with pytest.raises(ValueError, match="Value is NaN or None"):
            clean_numeric_value(float("nan"))

        # With default
        assert clean_numeric_value(float("nan"), default=0) == 0

    def test_invalid_format(self):
        """Test with invalid format."""
        with pytest.raises(ValueError, match="Could not convert"):
            clean_numeric_value("not a number")

        # With default
        assert clean_numeric_value("not a number", default=0) == 0

    def test_zero_constraint(self):
        """Test with zero constraint."""
        with pytest.raises(ValueError, match="Zero value not allowed"):
            clean_numeric_value(0, allow_zero=False)

        # With default
        assert clean_numeric_value(0, allow_zero=False, default=1) == 1

    def test_negative_constraint(self):
        """Test with negative constraint."""
        with pytest.raises(ValueError, match="Negative value not allowed"):
            clean_numeric_value(-10, allow_negative=False)

        # With default
        assert clean_numeric_value(-10, allow_negative=False, default=10) == 10
