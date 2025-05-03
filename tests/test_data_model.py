"""Tests for the data model classes.

This module tests the core functionality of the data model classes in src/folio/data_model.py.
"""

from src.folio.data_model import (
    ExposureBreakdown,
    OptionPosition,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
    create_portfolio_group,
)


class TestStockPosition:
    """Tests for the StockPosition class."""

    def test_stock_position_init(self):
        """Test basic initialization of StockPosition."""
        stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
            price=150.0,
        )

        assert stock.ticker == "AAPL"
        assert stock.quantity == 100
        assert stock.beta == 1.2
        assert stock.market_exposure == 15000.0
        assert stock.beta_adjusted_exposure == 18000.0
        assert stock.price == 150.0
        assert stock.position_type == "stock"

    def test_stock_position_to_dict(self):
        """Test conversion of StockPosition to dictionary."""
        stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
            price=150.0,
        )

        stock_dict = stock.to_dict()
        assert stock_dict["ticker"] == "AAPL"
        assert stock_dict["quantity"] == 100
        assert stock_dict["beta"] == 1.2
        assert stock_dict["market_exposure"] == 15000.0
        assert stock_dict["beta_adjusted_exposure"] == 18000.0
        assert stock_dict["price"] == 150.0
        assert stock_dict["position_type"] == "stock"

    def test_stock_position_from_dict(self):
        """Test creation of StockPosition from dictionary."""
        stock_dict = {
            "ticker": "AAPL",
            "quantity": 100,
            "beta": 1.2,
            "market_exposure": 15000.0,
            "beta_adjusted_exposure": 18000.0,
            "price": 150.0,
            "position_type": "stock",
        }

        stock = StockPosition.from_dict(stock_dict)
        assert stock.ticker == "AAPL"
        assert stock.quantity == 100
        assert stock.beta == 1.2
        assert stock.market_exposure == 15000.0
        assert stock.beta_adjusted_exposure == 18000.0
        assert stock.price == 150.0
        assert stock.position_type == "stock"


class TestOptionPosition:
    """Tests for the OptionPosition class."""

    def test_option_position_init(self):
        """Test basic initialization of OptionPosition."""
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            market_exposure=1500.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            price=15.0,
        )

        assert option.ticker == "AAPL"
        assert option.position_type == "option"
        assert option.quantity == 10
        assert option.beta == 1.2
        assert option.beta_adjusted_exposure == 1800.0
        assert option.market_exposure == 1500.0
        assert option.strike == 150.0
        assert option.expiry == "2023-01-01"
        assert option.option_type == "CALL"
        assert option.delta == 0.7
        assert option.delta_exposure == 1050.0
        assert option.notional_value == 15000.0
        assert option.underlying_beta == 1.2
        assert option.price == 15.0

    def test_option_position_to_dict(self):
        """Test conversion of OptionPosition to dictionary."""
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            market_exposure=1500.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            price=15.0,
        )

        option_dict = option.to_dict()
        assert option_dict["ticker"] == "AAPL"
        assert option_dict["position_type"] == "option"
        assert option_dict["quantity"] == 10
        assert option_dict["beta"] == 1.2
        assert option_dict["beta_adjusted_exposure"] == 1800.0
        assert option_dict["market_exposure"] == 1500.0
        assert option_dict["strike"] == 150.0
        assert option_dict["expiry"] == "2023-01-01"
        assert option_dict["option_type"] == "CALL"
        assert option_dict["delta"] == 0.7
        assert option_dict["delta_exposure"] == 1050.0
        assert option_dict["notional_value"] == 15000.0
        assert option_dict["underlying_beta"] == 1.2
        assert option_dict["price"] == 15.0

    def test_option_position_from_dict(self):
        """Test creation of OptionPosition from dictionary."""
        option_dict = {
            "ticker": "AAPL",
            "position_type": "option",
            "quantity": 10,
            "beta": 1.2,
            "beta_adjusted_exposure": 1800.0,
            "market_exposure": 1500.0,
            "strike": 150.0,
            "expiry": "2023-01-01",
            "option_type": "CALL",
            "delta": 0.7,
            "delta_exposure": 1050.0,
            "notional_value": 15000.0,
            "underlying_beta": 1.2,
            "price": 15.0,
        }

        option = OptionPosition.from_dict(option_dict)
        assert option.ticker == "AAPL"
        assert option.position_type == "option"
        assert option.quantity == 10
        assert option.beta == 1.2
        assert option.beta_adjusted_exposure == 1800.0
        assert option.market_exposure == 1500.0
        assert option.strike == 150.0
        assert option.expiry == "2023-01-01"
        assert option.option_type == "CALL"
        assert option.delta == 0.7
        assert option.delta_exposure == 1050.0
        assert option.notional_value == 15000.0
        assert option.underlying_beta == 1.2
        assert option.price == 15.0


class TestExposureBreakdown:
    """Tests for the ExposureBreakdown class."""

    def test_exposure_breakdown_init(self):
        """Test basic initialization of ExposureBreakdown."""
        exposure = ExposureBreakdown(
            stock_exposure=15000.0,
            stock_beta_adjusted=18000.0,
            option_delta_exposure=1050.0,
            option_beta_adjusted=1260.0,
            total_exposure=16050.0,
            total_beta_adjusted=19260.0,
            description="Test Exposure",
            formula="Stock + Options",
            components={"stock": 15000.0, "options": 1050.0},
        )

        assert exposure.stock_exposure == 15000.0
        assert exposure.stock_beta_adjusted == 18000.0
        assert exposure.option_delta_exposure == 1050.0
        assert exposure.option_beta_adjusted == 1260.0
        assert exposure.total_exposure == 16050.0
        assert exposure.total_beta_adjusted == 19260.0
        assert exposure.description == "Test Exposure"
        assert exposure.formula == "Stock + Options"
        assert exposure.components == {"stock": 15000.0, "options": 1050.0}

    def test_exposure_breakdown_to_dict(self):
        """Test conversion of ExposureBreakdown to dictionary."""
        exposure = ExposureBreakdown(
            stock_exposure=15000.0,
            stock_beta_adjusted=18000.0,
            option_delta_exposure=1050.0,
            option_beta_adjusted=1260.0,
            total_exposure=16050.0,
            total_beta_adjusted=19260.0,
            description="Test Exposure",
            formula="Stock + Options",
            components={"stock": 15000.0, "options": 1050.0},
        )

        exposure_dict = exposure.to_dict()
        assert exposure_dict["stock_exposure"] == 15000.0
        assert exposure_dict["stock_beta_adjusted"] == 18000.0
        assert exposure_dict["option_delta_exposure"] == 1050.0
        assert exposure_dict["option_beta_adjusted"] == 1260.0
        assert exposure_dict["total_exposure"] == 16050.0
        assert exposure_dict["total_beta_adjusted"] == 19260.0
        assert exposure_dict["description"] == "Test Exposure"
        assert exposure_dict["formula"] == "Stock + Options"
        assert exposure_dict["components"] == {"stock": 15000.0, "options": 1050.0}

    def test_exposure_breakdown_from_dict(self):
        """Test creation of ExposureBreakdown from dictionary."""
        exposure_dict = {
            "stock_exposure": 15000.0,
            "stock_beta_adjusted": 18000.0,
            "option_delta_exposure": 1050.0,
            "option_beta_adjusted": 1260.0,
            "total_exposure": 16050.0,
            "total_beta_adjusted": 19260.0,
            "description": "Test Exposure",
            "formula": "Stock + Options",
            "components": {"stock": 15000.0, "options": 1050.0},
        }

        exposure = ExposureBreakdown.from_dict(exposure_dict)
        assert exposure.stock_exposure == 15000.0
        assert exposure.stock_beta_adjusted == 18000.0
        assert exposure.option_delta_exposure == 1050.0
        assert exposure.option_beta_adjusted == 1260.0
        assert exposure.total_exposure == 16050.0
        assert exposure.total_beta_adjusted == 19260.0
        assert exposure.description == "Test Exposure"
        assert exposure.formula == "Stock + Options"
        assert exposure.components == {"stock": 15000.0, "options": 1050.0}


class TestPortfolioGroup:
    """Tests for the PortfolioGroup class."""

    def test_portfolio_group_init(self):
        """Test basic initialization of PortfolioGroup."""
        stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
        )

        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            market_exposure=1500.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
        )

        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock,
            option_positions=[option],
            net_exposure=16050.0,
            beta=1.2,
            beta_adjusted_exposure=19260.0,
            total_delta_exposure=1050.0,
            options_delta_exposure=1050.0,
        )

        assert group.ticker == "AAPL"
        assert group.stock_position == stock
        assert group.option_positions == [option]
        assert group.net_exposure == 16050.0
        assert group.beta == 1.2
        assert group.beta_adjusted_exposure == 19260.0
        assert group.total_delta_exposure == 1050.0
        assert group.options_delta_exposure == 1050.0
        assert group.call_count == 1
        assert group.put_count == 0

    def test_portfolio_group_to_dict(self):
        """Test conversion of PortfolioGroup to dictionary."""
        stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
        )

        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            market_exposure=1500.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
        )

        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock,
            option_positions=[option],
            net_exposure=16050.0,
            beta=1.2,
            beta_adjusted_exposure=19260.0,
            total_delta_exposure=1050.0,
            options_delta_exposure=1050.0,
        )

        group_dict = group.to_dict()
        assert group_dict["ticker"] == "AAPL"
        assert group_dict["stock_position"] == stock.to_dict()
        assert group_dict["option_positions"] == [option.to_dict()]
        assert group_dict["net_exposure"] == 16050.0
        assert group_dict["beta"] == 1.2
        assert group_dict["beta_adjusted_exposure"] == 19260.0
        assert group_dict["total_delta_exposure"] == 1050.0
        assert group_dict["options_delta_exposure"] == 1050.0
        assert group_dict["call_count"] == 1
        assert group_dict["put_count"] == 0

    def test_portfolio_group_from_dict(self):
        """Test creation of PortfolioGroup from dictionary."""
        stock_dict = {
            "ticker": "AAPL",
            "quantity": 100,
            "beta": 1.2,
            "market_exposure": 15000.0,
            "beta_adjusted_exposure": 18000.0,
            "position_type": "stock",
        }

        option_dict = {
            "ticker": "AAPL",
            "position_type": "option",
            "quantity": 10,
            "beta": 1.2,
            "beta_adjusted_exposure": 1800.0,
            "market_exposure": 1500.0,
            "strike": 150.0,
            "expiry": "2023-01-01",
            "option_type": "CALL",
            "delta": 0.7,
            "delta_exposure": 1050.0,
            "notional_value": 15000.0,
            "underlying_beta": 1.2,
        }

        group_dict = {
            "ticker": "AAPL",
            "stock_position": stock_dict,
            "option_positions": [option_dict],
            "net_exposure": 16050.0,
            "beta": 1.2,
            "beta_adjusted_exposure": 19260.0,
            "total_delta_exposure": 1050.0,
            "options_delta_exposure": 1050.0,
            "call_count": 1,
            "put_count": 0,
        }

        group = PortfolioGroup.from_dict(group_dict)
        assert group.ticker == "AAPL"
        assert group.stock_position.ticker == "AAPL"
        assert group.stock_position.quantity == 100
        assert len(group.option_positions) == 1
        assert group.option_positions[0].ticker == "AAPL"
        assert group.option_positions[0].option_type == "CALL"
        assert group.net_exposure == 16050.0
        assert group.beta == 1.2
        assert group.beta_adjusted_exposure == 19260.0
        assert group.total_delta_exposure == 1050.0
        assert group.options_delta_exposure == 1050.0
        assert group.call_count == 1
        assert group.put_count == 0

    def test_create_portfolio_group(self):
        """Test the create_portfolio_group function."""
        stock_data = {
            "ticker": "AAPL",
            "quantity": 100,
            "beta": 1.2,
            "market_exposure": 15000.0,
            "beta_adjusted_exposure": 18000.0,
            "description": "APPLE INC",
            "price": 150.0,
        }

        option_data = [
            {
                "ticker": "AAPL",
                "option_symbol": "-AAPL250417C220",
                "description": "AAPL APR 17 2025 $220 CALL",
                "quantity": 10,
                "beta": 1.2,
                "beta_adjusted_exposure": 1800.0,
                "market_exposure": 1500.0,
                "strike": 220.0,
                "expiry": "2025-04-17",
                "option_type": "CALL",
                "delta": 0.7,
                "delta_exposure": 1050.0,
                "notional_value": 15000.0,
                "price": 15.0,
            }
        ]

        group = create_portfolio_group(stock_data, option_data)
        assert group.ticker == "AAPL"
        assert group.stock_position.ticker == "AAPL"
        assert group.stock_position.quantity == 100
        assert group.stock_position.price == 150.0
        assert len(group.option_positions) == 1
        assert group.option_positions[0].ticker == "AAPL"
        assert group.option_positions[0].option_type == "CALL"
        assert group.option_positions[0].strike == 220.0
        assert group.option_positions[0].expiry == "2025-04-17"
        assert group.option_positions[0].price == 15.0
        assert group.net_exposure == 16050.0  # 15000 + 1050
        assert group.beta == 1.2
        assert group.beta_adjusted_exposure == 19800.0  # 18000 + 1800
        assert group.total_delta_exposure == 1050.0
        assert group.options_delta_exposure == 1050.0
        assert group.call_count == 1
        assert group.put_count == 0


class TestPortfolioSummary:
    """Tests for the PortfolioSummary class."""

    def test_portfolio_summary_init(self):
        """Test basic initialization of PortfolioSummary."""
        long_exposure = ExposureBreakdown(
            stock_exposure=15000.0,
            stock_beta_adjusted=18000.0,
            option_delta_exposure=1050.0,
            option_beta_adjusted=1260.0,
            total_exposure=16050.0,
            total_beta_adjusted=19260.0,
            description="Long Exposure",
            formula="Long Stock + Long Call Delta + Short Put Delta",
            components={"Long Stock": 15000.0, "Long Options": 1050.0},
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=5000.0,
            stock_beta_adjusted=6000.0,
            option_delta_exposure=500.0,
            option_beta_adjusted=600.0,
            total_exposure=5500.0,
            total_beta_adjusted=6600.0,
            description="Short Exposure",
            formula="Short Stock + Short Call Delta + Long Put Delta",
            components={"Short Stock": 5000.0, "Short Options": 500.0},
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=550.0,
            option_beta_adjusted=660.0,
            total_exposure=550.0,
            total_beta_adjusted=660.0,
            description="Options Exposure",
            formula="Long Options Delta - Short Options Delta",
            components={"Long Options": 1050.0, "Short Options": 500.0, "Net": 550.0},
        )

        cash_position = StockPosition(
            ticker="SPAXX",
            quantity=1,
            beta=0.0,
            market_exposure=5000.0,
            beta_adjusted_exposure=0.0,
            price=5000.0,
        )

        summary = PortfolioSummary(
            net_market_exposure=10550.0,  # 16050 - 5500
            portfolio_beta=1.2,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=25.5,  # (5500 / (16050 + 5500)) * 100
            cash_like_positions=[cash_position],
            cash_like_value=5000.0,
            cash_like_count=1,
            cash_percentage=32.1,  # (5000 / (10550 + 5000)) * 100
            portfolio_estimate_value=15550.0,  # 10550 + 5000
            price_updated_at="2025-05-03T09:00:00Z",
        )

        assert summary.net_market_exposure == 10550.0
        assert summary.portfolio_beta == 1.2
        assert summary.long_exposure == long_exposure
        assert summary.short_exposure == short_exposure
        assert summary.options_exposure == options_exposure
        assert summary.short_percentage == 25.5
        assert summary.cash_like_positions == [cash_position]
        assert summary.cash_like_value == 5000.0
        assert summary.cash_like_count == 1
        assert summary.cash_percentage == 32.1
        assert summary.portfolio_estimate_value == 15550.0
        assert summary.help_text is not None  # Help text should be initialized

    def test_portfolio_summary_to_dict(self):
        """Test conversion of PortfolioSummary to dictionary."""
        long_exposure = ExposureBreakdown(
            stock_exposure=15000.0,
            stock_beta_adjusted=18000.0,
            option_delta_exposure=1050.0,
            option_beta_adjusted=1260.0,
            total_exposure=16050.0,
            total_beta_adjusted=19260.0,
            description="Long Exposure",
            formula="Long Stock + Long Call Delta + Short Put Delta",
            components={"Long Stock": 15000.0, "Long Options": 1050.0},
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=5000.0,
            stock_beta_adjusted=6000.0,
            option_delta_exposure=500.0,
            option_beta_adjusted=600.0,
            total_exposure=5500.0,
            total_beta_adjusted=6600.0,
            description="Short Exposure",
            formula="Short Stock + Short Call Delta + Long Put Delta",
            components={"Short Stock": 5000.0, "Short Options": 500.0},
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=550.0,
            option_beta_adjusted=660.0,
            total_exposure=550.0,
            total_beta_adjusted=660.0,
            description="Options Exposure",
            formula="Long Options Delta - Short Options Delta",
            components={"Long Options": 1050.0, "Short Options": 500.0, "Net": 550.0},
        )

        cash_position = StockPosition(
            ticker="SPAXX",
            quantity=1,
            beta=0.0,
            market_exposure=5000.0,
            beta_adjusted_exposure=0.0,
        )

        # Test timestamp
        test_timestamp = "2025-04-08T12:34:56.789012"

        summary = PortfolioSummary(
            net_market_exposure=10550.0,
            portfolio_beta=1.2,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=25.5,
            cash_like_positions=[cash_position],
            cash_like_value=5000.0,
            cash_like_count=1,
            cash_percentage=32.1,
            portfolio_estimate_value=15550.0,
            price_updated_at=test_timestamp,
        )

        summary_dict = summary.to_dict()
        assert summary_dict["net_market_exposure"] == 10550.0
        assert summary_dict["portfolio_beta"] == 1.2
        assert summary_dict["long_exposure"] == long_exposure.to_dict()
        assert summary_dict["short_exposure"] == short_exposure.to_dict()
        assert summary_dict["options_exposure"] == options_exposure.to_dict()
        assert summary_dict["short_percentage"] == 25.5
        assert summary_dict["cash_like_positions"] == [cash_position.to_dict()]
        assert summary_dict["cash_like_value"] == 5000.0
        assert summary_dict["cash_like_count"] == 1
        assert summary_dict["cash_percentage"] == 32.1
        assert summary_dict["portfolio_estimate_value"] == 15550.0
        assert "help_text" in summary_dict
        assert summary_dict["price_updated_at"] == test_timestamp

    def test_portfolio_summary_from_dict(self):
        """Test creation of PortfolioSummary from dictionary."""
        long_exposure_dict = {
            "stock_exposure": 15000.0,
            "stock_beta_adjusted": 18000.0,
            "option_delta_exposure": 1050.0,
            "option_beta_adjusted": 1260.0,
            "total_exposure": 16050.0,
            "total_beta_adjusted": 19260.0,
            "description": "Long Exposure",
            "formula": "Long Stock + Long Call Delta + Short Put Delta",
            "components": {"Long Stock": 15000.0, "Long Options": 1050.0},
        }

        short_exposure_dict = {
            "stock_exposure": 5000.0,
            "stock_beta_adjusted": 6000.0,
            "option_delta_exposure": 500.0,
            "option_beta_adjusted": 600.0,
            "total_exposure": 5500.0,
            "total_beta_adjusted": 6600.0,
            "description": "Short Exposure",
            "formula": "Short Stock + Short Call Delta + Long Put Delta",
            "components": {"Short Stock": 5000.0, "Short Options": 500.0},
        }

        options_exposure_dict = {
            "stock_exposure": 0.0,
            "stock_beta_adjusted": 0.0,
            "option_delta_exposure": 550.0,
            "option_beta_adjusted": 660.0,
            "total_exposure": 550.0,
            "total_beta_adjusted": 660.0,
            "description": "Options Exposure",
            "formula": "Long Options Delta - Short Options Delta",
            "components": {
                "Long Options": 1050.0,
                "Short Options": 500.0,
                "Net": 550.0,
            },
        }

        cash_position_dict = {
            "ticker": "SPAXX",
            "quantity": 1,
            "beta": 0.0,
            "market_exposure": 5000.0,
            "beta_adjusted_exposure": 0.0,
            "position_type": "stock",
        }

        summary_dict = {
            "net_market_exposure": 10550.0,
            "portfolio_beta": 1.2,
            "long_exposure": long_exposure_dict,
            "short_exposure": short_exposure_dict,
            "options_exposure": options_exposure_dict,
            "short_percentage": 25.5,
            "cash_like_positions": [cash_position_dict],
            "cash_like_value": 5000.0,
            "cash_like_count": 1,
            "cash_percentage": 32.1,
            "portfolio_estimate_value": 15550.0,
            "help_text": {"key": "value"},  # Simplified help text for testing
            "price_updated_at": "2025-04-08T12:34:56.789012",
        }

        summary = PortfolioSummary.from_dict(summary_dict)
        assert summary.net_market_exposure == 10550.0
        assert summary.portfolio_beta == 1.2
        assert summary.long_exposure.total_exposure == 16050.0
        assert summary.short_exposure.total_exposure == 5500.0
        assert summary.options_exposure.total_exposure == 550.0
        assert summary.short_percentage == 25.5
        assert len(summary.cash_like_positions) == 1
        assert summary.cash_like_positions[0].ticker == "SPAXX"
        assert summary.cash_like_value == 5000.0
        assert summary.cash_like_count == 1
        assert summary.cash_percentage == 32.1
        assert summary.portfolio_estimate_value == 15550.0
        assert summary.price_updated_at == "2025-04-08T12:34:56.789012"
