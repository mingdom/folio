"""
Tests for the portfolio service module.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.folib.domain import (
    OptionPosition,
    Portfolio,
    PortfolioHolding,
    PortfolioSummary,
    StockPosition,
)
from src.folib.services.portfolio_service import (
    create_portfolio_summary,
    get_portfolio_exposures,
    process_portfolio,
)


@pytest.fixture
def mock_stockdata():
    """Create a mock stockdata object."""
    mock = MagicMock()
    mock.get_price.return_value = 150.0
    mock.get_beta.return_value = 1.2
    mock.is_valid_stock_symbol.return_value = True
    mock.is_cash_like.return_value = False
    return mock


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for testing."""
    stock_position = StockPosition(
        ticker="AAPL",
        quantity=10,
        price=150.0,
        cost_basis=1400.0,
    )
    option_position = OptionPosition(
        ticker="AAPL",
        quantity=2,
        price=5.0,
        strike=160.0,
        expiry=datetime.date.today() + datetime.timedelta(days=30),
        option_type="CALL",
        cost_basis=900.0,
    )
    return Portfolio(
        positions=[stock_position, option_position],
        pending_activity_value=100.0,
    )


class TestCreatePortfolioSummary:
    """Tests for the create_portfolio_summary function."""

    @patch("src.folib.services.portfolio_service.stockdata")
    @patch("src.folib.services.portfolio_service.calculate_option_delta")
    def test_create_portfolio_summary_with_stock_and_option(
        self, mock_calculate_delta, mock_stockdata, sample_portfolio
    ):
        """Test creating a portfolio summary with stock and option positions."""
        # Arrange
        mock_stockdata.get_price.return_value = 150.0
        mock_stockdata.get_beta.return_value = 1.2
        mock_calculate_delta.return_value = 0.6

        # Act
        summary = create_portfolio_summary(sample_portfolio)

        # Assert
        assert isinstance(summary, PortfolioSummary)
        assert summary.total_value > 0
        assert summary.stock_value == 1500.0  # 10 * 150.0
        assert summary.option_value == 1000.0  # 2 contracts * 100 shares * 5.0
        assert summary.pending_activity_value == 100.0

        # Verify the exposure calculations were called correctly
        mock_stockdata.get_beta.assert_called_with("AAPL")
        mock_calculate_delta.assert_called_once()


class TestGetPortfolioExposures:
    """Tests for the get_portfolio_exposures function."""

    @patch("src.folib.services.portfolio_service.stockdata")
    @patch("src.folib.services.portfolio_service.calculate_option_delta")
    def test_get_portfolio_exposures(
        self, mock_calculate_delta, mock_stockdata, sample_portfolio
    ):
        """Test calculating portfolio exposures."""
        # Arrange
        mock_stockdata.get_price.return_value = 150.0
        mock_stockdata.get_beta.return_value = 1.2
        mock_calculate_delta.return_value = 0.6

        # Act
        exposures = get_portfolio_exposures(sample_portfolio)

        # Assert
        assert isinstance(exposures, dict)
        assert "long_stock_exposure" in exposures
        assert "long_option_exposure" in exposures
        assert "net_market_exposure" in exposures
        assert "beta_adjusted_exposure" in exposures

        # Verify the exposure calculations were called correctly
        mock_stockdata.get_beta.assert_called_with("AAPL")
        mock_calculate_delta.assert_called_once()


class TestProcessPortfolio:
    """Tests for the process_portfolio function."""

    @patch("src.folib.services.portfolio_service.stockdata")
    def test_process_portfolio_with_stock_and_option(self, mock_stockdata):
        """Test processing portfolio holdings into a structured portfolio."""
        # Arrange
        mock_stockdata.is_valid_stock_symbol.return_value = True
        mock_stockdata.is_cash_like.return_value = False

        holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150.0,
                value=1500.0,
                cost_basis_total=1400.0,
            ),
            PortfolioHolding(
                symbol="-AAPL",
                description="AAPL MAY 20 2025 $160 CALL",
                quantity=2,
                price=5.0,
                value=1000.0,
                cost_basis_total=900.0,
            ),
        ]

        # Act
        portfolio = process_portfolio(holdings)

        # Assert
        assert isinstance(portfolio, Portfolio)
        assert len(portfolio.positions) == 2
        assert len(portfolio.stock_positions) == 1
        assert len(portfolio.option_positions) == 1
        assert portfolio.stock_positions[0].ticker == "AAPL"
        assert portfolio.option_positions[0].ticker == "AAPL"
        assert portfolio.option_positions[0].strike == 160.0
        assert portfolio.option_positions[0].option_type == "CALL"
