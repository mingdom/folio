"""
Tests for the portfolio service module.
"""

import datetime
from datetime import date
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
    _parse_option_position,
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

    @patch("src.folib.services.portfolio_service.ticker_service")
    @patch("src.folib.services.portfolio_service.calculate_option_delta")
    def test_create_portfolio_summary_with_stock_and_option(
        self, mock_calculate_delta, mock_ticker_service, sample_portfolio
    ):
        """Test creating a portfolio summary with stock and option positions."""
        # Arrange
        # Configure the mock ticker service
        mock_ticker_service.get_price.return_value = 150.0
        mock_ticker_service.get_beta.return_value = 1.2
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

        # Verify the beta-adjusted exposure calculation is correct
        # Stock exposure: 10 shares * $150 = $1500
        # Option exposure: 2 contracts * 100 shares * 0.6 delta * $150 = $18000
        # Total exposure: $1500 + $18000 = $19500
        # Beta-adjusted: $19500 * 1.2 = $23400
        expected_beta_adjusted = 23400.0
        assert abs(summary.beta_adjusted_exposure - expected_beta_adjusted) < 0.01


class TestGetPortfolioExposures:
    """Tests for the get_portfolio_exposures function."""

    @patch("src.folib.services.portfolio_service.ticker_service")
    @patch("src.folib.services.portfolio_service.calculate_option_delta")
    def test_get_portfolio_exposures(
        self, mock_calculate_delta, mock_ticker_service, sample_portfolio
    ):
        """Test calculating portfolio exposures."""
        # Arrange
        # Configure the mock ticker service
        mock_ticker_service.get_price.return_value = 150.0
        mock_ticker_service.get_beta.return_value = 1.2
        mock_calculate_delta.return_value = 0.6

        # Act
        exposures = get_portfolio_exposures(sample_portfolio)

        # Assert
        assert isinstance(exposures, dict)

        # Verify the exposure values are calculated correctly
        # Stock exposure: 10 shares * $150 = $1500
        assert exposures["long_stock_exposure"] == 1500.0

        # Option exposure: 2 contracts * 100 shares * 0.6 delta * $150 = $18000
        expected_option_exposure = 2 * 100 * 0.6 * 150.0
        assert abs(exposures["long_option_exposure"] - expected_option_exposure) < 0.01

        # Net exposure: long_stock + long_option + short_stock + short_option
        expected_net_exposure = (
            exposures["long_stock_exposure"] + exposures["long_option_exposure"]
        )
        assert abs(exposures["net_market_exposure"] - expected_net_exposure) < 0.01

        # Beta-adjusted exposure: net_exposure * beta
        expected_beta_adjusted = exposures["net_market_exposure"] * 1.2
        assert abs(exposures["beta_adjusted_exposure"] - expected_beta_adjusted) < 0.01


class TestProcessPortfolio:
    """Tests for the process_portfolio function."""

    @patch("src.folib.services.portfolio_service.is_cash_or_short_term")
    def test_process_portfolio_with_stock_and_option(self, mock_is_cash_or_short_term):
        """Test processing portfolio holdings into a structured portfolio."""
        # Arrange
        mock_is_cash_or_short_term.return_value = False

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

        # Create a tuple of holdings and stock_tickers to match the new interface
        holdings_data = (holdings, {"AAPL"})

        # Act
        portfolio = process_portfolio(holdings_data)

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


class TestSPXOptionParsing:
    """Tests for SPX option parsing with special formatting."""

    def test_parse_spx_option_with_comma_and_suffix(self):
        """Test parsing SPX option with comma in strike price and (AM) suffix."""
        holding = PortfolioHolding(
            symbol="-SPX250620P5600",
            description="SPX JUN 20 2025 $5,600 PUT (AM)",
            quantity=-1,
            price=41.50,
            value=-4150.00,
            cost_basis_total=3742.32,
        )

        option_position = _parse_option_position(holding)

        assert option_position is not None
        assert option_position.ticker == "SPX"
        assert option_position.strike == 5600.0
        assert option_position.expiry == date(2025, 6, 20)
        assert option_position.option_type == "PUT"
        assert option_position.quantity == -1
        assert option_position.price == 41.50

    def test_parse_spxw_option_normalizes_to_spx(self):
        """Test parsing SPXW option with comma in strike and normalizes ticker to SPX."""
        holding = PortfolioHolding(
            symbol="-SPXW250620P5920",
            description="SPXW JUN 20 2025 $5,920 PUT",
            quantity=1,
            price=128.70,
            value=12870.00,
            cost_basis_total=12193.68,
        )

        option_position = _parse_option_position(holding)

        assert option_position is not None
        assert option_position.ticker == "SPX"  # Should be normalized from SPXW to SPX
        assert option_position.strike == 5920.0
        assert option_position.expiry == date(2025, 6, 20)
        assert option_position.option_type == "PUT"
        assert option_position.quantity == 1
        assert option_position.price == 128.70

    def test_parse_option_with_large_comma_separated_strike(self):
        """Test parsing option with multi-comma strike price (e.g., $10,000)."""
        holding = PortfolioHolding(
            symbol="-SPX250620C10000",
            description="SPX JUN 20 2025 $10,000 CALL",
            quantity=1,
            price=5.25,
            value=525.00,
            cost_basis_total=500.00,
        )

        option_position = _parse_option_position(holding)

        assert option_position is not None
        assert option_position.ticker == "SPX"
        assert option_position.strike == 10000.0
        assert option_position.expiry == date(2025, 6, 20)
        assert option_position.option_type == "CALL"

    def test_parse_option_with_decimal_strike_and_comma(self):
        """Test parsing option with decimal strike price and comma (e.g., $1,500.50)."""
        holding = PortfolioHolding(
            symbol="-SPX250620P1500",
            description="SPX JUN 20 2025 $1,500.50 PUT",
            quantity=-2,
            price=25.75,
            value=-5150.00,
            cost_basis_total=5000.00,
        )

        option_position = _parse_option_position(holding)

        assert option_position is not None
        assert option_position.ticker == "SPX"
        assert option_position.strike == 1500.50
        assert option_position.expiry == date(2025, 6, 20)
        assert option_position.option_type == "PUT"
