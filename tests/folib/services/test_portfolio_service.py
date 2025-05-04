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
    get_pending_activity,
    get_portfolio_exposures,
    process_portfolio,
)


@pytest.fixture
def mock_stock_service():
    """Create a mock StockDataService object."""
    mock = MagicMock()
    # Create a mock StockData object
    mock_stock_data = MagicMock()
    mock_stock_data.price = 150.0
    mock_stock_data.beta = 1.2
    mock_stock_data.volatility = 0.25

    # Configure the load_market_data method to return the mock StockData
    mock.load_market_data.return_value = mock_stock_data

    # Configure other methods
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

    @patch("src.folib.services.portfolio_service.default_stock_service")
    @patch("src.folib.services.portfolio_service.calculate_option_delta")
    def test_create_portfolio_summary_with_stock_and_option(
        self, mock_calculate_delta, mock_stock_service, sample_portfolio
    ):
        """Test creating a portfolio summary with stock and option positions."""
        # Arrange
        # Create a mock StockData object
        mock_stock_data = MagicMock()
        mock_stock_data.price = 150.0
        mock_stock_data.beta = 1.2

        # Configure the mock service
        mock_stock_service.load_market_data.return_value = mock_stock_data
        mock_stock_service.is_cash_like.return_value = False
        mock_calculate_delta.return_value = 0.6

        # Act
        summary = create_portfolio_summary(sample_portfolio)

        # Assert
        assert isinstance(summary, PortfolioSummary)
        assert summary.total_value > 0
        assert summary.stock_value == 1500.0  # 10 * 150.0
        assert summary.option_value == 1000.0  # 2 contracts * 100 shares * 5.0
        assert summary.pending_activity_value == 100.0

        # Verify new fields
        assert hasattr(summary, "net_exposure_pct")
        assert hasattr(summary, "beta_adjusted_exposure")
        assert summary.net_exposure_pct >= 0
        assert summary.beta_adjusted_exposure != 0

        # Verify the exposure calculations were called correctly
        mock_stock_service.load_market_data.assert_called_with("AAPL")
        # The function is called at least once for option exposure calculation
        assert mock_calculate_delta.call_count >= 1


class TestGetPortfolioExposures:
    """Tests for the get_portfolio_exposures function."""

    @patch("src.folib.services.portfolio_service.default_stock_service")
    @patch("src.folib.services.portfolio_service.calculate_option_delta")
    def test_get_portfolio_exposures(
        self, mock_calculate_delta, mock_stock_service, sample_portfolio
    ):
        """Test calculating portfolio exposures."""
        # Arrange
        # Create a mock StockData object
        mock_stock_data = MagicMock()
        mock_stock_data.price = 150.0
        mock_stock_data.beta = 1.2

        # Configure the mock service
        mock_stock_service.load_market_data.return_value = mock_stock_data
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
        mock_stock_service.load_market_data.assert_called_with("AAPL")
        mock_calculate_delta.assert_called_once()


class TestProcessPortfolio:
    """Tests for the process_portfolio function."""

    @patch("src.folib.services.portfolio_service.default_stock_service")
    def test_process_portfolio_with_stock_and_option(self, mock_stock_service):
        """Test processing portfolio holdings into a structured portfolio."""
        # Arrange
        mock_stock_service.is_valid_stock_symbol.return_value = True
        mock_stock_service.is_cash_like.return_value = False

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


class TestGetPendingActivity:
    """Tests for the get_pending_activity function."""

    def test_pending_activity_in_current_value_column(self):
        """Test detection of pending activity value in the Current Value column."""
        # Create a test holding with pending activity in Current Value column
        holding = PortfolioHolding(
            symbol="Pending Activity",
            description="",
            quantity=0.0,
            price=0.0,
            value=0.0,
            cost_basis_total=None,
            raw_data={
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Last Price": None,
                "Last Price Change": None,
                "Current Value": "$5000.00",  # Pending activity value in Current Value
                "Today's Gain/Loss Dollar": None,
                "Cost Basis Total": None,
            },
        )

        # Detect pending activity
        pending_activity_value = get_pending_activity(holding)

        # Verify the pending activity value is correctly detected
        assert pending_activity_value == 5000.00

    def test_pending_activity_in_last_price_change_column(self):
        """Test detection of pending activity value in the Last Price Change column."""
        # Create a test holding with pending activity in Last Price Change column
        holding = PortfolioHolding(
            symbol="Pending Activity",
            description="",
            quantity=0.0,
            price=0.0,
            value=0.0,
            cost_basis_total=None,
            raw_data={
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Last Price": None,
                "Last Price Change": "$6000.00",  # Pending activity value in Last Price Change
                "Current Value": None,  # Empty Current Value
                "Today's Gain/Loss Dollar": None,
                "Cost Basis Total": None,
            },
        )

        # Detect pending activity
        pending_activity_value = get_pending_activity(holding)

        # Verify the pending activity value is correctly detected
        assert pending_activity_value == 6000.00

    def test_pending_activity_in_todays_gain_loss_column(self):
        """Test detection of pending activity value in the Today's Gain/Loss Dollar column."""
        # Create a test holding with pending activity in Today's Gain/Loss Dollar column
        holding = PortfolioHolding(
            symbol="Pending Activity",
            description="",
            quantity=0.0,
            price=0.0,
            value=0.0,
            cost_basis_total=None,
            raw_data={
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Last Price": None,
                "Last Price Change": None,
                "Current Value": None,  # Empty Current Value
                "Today's Gain/Loss Dollar": "$7000.00",  # Pending activity value here
                "Cost Basis Total": None,
            },
        )

        # Detect pending activity
        pending_activity_value = get_pending_activity(holding)

        # Verify the pending activity value is correctly detected
        assert pending_activity_value == 7000.00

    def test_pending_activity_with_no_value(self):
        """Test detection of pending activity with no value in any column."""
        # Create a test holding with pending activity but no value
        holding = PortfolioHolding(
            symbol="Pending Activity",
            description="",
            quantity=0.0,
            price=0.0,
            value=0.0,
            cost_basis_total=None,
            raw_data={
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Last Price": None,
                "Last Price Change": None,
                "Current Value": None,  # Empty
                "Today's Gain/Loss Dollar": None,  # Empty
                "Cost Basis Total": None,
            },
        )

        # Detect pending activity
        pending_activity_value = get_pending_activity(holding)

        # Verify the pending activity value is 0 when no value is found
        assert pending_activity_value == 0.0

    def test_pending_activity_with_real_world_csv_format1(self):
        """Test detection of pending activity with a real-world CSV format (Current Value column)."""
        # Create a test holding mimicking the format in portfolio-pending-value1.csv
        holding = PortfolioHolding(
            symbol="Pending Activity",
            description="",
            quantity=0.0,
            price=0.0,
            value=0.0,
            cost_basis_total=None,
            raw_data={
                "Account Number": "Z26522634",
                "Account Name": "GMX",
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Last Price": None,
                "Last Price Change": None,
                "Current Value": "$551528.45",  # Value in Current Value
                "Today's Gain/Loss Dollar": None,
                "Today's Gain/Loss Percent": None,
                "Total Gain/Loss Dollar": None,
                "Total Gain/Loss Percent": None,
                "Percent Of Account": None,
                "Cost Basis Total": None,
                "Average Cost Basis": None,
                "Type": None,
            },
        )

        # Detect pending activity
        pending_activity_value = get_pending_activity(holding)

        # Verify the pending activity value is correctly detected
        assert pending_activity_value == 551528.45

    def test_pending_activity_with_real_world_csv_format2(self):
        """Test detection of pending activity with a real-world CSV format (Last Price Change column)."""
        # Create a test holding mimicking the format in portfolio-pending-value2.csv
        holding = PortfolioHolding(
            symbol="Pending Activity",
            description="",
            quantity=0.0,
            price=0.0,
            value=0.0,
            cost_basis_total=None,
            raw_data={
                "Account Number": "Z26522634",
                "Account Name": "GMX",
                "Symbol": "Pending Activity",
                "Description": "",
                "Quantity": None,
                "Last Price": None,
                "Last Price Change": "$524609.67",  # Value in Last Price Change
                "Current Value": None,  # Empty Current Value
                "Today's Gain/Loss Dollar": None,
                "Today's Gain/Loss Percent": None,
                "Total Gain/Loss Dollar": None,
                "Total Gain/Loss Percent": None,
                "Percent Of Account": None,
                "Cost Basis Total": None,
                "Average Cost Basis": None,
                "Type": None,
            },
        )

        # Detect pending activity
        pending_activity_value = get_pending_activity(holding)

        # Verify the pending activity value is correctly detected
        assert pending_activity_value == 524609.67
