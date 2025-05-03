"""
Tests for the portfolio loader module.

This module contains tests for the CSV loading and parsing functionality,
focusing on handling different types of portfolio entries including pending activity.
"""

import os
import tempfile
from unittest.mock import patch

import pandas as pd
import pytest

from src.folib.data.loader import (
    clean_currency_value,
    load_portfolio_from_csv,
    parse_portfolio_holdings,
)


class TestCleanCurrencyValue:
    """Tests for the clean_currency_value function."""

    def test_clean_currency_value_with_dollar_sign(self):
        """Test cleaning currency values with dollar signs."""
        assert clean_currency_value("$1,234.56") == 1234.56

    def test_clean_currency_value_with_commas(self):
        """Test cleaning currency values with commas."""
        assert clean_currency_value("1,234.56") == 1234.56

    def test_clean_currency_value_with_parentheses(self):
        """Test cleaning negative currency values in parentheses."""
        assert clean_currency_value("($1,234.56)") == -1234.56

    def test_clean_currency_value_with_empty_string(self):
        """Test cleaning empty currency values."""
        assert clean_currency_value("") == 0.0

    def test_clean_currency_value_with_dashes(self):
        """Test cleaning currency values with dashes."""
        assert clean_currency_value("--") == 0.0


class TestLoadPortfolioFromCSV:
    """Tests for the load_portfolio_from_csv function."""

    def test_load_portfolio_from_csv(self):
        """Test loading a portfolio from a CSV file."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            temp_file.write(
                b"Symbol,Description,Quantity,Last Price,Current Value,Cost Basis Total\n"
                b"AAPL,APPLE INC,10,$150.00,$1500.00,$1000.00\n"
            )
            temp_path = temp_file.name

        try:
            # Load the portfolio
            df = load_portfolio_from_csv(temp_path)
            assert len(df) == 1
            assert df.iloc[0]["Symbol"] == "AAPL"
        finally:
            # Clean up
            os.unlink(temp_path)

    def test_load_portfolio_from_nonexistent_file(self):
        """Test loading a portfolio from a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_portfolio_from_csv("nonexistent_file.csv")

    def test_load_empty_portfolio(self):
        """Test loading an empty portfolio."""
        # Create a temporary CSV file with just headers
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            temp_file.write(
                b"Symbol,Description,Quantity,Last Price,Current Value,Cost Basis Total\n"
            )
            temp_path = temp_file.name

        try:
            # Load the portfolio
            with pytest.raises(ValueError, match="Portfolio CSV file is empty"):
                load_portfolio_from_csv(temp_path)
        finally:
            # Clean up
            os.unlink(temp_path)


class TestParsePortfolioHoldings:
    """Tests for the parse_portfolio_holdings function."""

    def test_parse_portfolio_holdings(self):
        """Test parsing portfolio holdings from a DataFrame."""
        # Create a test DataFrame
        df = pd.DataFrame({
            "Symbol": ["AAPL", "MSFT"],
            "Description": ["APPLE INC", "MICROSOFT CORP"],
            "Quantity": [10, 5],
            "Last Price": ["$150.00", "$300.00"],
            "Current Value": ["$1500.00", "$1500.00"],
            "Cost Basis Total": ["$1000.00", "$1200.00"],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 2
        assert holdings[0].symbol == "AAPL"
        assert holdings[0].quantity == 10
        assert holdings[0].price == 150.0
        assert holdings[0].value == 1500.0
        assert holdings[0].cost_basis_total == 1000.0

    def test_parse_portfolio_holdings_with_empty_symbols(self):
        """Test parsing portfolio holdings with empty symbols."""
        # Create a test DataFrame with an empty symbol
        df = pd.DataFrame({
            "Symbol": ["AAPL", ""],
            "Description": ["APPLE INC", "EMPTY SYMBOL"],
            "Quantity": [10, 5],
            "Last Price": ["$150.00", "$300.00"],
            "Current Value": ["$1500.00", "$1500.00"],
            "Cost Basis Total": ["$1000.00", "$1200.00"],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 1
        assert holdings[0].symbol == "AAPL"

    def test_parse_portfolio_holdings_with_invalid_values(self):
        """Test parsing portfolio holdings with invalid values."""
        # Create a test DataFrame with invalid values
        df = pd.DataFrame({
            "Symbol": ["AAPL", "MSFT"],
            "Description": ["APPLE INC", "MICROSOFT CORP"],
            "Quantity": [10, "invalid"],
            "Last Price": ["$150.00", "invalid"],
            "Current Value": ["$1500.00", "invalid"],
            "Cost Basis Total": ["$1000.00", "invalid"],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 2
        assert holdings[0].symbol == "AAPL"
        assert holdings[0].quantity == 10
        assert holdings[0].price == 150.0
        assert holdings[0].value == 1500.0
        assert holdings[0].cost_basis_total == 1000.0
        assert holdings[1].symbol == "MSFT"
        assert holdings[1].quantity == 0.0
        assert holdings[1].price == 0.0
        assert holdings[1].value == 0.0
        assert holdings[1].cost_basis_total is None

    def test_parse_portfolio_holdings_with_pending_activity(self):
        """Test parsing portfolio holdings with pending activity."""
        # Create a test DataFrame with pending activity
        df = pd.DataFrame({
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [10, ""],
            "Last Price": ["$150.00", ""],
            "Current Value": ["$1500.00", "$529535.51"],
            "Cost Basis Total": ["$1000.00", ""],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 2
        assert holdings[0].symbol == "AAPL"
        assert holdings[1].symbol == "Pending Activity"
        assert holdings[1].quantity == 0
        assert holdings[1].price == 0.0
        assert holdings[1].value == 529535.51

    def test_parse_portfolio_holdings_with_fidelity_format_pending_activity(self):
        """Test parsing portfolio holdings with Fidelity-format pending activity."""
        # Create a test DataFrame with Fidelity-format pending activity
        # Format: Z26522634,GMX,Pending Activity,,,,,$529535.51,,,,,,,,
        df = pd.DataFrame({
            "Account Number": ["Z26522634", "Z26522634"],
            "Account Name": ["GMX", "GMX"],
            "Symbol": ["AAPL", "Pending Activity"],
            "Description": ["APPLE INC", ""],
            "Quantity": [10, ""],
            "Last Price": ["$150.00", ""],
            "Last Price Change": ["$1.00", ""],
            "Current Value": ["$1500.00", "$529535.51"],
            "Today's Gain/Loss Dollar": ["$10.00", ""],
            "Today's Gain/Loss Percent": ["0.67%", ""],
            "Total Gain/Loss Dollar": ["$500.00", ""],
            "Total Gain/Loss Percent": ["50.00%", ""],
            "Percent Of Account": ["1.00%", ""],
            "Cost Basis Total": ["$1000.00", ""],
            "Average Cost Basis": ["$100.00", ""],
            "Type": ["Margin", ""],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 2
        assert holdings[0].symbol == "AAPL"
        assert holdings[1].symbol == "Pending Activity"
        assert holdings[1].quantity == 0
        assert holdings[1].price == 0.0
        assert holdings[1].value == 529535.51

    @patch("src.folib.data.loader.logger")
    def test_parse_portfolio_holdings_with_pending_activity_logging(self, mock_logger):
        """Test that pending activity parsing is properly logged."""
        # Create a test DataFrame with pending activity
        df = pd.DataFrame({
            "Symbol": ["Pending Activity"],
            "Description": [""],
            "Quantity": [""],
            "Last Price": [""],
            "Current Value": ["$529535.51"],
            "Cost Basis Total": [""],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 1
        assert holdings[0].symbol == "Pending Activity"
        assert holdings[0].value == 529535.51

        # Check that the correct log messages were generated
        mock_logger.debug.assert_any_call("Row 0: Identified pending activity row")
        mock_logger.debug.assert_any_call(
            "Found pending activity value in Current Value column: 529535.51"
        )

    def test_parse_portfolio_holdings_with_special_symbols(self):
        """Test parsing portfolio holdings with special symbols like SPAXX**."""
        # Create a test DataFrame with a special symbol
        df = pd.DataFrame({
            "Symbol": ["SPAXX**"],
            "Description": ["FIDELITY GOVERNMENT MONEY MARKET"],
            "Quantity": [""],
            "Last Price": [""],
            "Current Value": ["$51151.25"],
            "Cost Basis Total": [""],
        })

        # Parse the holdings
        holdings = parse_portfolio_holdings(df)
        assert len(holdings) == 1
        assert holdings[0].symbol == "SPAXX"  # ** should be removed
        assert holdings[0].quantity == 1.0  # Should be set to 1.0 for cash positions
        assert holdings[0].price == 51151.25  # Should be calculated from value/quantity
        assert holdings[0].value == 51151.25

    @patch("src.folib.data.loader.logger")
    def test_parse_portfolio_holdings_with_special_symbols_logging(self, mock_logger):
        """Test that special symbol cleaning is properly logged."""
        # Create a test DataFrame with a special symbol
        df = pd.DataFrame({
            "Symbol": ["SPAXX**"],
            "Description": ["FIDELITY GOVERNMENT MONEY MARKET"],
            "Quantity": [""],
            "Last Price": [""],
            "Current Value": ["$51151.25"],
            "Cost Basis Total": [""],
        })

        # Mock the is_cash_like method to return True
        with patch("src.folib.data.stock.stockdata.is_cash_like", return_value=True):
            # Parse the holdings
            holdings = parse_portfolio_holdings(df)
            assert len(holdings) == 1
            assert holdings[0].symbol == "SPAXX"  # ** should be removed

            # Check that the correct log messages were generated
            mock_logger.debug.assert_any_call(
                "Row 0: Cleaned up symbol from SPAXX** to SPAXX"
            )
            mock_logger.debug.assert_any_call(
                "Row 0: Identified SPAXX as a cash-like position"
            )
            mock_logger.debug.assert_any_call(
                "Row 0: Set quantity to 1.0 for cash position SPAXX"
            )
            mock_logger.debug.assert_any_call(
                "Row 0: Calculated price for cash position SPAXX: 51151.25"
            )
