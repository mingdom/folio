"""
Tests for the domain models in src.folib.domain.

This module tests the core functionality of the domain model classes,
particularly focusing on the description generation and constructor behavior.
"""

from datetime import date

import pytest

from src.folib.domain import (
    CashPosition,
    OptionPosition,
    StockPosition,
    UnknownPosition,
)


class TestPosition:
    """Tests for the base Position class."""

    def test_position_immutable(self):
        """Test that Position objects are immutable."""
        position = StockPosition(ticker="AAPL", quantity=10, price=150.0)

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            position.ticker = "MSFT"

        with pytest.raises(AttributeError):
            position.quantity = 20

    def test_market_value_calculation(self):
        """Test market value calculation for base position."""
        position = StockPosition(ticker="AAPL", quantity=10, price=150.0)
        assert position.market_value == 1500.0


class TestStockPosition:
    """Tests for the StockPosition class."""

    def test_stock_position_init_basic(self):
        """Test basic StockPosition initialization."""
        position = StockPosition(ticker="AAPL", quantity=10, price=150.0)

        assert position.ticker == "AAPL"
        assert position.quantity == 10
        assert position.price == 150.0
        assert position.position_type == "stock"
        assert position.description == "AAPL Stock"
        assert position.cost_basis is None
        assert position.raw_data is None
        assert position.market_value == 1500.0

    def test_stock_position_init_with_all_params(self):
        """Test StockPosition initialization with all parameters."""
        raw_data = {"symbol": "AAPL", "value": 1500.0}
        position = StockPosition(
            ticker="AAPL",
            quantity=10,
            price=150.0,
            description="Apple Inc. Stock",
            cost_basis=1400.0,
            raw_data=raw_data,
        )

        assert position.ticker == "AAPL"
        assert position.quantity == 10
        assert position.price == 150.0
        assert position.position_type == "stock"
        assert position.description == "Apple Inc. Stock"
        assert position.cost_basis == 1400.0
        assert position.raw_data == raw_data

    def test_stock_position_auto_description(self):
        """Test automatic description generation for stocks."""
        position = StockPosition(ticker="NVDA", quantity=100, price=200.0)
        assert position.description == "NVDA Stock"

    def test_stock_position_custom_description(self):
        """Test custom description override for stocks."""
        position = StockPosition(
            ticker="GOOGL", quantity=50, price=120.0, description="Alphabet Class A"
        )
        assert position.description == "Alphabet Class A"


class TestOptionPosition:
    """Tests for the OptionPosition class."""

    def test_option_position_init_basic(self):
        """Test basic OptionPosition initialization."""
        expiry = date(2024, 1, 19)
        position = OptionPosition(
            ticker="AAPL",
            quantity=2,
            price=5.0,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
        )

        assert position.ticker == "AAPL"
        assert position.quantity == 2
        assert position.price == 5.0
        assert position.position_type == "option"
        assert position.strike == 150.0
        assert position.expiry == expiry
        assert position.option_type == "CALL"
        assert position.description == "AAPL 150C 01-19-24"
        assert position.cost_basis is None
        assert position.raw_data is None
        assert position.market_value == 1000.0  # 2 * 5.0 * 100

    def test_option_position_auto_description_call(self):
        """Test automatic description generation for CALL options."""
        expiry = date(2025, 6, 20)
        position = OptionPosition(
            ticker="SPY",
            quantity=-10,
            price=4.5,
            strike=560.0,
            expiry=expiry,
            option_type="CALL",
        )

        assert position.description == "SPY 560C 06-20-25"

    def test_option_position_auto_description_put(self):
        """Test automatic description generation for PUT options."""
        expiry = date(2025, 12, 18)
        position = OptionPosition(
            ticker="NVDA",
            quantity=5,
            price=12.75,
            strike=135.5,
            expiry=expiry,
            option_type="PUT",
        )

        assert position.description == "NVDA 135.5P 12-18-25"

    def test_option_position_integer_strike(self):
        """Test description with integer strike price."""
        expiry = date(2024, 3, 15)
        position = OptionPosition(
            ticker="TSLA",
            quantity=1,
            price=10.0,
            strike=250.0,  # Integer strike
            expiry=expiry,
            option_type="CALL",
        )

        assert position.description == "TSLA 250C 03-15-24"

    def test_option_position_custom_description(self):
        """Test custom description override for options."""
        expiry = date(2024, 1, 19)
        position = OptionPosition(
            ticker="AAPL",
            quantity=2,
            price=5.0,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
            description="Custom Apple Call Option",
        )

        assert position.description == "Custom Apple Call Option"

    def test_option_position_market_value_calculation(self):
        """Test market value calculation for options (100x multiplier)."""
        expiry = date(2024, 1, 19)
        position = OptionPosition(
            ticker="AAPL",
            quantity=3,
            price=7.50,
            strike=150.0,
            expiry=expiry,
            option_type="PUT",
        )

        # 3 contracts * $7.50 * 100 shares per contract
        assert position.market_value == 2250.0

    def test_option_position_with_all_params(self):
        """Test OptionPosition initialization with all parameters."""
        expiry = date(2024, 6, 21)
        raw_data = {"symbol": "-AAPL240621C150", "description": "Apple Call"}
        position = OptionPosition(
            ticker="AAPL",
            quantity=1,
            price=8.25,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
            description="Custom AAPL Call",
            cost_basis=750.0,
            raw_data=raw_data,
        )

        assert position.ticker == "AAPL"
        assert position.quantity == 1
        assert position.price == 8.25
        assert position.position_type == "option"
        assert position.strike == 150.0
        assert position.expiry == expiry
        assert position.option_type == "CALL"
        assert position.description == "Custom AAPL Call"
        assert position.cost_basis == 750.0
        assert position.raw_data == raw_data
        assert position.market_value == 825.0  # 1 * 8.25 * 100


class TestCashPosition:
    """Tests for the CashPosition class."""

    def test_cash_position_init_basic(self):
        """Test basic CashPosition initialization."""
        position = CashPosition(ticker="SPAXX", quantity=1000, price=1.0)

        assert position.ticker == "SPAXX"
        assert position.quantity == 1000
        assert position.price == 1.0
        assert position.position_type == "cash"
        assert position.description == "SPAXX Cash"
        assert position.cost_basis is None
        assert position.raw_data is None
        assert position.market_value == 1000.0

    def test_cash_position_auto_description(self):
        """Test automatic description generation for cash positions."""
        position = CashPosition(ticker="FMPXX", quantity=5000, price=1.0)
        assert position.description == "FMPXX Cash"

    def test_cash_position_custom_description(self):
        """Test custom description override for cash positions."""
        position = CashPosition(
            ticker="SPAXX",
            quantity=2500,
            price=1.0,
            description="Money Market Fund",
        )
        assert position.description == "Money Market Fund"

    def test_cash_position_with_all_params(self):
        """Test CashPosition initialization with all parameters."""
        raw_data = {"symbol": "SPAXX", "type": "cash"}
        position = CashPosition(
            ticker="SPAXX",
            quantity=10000,
            price=1.0,
            description="Fidelity Money Market",
            cost_basis=10000.0,
            raw_data=raw_data,
        )

        assert position.ticker == "SPAXX"
        assert position.quantity == 10000
        assert position.price == 1.0
        assert position.position_type == "cash"
        assert position.description == "Fidelity Money Market"
        assert position.cost_basis == 10000.0
        assert position.raw_data == raw_data


class TestUnknownPosition:
    """Tests for the UnknownPosition class."""

    def test_unknown_position_init_basic(self):
        """Test basic UnknownPosition initialization."""
        position = UnknownPosition(
            ticker="XYZ123",
            quantity=5,
            price=10.0,
            original_description="Unknown security type",
        )

        assert position.ticker == "XYZ123"
        assert position.quantity == 5
        assert position.price == 10.0
        assert position.position_type == "unknown"
        assert position.original_description == "Unknown security type"
        assert position.description == "Unknown security type"
        assert position.cost_basis is None
        assert position.raw_data is None
        assert position.market_value == 50.0

    def test_unknown_position_with_all_params(self):
        """Test UnknownPosition initialization with all parameters."""
        raw_data = {"symbol": "XYZ123", "desc": "Weird instrument"}
        position = UnknownPosition(
            ticker="XYZ123",
            quantity=10,
            price=25.0,
            original_description="Complex derivative",
            cost_basis=200.0,
            raw_data=raw_data,
        )

        assert position.ticker == "XYZ123"
        assert position.quantity == 10
        assert position.price == 25.0
        assert position.position_type == "unknown"
        assert position.original_description == "Complex derivative"
        assert position.description == "Complex derivative"
        assert position.cost_basis == 200.0
        assert position.raw_data == raw_data
        assert position.market_value == 250.0

    def test_unknown_position_to_dict(self):
        """Test UnknownPosition to_dict method includes original_description."""
        position = UnknownPosition(
            ticker="XYZ123",
            quantity=5,
            price=10.0,
            original_description="Unknown instrument",
            cost_basis=45.0,
        )

        result = position.to_dict()

        assert isinstance(result, dict)
        assert result["ticker"] == "XYZ123"
        assert result["quantity"] == 5
        assert result["price"] == 10.0
        assert result["position_type"] == "unknown"
        assert result["market_value"] == 50.0
        assert result["cost_basis"] == 45.0
        assert result["original_description"] == "Unknown instrument"


class TestPositionDescriptions:
    """Tests for position description behavior across all position types."""

    def test_stock_description_formats(self):
        """Test various stock description formats."""
        # Default format
        pos1 = StockPosition(ticker="AAPL", quantity=10, price=150.0)
        assert pos1.description == "AAPL Stock"

        # Custom format
        pos2 = StockPosition(
            ticker="GOOGL", quantity=10, price=120.0, description="Alphabet Inc."
        )
        assert pos2.description == "Alphabet Inc."

    def test_option_description_date_formats(self):
        """Test option description with various expiry dates."""
        test_cases = [
            (date(2024, 1, 19), "01-19-24"),
            (date(2025, 12, 31), "12-31-25"),
            (date(2026, 6, 5), "06-05-26"),
        ]

        for expiry, expected_date in test_cases:
            position = OptionPosition(
                ticker="TEST",
                quantity=1,
                price=5.0,
                strike=100.0,
                expiry=expiry,
                option_type="CALL",
            )
            expected = f"TEST 100C {expected_date}"
            assert position.description == expected

    def test_option_description_strike_formats(self):
        """Test option description with various strike formats."""
        expiry = date(2024, 1, 19)

        # Integer strike
        pos1 = OptionPosition(
            ticker="TEST",
            quantity=1,
            price=5.0,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
        )
        assert pos1.description == "TEST 150C 01-19-24"

        # Decimal strike
        pos2 = OptionPosition(
            ticker="TEST",
            quantity=1,
            price=5.0,
            strike=150.5,
            expiry=expiry,
            option_type="PUT",
        )
        assert pos2.description == "TEST 150.5P 01-19-24"

    def test_all_position_types_have_descriptions(self):
        """Test that all position types generate descriptions."""
        expiry = date(2024, 1, 19)

        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=expiry,
                option_type="CALL",
            ),
            CashPosition(ticker="SPAXX", quantity=1000, price=1.0),
            UnknownPosition(
                ticker="XYZ", quantity=5, price=10.0, original_description="Unknown"
            ),
        ]

        for position in positions:
            assert hasattr(position, "description")
            assert position.description is not None
            assert len(position.description) > 0
