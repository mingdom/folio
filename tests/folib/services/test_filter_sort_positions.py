"""
Tests for the position filtering and sorting functions.

This module contains tests for the filter_positions_by_criteria and sort_positions functions.
"""

from datetime import date

from src.folib.domain import (
    CashPosition,
    OptionPosition,
    StockPosition,
    UnknownPosition,
)
from src.folib.services.portfolio_service import (
    filter_positions_by_criteria,
    sort_positions,
)


class TestFilterPositionsByCriteria:
    """Tests for the filter_positions_by_criteria function."""

    def test_filter_by_type(self):
        """Test filtering positions by type."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),
            CashPosition(ticker="SPAXX", quantity=1, price=1.0),
            UnknownPosition(
                ticker="XYZ", quantity=5, price=10.0, description="Unknown"
            ),
        ]

        # Filter by type=stock
        filtered = filter_positions_by_criteria(positions, {"type": "stock"})
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"
        assert filtered[0].position_type == "stock"

        # Filter by type=option
        filtered = filter_positions_by_criteria(positions, {"type": "option"})
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"
        assert filtered[0].position_type == "option"

        # Filter by type=cash
        filtered = filter_positions_by_criteria(positions, {"type": "cash"})
        assert len(filtered) == 1
        assert filtered[0].ticker == "SPAXX"
        assert filtered[0].position_type == "cash"

        # Filter by type=unknown
        filtered = filter_positions_by_criteria(positions, {"type": "unknown"})
        assert len(filtered) == 1
        assert filtered[0].ticker == "XYZ"
        assert filtered[0].position_type == "unknown"

    def test_filter_by_symbol(self):
        """Test filtering positions by symbol."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),
            StockPosition(ticker="MSFT", quantity=5, price=300.0),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),
        ]

        # Filter by symbol=AAPL
        filtered = filter_positions_by_criteria(positions, {"symbol": "AAPL"})
        assert len(filtered) == 2
        assert all(p.ticker == "AAPL" for p in filtered)

        # Filter by symbol=MSFT
        filtered = filter_positions_by_criteria(positions, {"symbol": "MSFT"})
        assert len(filtered) == 1
        assert filtered[0].ticker == "MSFT"

        # Filter by symbol=GOOGL (no matches)
        filtered = filter_positions_by_criteria(positions, {"symbol": "GOOGL"})
        assert len(filtered) == 0

        # Test case insensitivity
        filtered = filter_positions_by_criteria(positions, {"symbol": "aapl"})
        assert len(filtered) == 2
        assert all(p.ticker == "AAPL" for p in filtered)

    def test_filter_by_value_range(self):
        """Test filtering positions by value range."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),  # Value: 1500
            StockPosition(ticker="MSFT", quantity=5, price=300.0),  # Value: 1500
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),  # Value: 500 (100 shares per contract)
            CashPosition(ticker="SPAXX", quantity=1000, price=1.0),  # Value: 1000
        ]

        # Print market values for debugging
        for _p in positions:
            pass

        # Filter by min_value=1000
        filtered = filter_positions_by_criteria(positions, {"min_value": "1000"})
        filtered_tickers = [p.ticker for p in filtered]

        # We expect AAPL stock, MSFT stock, and SPAXX cash to be above 1000
        assert "MSFT" in filtered_tickers
        assert "SPAXX" in filtered_tickers
        # AAPL appears twice (stock and option), so we need to check if AAPL stock is in the filtered positions
        assert any(p.ticker == "AAPL" and p.position_type == "stock" for p in filtered)

        # Filter by max_value=500
        filtered = filter_positions_by_criteria(positions, {"max_value": "500"})
        filtered_tickers = [p.ticker for p in filtered]
        [p.position_type for p in filtered]

        # We expect only the AAPL option to be below 500
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"
        assert filtered[0].position_type == "option"

        # Filter by min_value=1000 and max_value=1500
        filtered = filter_positions_by_criteria(
            positions, {"min_value": "1000", "max_value": "1500"}
        )
        filtered_tickers = [p.ticker for p in filtered]

        # We expect AAPL stock, MSFT stock, and SPAXX cash to be between 1000 and 1500
        assert "MSFT" in filtered_tickers
        assert "SPAXX" in filtered_tickers
        assert any(p.ticker == "AAPL" and p.position_type == "stock" for p in filtered)

        # Test with invalid value
        filtered = filter_positions_by_criteria(positions, {"min_value": "invalid"})
        assert len(filtered) == 4  # No filtering applied

    def test_filter_by_multiple_criteria(self):
        """Test filtering positions by multiple criteria."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),  # Value: 1500
            StockPosition(ticker="MSFT", quantity=5, price=300.0),  # Value: 1500
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),  # Value: 500 (100 shares per contract)
            CashPosition(ticker="SPAXX", quantity=1000, price=1.0),  # Value: 1000
        ]

        # Filter by type=stock and min_value=1000
        filtered = filter_positions_by_criteria(
            positions, {"type": "stock", "min_value": "1000"}
        )
        assert len(filtered) == 2
        assert all(p.position_type == "stock" for p in filtered)
        assert all(p.market_value >= 1000 for p in filtered)

        # Filter by symbol=AAPL and type=stock
        filtered = filter_positions_by_criteria(
            positions, {"symbol": "AAPL", "type": "stock"}
        )
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"
        assert filtered[0].position_type == "stock"

        # Filter by symbol=AAPL and max_value=1000
        filtered = filter_positions_by_criteria(
            positions, {"symbol": "AAPL", "max_value": "1000"}
        )
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"
        assert filtered[0].position_type == "option"


class TestSortPositions:
    """Tests for the sort_positions function."""

    def test_sort_by_value(self):
        """Test sorting positions by value."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),  # Value: 1500
            StockPosition(ticker="MSFT", quantity=5, price=300.0),  # Value: 1500
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),  # Value: 500 (100 shares per contract)
            CashPosition(ticker="SPAXX", quantity=1000, price=1.0),  # Value: 1000
        ]

        # Sort by value (descending by default)
        sorted_positions = sort_positions(positions, "value")
        assert sorted_positions[0].ticker in ["AAPL", "MSFT"]  # Both have value 1500
        assert sorted_positions[1].ticker in ["AAPL", "MSFT"]
        assert sorted_positions[2].ticker == "SPAXX"  # Value 1000
        assert sorted_positions[3].ticker == "AAPL"  # Option with value 500

        # Sort by value (ascending)
        sorted_positions = sort_positions(positions, "value", "asc")
        assert sorted_positions[0].ticker == "AAPL"  # Option with value 500
        assert sorted_positions[1].ticker == "SPAXX"  # Value 1000
        assert sorted_positions[2].ticker in ["AAPL", "MSFT"]  # Both have value 1500
        assert sorted_positions[3].ticker in ["AAPL", "MSFT"]

    def test_sort_by_symbol(self):
        """Test sorting positions by symbol."""
        # Create test positions
        positions = [
            StockPosition(ticker="MSFT", quantity=5, price=300.0),
            StockPosition(ticker="AAPL", quantity=10, price=150.0),
            CashPosition(ticker="SPAXX", quantity=1000, price=1.0),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),
        ]

        # Sort by symbol (descending)
        sorted_positions = sort_positions(positions, "symbol")
        assert sorted_positions[0].ticker == "SPAXX"
        assert sorted_positions[1].ticker == "MSFT"
        assert sorted_positions[2].ticker == "AAPL"
        assert sorted_positions[3].ticker == "AAPL"

        # Sort by symbol (ascending)
        sorted_positions = sort_positions(positions, "symbol", "asc")
        assert sorted_positions[0].ticker == "AAPL"
        assert sorted_positions[1].ticker == "AAPL"
        assert sorted_positions[2].ticker == "MSFT"
        assert sorted_positions[3].ticker == "SPAXX"

    def test_sort_by_type(self):
        """Test sorting positions by type."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5.0,
                strike=160.0,
                expiry=date(2023, 12, 15),
                option_type="CALL",
            ),
            CashPosition(ticker="SPAXX", quantity=1000, price=1.0),
            UnknownPosition(
                ticker="XYZ", quantity=5, price=10.0, description="Unknown"
            ),
        ]

        # Sort by type (descending)
        sorted_positions = sort_positions(positions, "type")
        assert sorted_positions[0].position_type == "unknown"
        assert sorted_positions[1].position_type == "stock"
        assert sorted_positions[2].position_type == "option"
        assert sorted_positions[3].position_type == "cash"

        # Sort by type (ascending)
        sorted_positions = sort_positions(positions, "type", "asc")
        assert sorted_positions[0].position_type == "cash"
        assert sorted_positions[1].position_type == "option"
        assert sorted_positions[2].position_type == "stock"
        assert sorted_positions[3].position_type == "unknown"

    def test_sort_with_invalid_sort_by(self):
        """Test sorting with an invalid sort_by parameter."""
        # Create test positions
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150.0),  # Value: 1500
            StockPosition(ticker="MSFT", quantity=5, price=300.0),  # Value: 1500
        ]

        # Sort with invalid sort_by (should default to value)
        sorted_positions = sort_positions(positions, "invalid")
        # Both have the same value, so order doesn't matter
        assert len(sorted_positions) == 2
        assert sorted_positions[0].ticker in ["AAPL", "MSFT"]
        assert sorted_positions[1].ticker in ["AAPL", "MSFT"]
