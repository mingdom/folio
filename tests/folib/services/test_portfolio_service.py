"""
Unit tests for the portfolio service module.

These tests verify that the portfolio service functions correctly process
portfolio holdings and calculate portfolio metrics.
"""

from datetime import date
from unittest.mock import patch

import pytest

from src.folib.domain import (
    CashPosition,
    OptionPosition,
    Portfolio,
    PortfolioHolding,
    PortfolioSummary,
    StockPosition,
    UnknownPosition,
)
from src.folib.services.portfolio_service import (
    create_portfolio_summary,
    get_option_positions_by_ticker,
    get_portfolio_exposures,
    get_positions_by_ticker,
    get_positions_by_type,
    get_stock_position_by_ticker,
    group_positions_by_ticker,
    process_portfolio,
)


class TestPositionHelperFunctions:
    """Tests for the position helper functions."""

    def test_group_positions_by_ticker(self):
        """Test that positions are correctly grouped by ticker."""
        # Arrange
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150),
            StockPosition(ticker="MSFT", quantity=5, price=200),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5,
                strike=160,
                expiry=date(2025, 6, 20),
                option_type="CALL",
            ),
        ]

        # Act
        grouped = group_positions_by_ticker(positions)

        # Assert
        assert len(grouped) == 2
        assert "AAPL" in grouped
        assert "MSFT" in grouped
        assert len(grouped["AAPL"]) == 2
        assert len(grouped["MSFT"]) == 1
        assert isinstance(grouped["AAPL"][0], StockPosition)
        assert isinstance(grouped["AAPL"][1], OptionPosition)
        assert isinstance(grouped["MSFT"][0], StockPosition)

    def test_get_positions_by_ticker(self):
        """Test that positions are correctly filtered by ticker."""
        # Arrange
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150),
            StockPosition(ticker="MSFT", quantity=5, price=200),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5,
                strike=160,
                expiry=date(2025, 6, 20),
                option_type="CALL",
            ),
        ]

        # Act
        aapl_positions = get_positions_by_ticker(positions, "AAPL")
        msft_positions = get_positions_by_ticker(positions, "MSFT")
        goog_positions = get_positions_by_ticker(positions, "GOOG")

        # Assert
        assert len(aapl_positions) == 2
        assert len(msft_positions) == 1
        assert len(goog_positions) == 0
        assert aapl_positions[0].ticker == "AAPL"
        assert aapl_positions[1].ticker == "AAPL"
        assert msft_positions[0].ticker == "MSFT"

    def test_get_stock_position_by_ticker(self):
        """Test that stock positions are correctly retrieved by ticker."""
        # Arrange
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150),
            StockPosition(ticker="MSFT", quantity=5, price=200),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5,
                strike=160,
                expiry=date(2025, 6, 20),
                option_type="CALL",
            ),
        ]

        # Act
        aapl_stock = get_stock_position_by_ticker(positions, "AAPL")
        msft_stock = get_stock_position_by_ticker(positions, "MSFT")
        goog_stock = get_stock_position_by_ticker(positions, "GOOG")

        # Assert
        assert aapl_stock is not None
        assert msft_stock is not None
        assert goog_stock is None
        assert aapl_stock.ticker == "AAPL"
        assert aapl_stock.quantity == 10
        assert aapl_stock.price == 150
        assert msft_stock.ticker == "MSFT"
        assert msft_stock.quantity == 5
        assert msft_stock.price == 200

    def test_get_option_positions_by_ticker(self):
        """Test that option positions are correctly retrieved by ticker."""
        # Arrange
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5,
                strike=160,
                expiry=date(2025, 6, 20),
                option_type="CALL",
            ),
            OptionPosition(
                ticker="AAPL",
                quantity=-2,
                price=3,
                strike=170,
                expiry=date(2025, 6, 20),
                option_type="CALL",
            ),
            OptionPosition(
                ticker="MSFT",
                quantity=1,
                price=4,
                strike=210,
                expiry=date(2025, 6, 20),
                option_type="PUT",
            ),
        ]

        # Act
        aapl_options = get_option_positions_by_ticker(positions, "AAPL")
        msft_options = get_option_positions_by_ticker(positions, "MSFT")
        goog_options = get_option_positions_by_ticker(positions, "GOOG")

        # Assert
        assert len(aapl_options) == 2
        assert len(msft_options) == 1
        assert len(goog_options) == 0
        assert aapl_options[0].ticker == "AAPL"
        assert aapl_options[0].strike == 160
        assert aapl_options[0].option_type == "CALL"
        assert aapl_options[1].ticker == "AAPL"
        assert aapl_options[1].strike == 170
        assert aapl_options[1].option_type == "CALL"
        assert msft_options[0].ticker == "MSFT"
        assert msft_options[0].strike == 210
        assert msft_options[0].option_type == "PUT"

    def test_get_positions_by_type(self):
        """Test that positions are correctly filtered by type."""
        # Arrange
        positions = [
            StockPosition(ticker="AAPL", quantity=10, price=150),
            StockPosition(ticker="MSFT", quantity=5, price=200),
            OptionPosition(
                ticker="AAPL",
                quantity=1,
                price=5,
                strike=160,
                expiry=date(2025, 6, 20),
                option_type="CALL",
            ),
            CashPosition(ticker="FMPXX", quantity=1000, price=1),
            UnknownPosition(
                ticker="UNKNOWN", quantity=1, price=10, description="Unknown position"
            ),
        ]

        # Act
        stock_positions = get_positions_by_type(positions, "stock")
        option_positions = get_positions_by_type(positions, "option")
        cash_positions = get_positions_by_type(positions, "cash")
        unknown_positions = get_positions_by_type(positions, "unknown")

        # Assert
        assert len(stock_positions) == 2
        assert len(option_positions) == 1
        assert len(cash_positions) == 1
        assert len(unknown_positions) == 1
        assert all(p.position_type == "stock" for p in stock_positions)
        assert all(p.position_type == "option" for p in option_positions)
        assert all(p.position_type == "cash" for p in cash_positions)
        assert all(p.position_type == "unknown" for p in unknown_positions)


class TestProcessPortfolio:
    """Tests for the process_portfolio function."""

    def test_process_portfolio_with_stock_positions(self):
        """Test that process_portfolio correctly processes stock positions."""
        # Arrange
        holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150,
                value=1500,
                cost_basis_total=1400,
            ),
            PortfolioHolding(
                symbol="MSFT",
                description="MICROSOFT CORP",
                quantity=5,
                price=200,
                value=1000,
                cost_basis_total=950,
            ),
        ]

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock
            mock_oracle.is_cash_like.return_value = False
            mock_oracle.is_valid_stock_symbol.return_value = True

            # Act
            portfolio = process_portfolio(holdings)

            # Assert
            assert len(portfolio.positions) == 2
            assert len(portfolio.stock_positions) == 2
            assert len(portfolio.option_positions) == 0
            assert len(portfolio.cash_positions) == 0
            assert len(portfolio.unknown_positions) == 0

            # Check the first stock position
            stock1 = portfolio.stock_positions[0]
            assert stock1.ticker == "AAPL"
            assert stock1.quantity == 10
            assert stock1.price == 150
            assert stock1.cost_basis == 1400
            assert stock1.market_value == 1500

            # Check the second stock position
            stock2 = portfolio.stock_positions[1]
            assert stock2.ticker == "MSFT"
            assert stock2.quantity == 5
            assert stock2.price == 200
            assert stock2.cost_basis == 950
            assert stock2.market_value == 1000

    def test_process_portfolio_with_cash_positions(self):
        """Test that process_portfolio correctly processes cash positions."""
        # Arrange
        holdings = [
            PortfolioHolding(
                symbol="FMPXX",
                description="FIDELITY MONEY MARKET",
                quantity=1000,
                price=1,
                value=1000,
                cost_basis_total=1000,
            ),
        ]

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock to identify cash-like positions
            mock_oracle.is_cash_like.return_value = True

            # Act
            portfolio = process_portfolio(holdings)

            # Assert
            assert len(portfolio.positions) == 1
            assert len(portfolio.stock_positions) == 0
            assert len(portfolio.option_positions) == 0
            assert len(portfolio.cash_positions) == 1
            assert len(portfolio.unknown_positions) == 0

            # Check the cash position
            cash = portfolio.cash_positions[0]
            assert cash.ticker == "FMPXX"
            assert cash.quantity == 1000
            assert cash.price == 1
            assert cash.cost_basis == 1000
            assert cash.market_value == 1000
            assert cash.position_type == "cash"

    def test_process_portfolio_with_option_positions(self):
        """Test that process_portfolio correctly processes option positions."""
        # Arrange
        holdings = [
            PortfolioHolding(
                symbol="-AAPL",
                description="AAPL JUN 20 2025 $160 CALL",
                quantity=1,
                price=5,
                value=500,  # 1 contract * 100 shares * $5
                cost_basis_total=450,
            ),
        ]

        # Mock the stock oracle and option extraction to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock
            mock_oracle.is_cash_like.return_value = False
            mock_oracle.is_valid_stock_symbol.return_value = False

            # Mock the _is_valid_option_symbol and _extract_option_data functions
            with patch(
                "src.folib.services.portfolio_service._is_valid_option_symbol"
            ) as mock_is_option:
                mock_is_option.return_value = True

                with patch(
                    "src.folib.services.portfolio_service._extract_option_data"
                ) as mock_extract:
                    mock_extract.return_value = (
                        "AAPL",
                        160.0,
                        date(2025, 6, 20),
                        "CALL",
                        1,
                    )

                    # Act
                    portfolio = process_portfolio(holdings)

                    # Assert
                    assert len(portfolio.positions) == 1
                    assert len(portfolio.stock_positions) == 0
                    assert len(portfolio.option_positions) == 1
                    assert len(portfolio.cash_positions) == 0
                    assert len(portfolio.unknown_positions) == 0

                    # Check the option position
                    option = portfolio.option_positions[0]
                    assert option.ticker == "AAPL"
                    assert option.quantity == 1
                    assert option.price == 5
                    assert option.strike == 160
                    assert option.expiry == date(2025, 6, 20)
                    assert option.option_type == "CALL"
                    assert option.cost_basis == 450
                    assert option.market_value == 500
                    assert option.position_type == "option"

    def test_process_portfolio_with_unknown_positions(self):
        """Test that process_portfolio correctly processes unknown positions."""
        # Arrange
        holdings = [
            PortfolioHolding(
                symbol="UNKNOWN",
                description="UNKNOWN SECURITY",
                quantity=1,
                price=10,
                value=10,
                cost_basis_total=9,
            ),
        ]

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock to reject all position types
            mock_oracle.is_cash_like.return_value = False
            mock_oracle.is_valid_stock_symbol.return_value = False

            # Mock the _is_valid_option_symbol function
            with patch(
                "src.folib.services.portfolio_service._is_valid_option_symbol"
            ) as mock_is_option:
                mock_is_option.return_value = False

                # Act
                portfolio = process_portfolio(holdings)

                # Assert
                assert len(portfolio.positions) == 1
                assert len(portfolio.stock_positions) == 0
                assert len(portfolio.option_positions) == 0
                assert len(portfolio.cash_positions) == 0
                assert len(portfolio.unknown_positions) == 1

                # Check the unknown position
                unknown = portfolio.unknown_positions[0]
                assert unknown.ticker == "UNKNOWN"
                assert unknown.quantity == 1
                assert unknown.price == 10
                assert unknown.cost_basis == 9
                assert unknown.market_value == 10
                assert unknown.position_type == "unknown"
                assert unknown.description == "UNKNOWN SECURITY"

    def test_process_portfolio_with_pending_activity(self):
        """Test that process_portfolio correctly handles pending activity."""
        # Arrange
        holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150,
                value=1500,
                cost_basis_total=1400,
            ),
            PortfolioHolding(
                symbol="PENDING ACTIVITY",
                description="Pending Activity",
                quantity=1,
                price=0,
                value=500,
                cost_basis_total=None,
            ),
        ]

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock
            mock_oracle.is_cash_like.return_value = False
            mock_oracle.is_valid_stock_symbol.return_value = True

            # Act
            portfolio = process_portfolio(holdings)

            # Assert
            assert len(portfolio.positions) == 1  # Only the AAPL position
            assert portfolio.pending_activity_value == 500


class TestCreatePortfolioSummary:
    """Tests for the create_portfolio_summary function."""

    def test_create_portfolio_summary_with_mixed_positions(self):
        """Test that create_portfolio_summary correctly calculates summary metrics."""
        # Arrange
        # Create a portfolio with mixed position types
        stock1 = StockPosition(ticker="AAPL", quantity=10, price=150)
        stock2 = StockPosition(ticker="MSFT", quantity=5, price=200)
        option = OptionPosition(
            ticker="AAPL",
            quantity=1,
            price=5,
            strike=160,
            expiry=date(2025, 6, 20),
            option_type="CALL",
        )
        cash = CashPosition(ticker="FMPXX", quantity=1000, price=1)
        unknown = UnknownPosition(
            ticker="UNKNOWN", quantity=1, price=10, description="Unknown position"
        )

        portfolio = Portfolio(
            positions=[stock1, stock2, option, cash, unknown],
            pending_activity_value=500,
        )

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock to return beta values
            mock_oracle.get_beta.side_effect = (
                lambda ticker: 1.2 if ticker == "AAPL" else 1.0
            )

            # Act
            summary = create_portfolio_summary(portfolio)

            # Assert
            assert isinstance(summary, PortfolioSummary)
            assert summary.total_value == 4510  # 1500 + 1000 + 500 + 1000 + 10 + 500
            assert summary.stock_value == 2500  # 1500 + 1000
            assert summary.option_value == 500  # 500
            assert summary.cash_value == 1000  # 1000
            assert summary.unknown_value == 10  # 10
            assert summary.pending_activity_value == 500  # 500
            assert summary.portfolio_beta == 1.12  # (1500*1.2 + 1000*1.0) / 2500

    def test_create_portfolio_summary_with_empty_portfolio(self):
        """Test that create_portfolio_summary handles empty portfolios correctly."""
        # Arrange
        portfolio = Portfolio(positions=[], pending_activity_value=0)

        # Act
        summary = create_portfolio_summary(portfolio)

        # Assert
        assert isinstance(summary, PortfolioSummary)
        assert summary.total_value == 0
        assert summary.stock_value == 0
        assert summary.option_value == 0
        assert summary.cash_value == 0
        assert summary.unknown_value == 0
        assert summary.pending_activity_value == 0
        assert summary.portfolio_beta is None  # No stocks to calculate beta


class TestGetPortfolioExposures:
    """Tests for the get_portfolio_exposures function."""

    def test_get_portfolio_exposures_with_mixed_positions(self):
        """Test that get_portfolio_exposures correctly calculates exposure metrics."""
        # Arrange
        # Create a portfolio with mixed position types
        stock1 = StockPosition(ticker="AAPL", quantity=10, price=150)  # Long
        stock2 = StockPosition(ticker="MSFT", quantity=-5, price=200)  # Short
        option1 = OptionPosition(
            ticker="AAPL",
            quantity=1,
            price=5,
            strike=160,
            expiry=date(2025, 6, 20),
            option_type="CALL",
        )  # Long
        option2 = OptionPosition(
            ticker="MSFT",
            quantity=-2,
            price=3,
            strike=210,
            expiry=date(2025, 6, 20),
            option_type="PUT",
        )  # Short

        portfolio = Portfolio(
            positions=[stock1, stock2, option1, option2],
            pending_activity_value=0,
        )

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock to return beta values
            mock_oracle.get_beta.side_effect = (
                lambda ticker: 1.2 if ticker == "AAPL" else 1.0
            )

            # Act
            exposures = get_portfolio_exposures(portfolio)

            # Assert
            assert exposures["long_stock_exposure"] == 1500  # 10 * 150
            assert exposures["short_stock_exposure"] == 1000  # 5 * 200
            assert exposures["long_option_exposure"] == 500  # 1 * 5 * 100
            assert exposures["short_option_exposure"] == 600  # 2 * 3 * 100
            assert exposures["net_market_exposure"] == 400  # 1500 - 1000 + 500 - 600
            assert (
                exposures["beta_adjusted_exposure"] == 1800 - 1000
            )  # 1500*1.2 - 1000*1.0

    def test_get_portfolio_exposures_with_empty_portfolio(self):
        """Test that get_portfolio_exposures handles empty portfolios correctly."""
        # Arrange
        portfolio = Portfolio(positions=[], pending_activity_value=0)

        # Act
        exposures = get_portfolio_exposures(portfolio)

        # Assert
        assert exposures["long_stock_exposure"] == 0
        assert exposures["short_stock_exposure"] == 0
        assert exposures["long_option_exposure"] == 0
        assert exposures["short_option_exposure"] == 0
        assert exposures["net_market_exposure"] == 0
        assert exposures["beta_adjusted_exposure"] == 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
