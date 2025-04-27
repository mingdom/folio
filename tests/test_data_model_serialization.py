"""Tests for data model serialization and deserialization.

This module tests the serialization and deserialization of data model classes,
ensuring that objects can be converted to dictionaries and back without losing
information.
"""

import unittest

from src.folio.data_model import (
    ExposureBreakdown,
    OptionPosition,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
)


class TestDataModelSerialization(unittest.TestCase):
    """Test serialization and deserialization of data model classes."""

    def test_stock_position_serialization(self):
        """Test that StockPosition objects can be serialized and deserialized."""
        # Create a StockPosition
        stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
            price=150.0,
            cost_basis=140.0,
        )

        # Serialize to dict
        stock_dict = stock.to_dict()

        # Deserialize from dict
        stock2 = StockPosition.from_dict(stock_dict)

        # Check that the deserialized object has the same attributes
        self.assertEqual(stock.ticker, stock2.ticker)
        self.assertEqual(stock.quantity, stock2.quantity)
        self.assertEqual(stock.beta, stock2.beta)
        self.assertEqual(stock.market_exposure, stock2.market_exposure)
        self.assertEqual(stock.beta_adjusted_exposure, stock2.beta_adjusted_exposure)
        self.assertEqual(stock.price, stock2.price)
        self.assertEqual(stock.cost_basis, stock2.cost_basis)
        self.assertEqual(stock.market_value, stock2.market_value)

    def test_stock_position_serialization_without_market_value(self):
        """Test that StockPosition objects can be deserialized without market_value."""
        # Create a dict without market_value
        stock_dict = {
            "ticker": "AAPL",
            "quantity": 100,
            "beta": 1.2,
            "market_exposure": 15000.0,
            "beta_adjusted_exposure": 18000.0,
            "price": 150.0,
            "position_type": "stock",
            "cost_basis": 140.0,
        }

        # Deserialize from dict
        stock = StockPosition.from_dict(stock_dict)

        # Check that market_value was calculated correctly
        self.assertEqual(
            stock.market_value, stock_dict["price"] * stock_dict["quantity"]
        )

    def test_option_position_serialization(self):
        """Test that OptionPosition objects can be serialized and deserialized."""
        # Create an OptionPosition
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=18000.0,
            strike=150.0,
            expiry="2023-12-15",
            option_type="CALL",
            delta=0.7,
            delta_exposure=10500.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=10500.0,
            price=15.0,
            cost_basis=14.0,
        )

        # Serialize to dict
        option_dict = option.to_dict()

        # Deserialize from dict
        option2 = OptionPosition.from_dict(option_dict)

        # Check that the deserialized object has the same attributes
        self.assertEqual(option.ticker, option2.ticker)
        self.assertEqual(option.position_type, option2.position_type)
        self.assertEqual(option.quantity, option2.quantity)
        self.assertEqual(option.beta, option2.beta)
        self.assertEqual(option.beta_adjusted_exposure, option2.beta_adjusted_exposure)
        self.assertEqual(option.strike, option2.strike)
        self.assertEqual(option.expiry, option2.expiry)
        self.assertEqual(option.option_type, option2.option_type)
        self.assertEqual(option.delta, option2.delta)
        self.assertEqual(option.delta_exposure, option2.delta_exposure)
        self.assertEqual(option.notional_value, option2.notional_value)
        self.assertEqual(option.underlying_beta, option2.underlying_beta)
        self.assertEqual(option.market_exposure, option2.market_exposure)
        self.assertEqual(option.price, option2.price)
        self.assertEqual(option.cost_basis, option2.cost_basis)
        self.assertEqual(option.market_value, option2.market_value)

    def test_option_position_serialization_without_market_value(self):
        """Test that OptionPosition objects can be deserialized without market_value."""
        # Create a dict without market_value
        option_dict = {
            "ticker": "AAPL",
            "position_type": "option",
            "quantity": 10,
            "beta": 1.2,
            "beta_adjusted_exposure": 18000.0,
            "strike": 150.0,
            "expiry": "2023-12-15",
            "option_type": "CALL",
            "delta": 0.7,
            "delta_exposure": 10500.0,
            "notional_value": 15000.0,
            "underlying_beta": 1.2,
            "market_exposure": 10500.0,
            "price": 15.0,
            "cost_basis": 14.0,
        }

        # Deserialize from dict
        option = OptionPosition.from_dict(option_dict)

        # Check that market_value was calculated correctly with 100x multiplier
        self.assertEqual(
            option.market_value, option_dict["price"] * option_dict["quantity"] * 100
        )

    def test_portfolio_group_serialization(self):
        """Test that PortfolioGroup objects can be serialized and deserialized."""
        # Create a StockPosition
        stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
            price=150.0,
            cost_basis=140.0,
        )

        # Create an OptionPosition
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=18000.0,
            strike=150.0,
            expiry="2023-12-15",
            option_type="CALL",
            delta=0.7,
            delta_exposure=10500.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=10500.0,
            price=15.0,
            cost_basis=14.0,
        )

        # Create a PortfolioGroup
        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock,
            option_positions=[option],
            net_exposure=25500.0,
            beta=1.2,
            beta_adjusted_exposure=36000.0,
            total_delta_exposure=10500.0,
            options_delta_exposure=10500.0,
        )

        # Serialize to dict
        group_dict = group.to_dict()

        # Deserialize from dict
        group2 = PortfolioGroup.from_dict(group_dict)

        # Check that the deserialized object has the same attributes
        self.assertEqual(group.ticker, group2.ticker)
        self.assertEqual(group.net_exposure, group2.net_exposure)
        self.assertEqual(group.beta, group2.beta)
        self.assertEqual(group.beta_adjusted_exposure, group2.beta_adjusted_exposure)
        self.assertEqual(group.total_delta_exposure, group2.total_delta_exposure)
        self.assertEqual(group.options_delta_exposure, group2.options_delta_exposure)

        # Check that the stock position was deserialized correctly
        self.assertEqual(group.stock_position.ticker, group2.stock_position.ticker)
        self.assertEqual(group.stock_position.quantity, group2.stock_position.quantity)
        self.assertEqual(group.stock_position.beta, group2.stock_position.beta)
        self.assertEqual(
            group.stock_position.market_exposure, group2.stock_position.market_exposure
        )
        self.assertEqual(
            group.stock_position.beta_adjusted_exposure,
            group2.stock_position.beta_adjusted_exposure,
        )
        self.assertEqual(group.stock_position.price, group2.stock_position.price)
        self.assertEqual(
            group.stock_position.cost_basis, group2.stock_position.cost_basis
        )
        self.assertEqual(
            group.stock_position.market_value, group2.stock_position.market_value
        )

        # Check that the option position was deserialized correctly
        self.assertEqual(
            group.option_positions[0].ticker, group2.option_positions[0].ticker
        )
        self.assertEqual(
            group.option_positions[0].position_type,
            group2.option_positions[0].position_type,
        )
        self.assertEqual(
            group.option_positions[0].quantity, group2.option_positions[0].quantity
        )
        self.assertEqual(
            group.option_positions[0].beta, group2.option_positions[0].beta
        )
        self.assertEqual(
            group.option_positions[0].beta_adjusted_exposure,
            group2.option_positions[0].beta_adjusted_exposure,
        )
        self.assertEqual(
            group.option_positions[0].strike, group2.option_positions[0].strike
        )
        self.assertEqual(
            group.option_positions[0].expiry, group2.option_positions[0].expiry
        )
        self.assertEqual(
            group.option_positions[0].option_type,
            group2.option_positions[0].option_type,
        )
        self.assertEqual(
            group.option_positions[0].delta, group2.option_positions[0].delta
        )
        self.assertEqual(
            group.option_positions[0].delta_exposure,
            group2.option_positions[0].delta_exposure,
        )
        self.assertEqual(
            group.option_positions[0].notional_value,
            group2.option_positions[0].notional_value,
        )
        self.assertEqual(
            group.option_positions[0].underlying_beta,
            group2.option_positions[0].underlying_beta,
        )
        self.assertEqual(
            group.option_positions[0].market_exposure,
            group2.option_positions[0].market_exposure,
        )
        self.assertEqual(
            group.option_positions[0].price, group2.option_positions[0].price
        )
        self.assertEqual(
            group.option_positions[0].cost_basis, group2.option_positions[0].cost_basis
        )
        self.assertEqual(
            group.option_positions[0].market_value,
            group2.option_positions[0].market_value,
        )

    def test_portfolio_summary_serialization(self):
        """Test that PortfolioSummary objects can be serialized and deserialized."""
        # Create ExposureBreakdown objects
        long_exposure = ExposureBreakdown(
            stock_exposure=15000.0,
            stock_beta_adjusted=18000.0,
            option_delta_exposure=10500.0,
            option_beta_adjusted=12600.0,
            total_exposure=25500.0,
            total_beta_adjusted=30600.0,
            description="Long exposure",
            formula="Long stocks + Long calls + Short puts",
            components={
                "Long stocks": 15000.0,
                "Long calls": 10500.0,
                "Short puts": 0.0,
            },
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=-5000.0,
            stock_beta_adjusted=-6000.0,
            option_delta_exposure=-3500.0,
            option_beta_adjusted=-4200.0,
            total_exposure=-8500.0,
            total_beta_adjusted=-10200.0,
            description="Short exposure",
            formula="Short stocks + Short calls + Long puts",
            components={
                "Short stocks": -5000.0,
                "Short calls": -3500.0,
                "Long puts": 0.0,
            },
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=7000.0,
            option_beta_adjusted=8400.0,
            total_exposure=7000.0,
            total_beta_adjusted=8400.0,
            description="Options exposure",
            formula="Long calls + Short calls + Long puts + Short puts",
            components={
                "Long calls": 10500.0,
                "Short calls": -3500.0,
                "Long puts": 0.0,
                "Short puts": 0.0,
            },
        )

        # Create a StockPosition for cash
        cash = StockPosition(
            ticker="CASH",
            quantity=1,
            beta=0.0,
            market_exposure=0.0,
            beta_adjusted_exposure=0.0,
            price=10000.0,
            cost_basis=10000.0,
        )

        # Create a PortfolioSummary
        summary = PortfolioSummary(
            net_market_exposure=17000.0,
            portfolio_beta=1.2,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=33.33,
            cash_like_positions=[cash],
            cash_like_value=10000.0,
            cash_like_count=1,
            cash_percentage=20.0,
            stock_value=20000.0,
            option_value=15000.0,
            pending_activity_value=5000.0,
            portfolio_estimate_value=50000.0,
            price_updated_at="2023-12-15T12:00:00Z",
        )

        # Serialize to dict
        summary_dict = summary.to_dict()

        # Deserialize from dict
        summary2 = PortfolioSummary.from_dict(summary_dict)

        # Check that the deserialized object has the same attributes
        self.assertEqual(summary.net_market_exposure, summary2.net_market_exposure)
        self.assertEqual(summary.portfolio_beta, summary2.portfolio_beta)
        self.assertEqual(summary.short_percentage, summary2.short_percentage)
        self.assertEqual(summary.cash_like_value, summary2.cash_like_value)
        self.assertEqual(summary.cash_like_count, summary2.cash_like_count)
        self.assertEqual(summary.cash_percentage, summary2.cash_percentage)
        self.assertEqual(summary.stock_value, summary2.stock_value)
        self.assertEqual(summary.option_value, summary2.option_value)
        self.assertEqual(
            summary.pending_activity_value, summary2.pending_activity_value
        )
        self.assertEqual(
            summary.portfolio_estimate_value, summary2.portfolio_estimate_value
        )
        self.assertEqual(summary.price_updated_at, summary2.price_updated_at)

        # Check that the exposure breakdowns were deserialized correctly
        self.assertEqual(
            summary.long_exposure.stock_exposure, summary2.long_exposure.stock_exposure
        )
        self.assertEqual(
            summary.long_exposure.stock_beta_adjusted,
            summary2.long_exposure.stock_beta_adjusted,
        )
        self.assertEqual(
            summary.long_exposure.option_delta_exposure,
            summary2.long_exposure.option_delta_exposure,
        )
        self.assertEqual(
            summary.long_exposure.option_beta_adjusted,
            summary2.long_exposure.option_beta_adjusted,
        )
        self.assertEqual(
            summary.long_exposure.total_exposure, summary2.long_exposure.total_exposure
        )
        self.assertEqual(
            summary.long_exposure.total_beta_adjusted,
            summary2.long_exposure.total_beta_adjusted,
        )

    def test_portfolio_summary_serialization_without_pending_activity(self):
        """Test that PortfolioSummary objects can be deserialized without pending_activity_value."""
        # Create ExposureBreakdown objects
        long_exposure = ExposureBreakdown(
            stock_exposure=15000.0,
            stock_beta_adjusted=18000.0,
            option_delta_exposure=10500.0,
            option_beta_adjusted=12600.0,
            total_exposure=25500.0,
            total_beta_adjusted=30600.0,
            description="Long exposure",
            formula="Long stocks + Long calls + Short puts",
            components={
                "Long stocks": 15000.0,
                "Long calls": 10500.0,
                "Short puts": 0.0,
            },
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=-5000.0,
            stock_beta_adjusted=-6000.0,
            option_delta_exposure=-3500.0,
            option_beta_adjusted=-4200.0,
            total_exposure=-8500.0,
            total_beta_adjusted=-10200.0,
            description="Short exposure",
            formula="Short stocks + Short calls + Long puts",
            components={
                "Short stocks": -5000.0,
                "Short calls": -3500.0,
                "Long puts": 0.0,
            },
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=7000.0,
            option_beta_adjusted=8400.0,
            total_exposure=7000.0,
            total_beta_adjusted=8400.0,
            description="Options exposure",
            formula="Long calls + Short calls + Long puts + Short puts",
            components={
                "Long calls": 10500.0,
                "Short calls": -3500.0,
                "Long puts": 0.0,
                "Short puts": 0.0,
            },
        )

        # Create a dict without pending_activity_value
        summary_dict = {
            "net_market_exposure": 17000.0,
            "portfolio_beta": 1.2,
            "long_exposure": long_exposure.to_dict(),
            "short_exposure": short_exposure.to_dict(),
            "options_exposure": options_exposure.to_dict(),
            "short_percentage": 33.33,
            "cash_like_positions": [],
            "cash_like_value": 10000.0,
            "cash_like_count": 1,
            "cash_percentage": 20.0,
            "stock_value": 20000.0,
            "option_value": 15000.0,
            "portfolio_estimate_value": 50000.0,
            "help_text": {},
            "price_updated_at": "2023-12-15T12:00:00Z",
        }

        # Deserialize from dict
        summary = PortfolioSummary.from_dict(summary_dict)

        # Check that pending_activity_value was set to default value
        self.assertEqual(summary.pending_activity_value, 0.0)


if __name__ == "__main__":
    unittest.main()
