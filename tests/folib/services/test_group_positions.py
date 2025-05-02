"""
Tests for the group_positions_by_ticker function in portfolio_service.py.
"""

import datetime

import pytest

from src.folib.domain import (
    OptionPosition,
    Portfolio,
    StockPosition,
)
from src.folib.services.portfolio_service import group_positions_by_ticker


@pytest.fixture
def multi_ticker_portfolio():
    """Create a portfolio with multiple tickers for testing."""
    aapl_stock = StockPosition(
        ticker="AAPL",
        quantity=10,
        price=150.0,
        cost_basis=1400.0,
    )
    aapl_option = OptionPosition(
        ticker="AAPL",
        quantity=2,
        price=5.0,
        strike=160.0,
        expiry=datetime.date.today() + datetime.timedelta(days=30),
        option_type="CALL",
        cost_basis=900.0,
    )
    msft_stock = StockPosition(
        ticker="MSFT",
        quantity=5,
        price=300.0,
        cost_basis=1450.0,
    )
    return Portfolio(
        positions=[aapl_stock, aapl_option, msft_stock],
        pending_activity_value=100.0,
    )


class TestGroupPositionsByTicker:
    """Tests for the group_positions_by_ticker function."""

    def test_group_positions_by_ticker(self, multi_ticker_portfolio):
        """Test grouping positions by ticker."""
        # Act
        grouped = group_positions_by_ticker(multi_ticker_portfolio.positions)

        # Assert
        assert isinstance(grouped, dict)
        assert "AAPL" in grouped
        assert "MSFT" in grouped
        assert len(grouped["AAPL"]) == 2
        assert len(grouped["MSFT"]) == 1
        assert grouped["AAPL"][0].position_type == "stock"
        assert grouped["AAPL"][1].position_type == "option"
        assert grouped["MSFT"][0].position_type == "stock"

    def test_group_positions_by_ticker_empty_list(self):
        """Test grouping an empty list of positions."""
        # Act
        grouped = group_positions_by_ticker([])

        # Assert
        assert isinstance(grouped, dict)
        assert len(grouped) == 0
