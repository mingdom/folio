"""
Basic integration tests for simulator_v2 module.
"""

import unittest
from datetime import date, timedelta

from src.folio.data_model import OptionPosition, PortfolioGroup, StockPosition
from src.folio.simulator_v2 import (
    simulate_option_position,
    simulate_portfolio,
    simulate_position_group,
    simulate_stock_position,
)


class TestSimulatorV2Integration(unittest.TestCase):
    """Basic integration tests for simulator_v2 module."""

    def test_simulate_stock_position(self):
        """Test that stock position simulation works correctly."""
        # Create a test stock position
        stock = StockPosition(
            ticker="AAPL",
            quantity=10,
            beta=1.2,
            market_exposure=1500.0,
            beta_adjusted_exposure=1800.0,
            price=150.0,
            market_value=1500.0,
        )

        # Simulate with a price increase
        result = simulate_stock_position(stock, 160.0)

        # Check the results
        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["position_type"], "stock")
        self.assertEqual(result["original_price"], 150.0)
        self.assertEqual(result["new_price"], 160.0)
        self.assertEqual(result["original_value"], 1500.0)
        self.assertEqual(result["new_value"], 1600.0)
        self.assertEqual(result["pnl"], 100.0)
        self.assertAlmostEqual(result["pnl_percent"], 6.67, places=2)

    def test_simulate_option_position(self):
        """Test that option position simulation works correctly."""
        # Create a test option position
        today = date.today()
        expiry = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=1,
            beta=1.2,
            beta_adjusted_exposure=300.0,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
            delta=0.5,
            delta_exposure=750.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=750.0,
            price=5.0,
            market_value=500.0,
        )

        # Simulate with a price increase
        result = simulate_option_position(option, 160.0, current_underlying_price=150.0)

        # Check the results
        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["position_type"], "option")
        self.assertEqual(result["option_type"], "CALL")
        self.assertEqual(result["strike"], 150.0)
        self.assertEqual(result["expiry"], expiry)
        self.assertEqual(result["original_underlying_price"], 150.0)
        self.assertEqual(result["new_underlying_price"], 160.0)
        self.assertEqual(result["original_value"], 500.0)
        # We don't check the exact new value or PnL since it depends on Black-Scholes
        self.assertGreater(result["new_value"], result["original_value"])
        self.assertGreater(result["pnl"], 0)

    def test_simulate_position_group(self):
        """Test that position group simulation works correctly."""
        # Create a test stock position
        stock = StockPosition(
            ticker="AAPL",
            quantity=10,
            beta=1.2,
            market_exposure=1500.0,
            beta_adjusted_exposure=1800.0,
            price=150.0,
            market_value=1500.0,
        )

        # Create a test option position
        today = date.today()
        expiry = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=1,
            beta=1.2,
            beta_adjusted_exposure=300.0,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
            delta=0.5,
            delta_exposure=750.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=750.0,
            price=5.0,
            market_value=500.0,
        )

        # Create a test position group
        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock,
            option_positions=[option],
            net_exposure=2250.0,
            beta=1.2,
            beta_adjusted_exposure=2100.0,
            total_delta_exposure=750.0,
            options_delta_exposure=750.0,
        )

        # Simulate with a SPY increase
        result = simulate_position_group(group, 0.05)

        # Check the results
        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["beta"], 1.2)
        self.assertEqual(result["current_price"], 150.0)
        # With beta 1.2 and SPY change 0.05, price should increase by 6%
        self.assertAlmostEqual(result["new_price"], 159.0, places=2)
        self.assertEqual(len(result["positions"]), 2)

    def test_simulate_portfolio(self):
        """Test that portfolio simulation works correctly."""
        # Create a test stock position
        stock = StockPosition(
            ticker="AAPL",
            quantity=10,
            beta=1.2,
            market_exposure=1500.0,
            beta_adjusted_exposure=1800.0,
            price=150.0,
            market_value=1500.0,
        )

        # Create a test option position
        today = date.today()
        expiry = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=1,
            beta=1.2,
            beta_adjusted_exposure=300.0,
            strike=150.0,
            expiry=expiry,
            option_type="CALL",
            delta=0.5,
            delta_exposure=750.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=750.0,
            price=5.0,
            market_value=500.0,
        )

        # Create a test position group
        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock,
            option_positions=[option],
            net_exposure=2250.0,
            beta=1.2,
            beta_adjusted_exposure=2100.0,
            total_delta_exposure=750.0,
            options_delta_exposure=750.0,
        )

        # Simulate with multiple SPY changes
        spy_changes = [-0.05, 0.0, 0.05]
        result = simulate_portfolio([group], spy_changes, cash_value=1000.0)

        # Check the results
        self.assertEqual(result["spy_changes"], spy_changes)
        self.assertEqual(len(result["portfolio_values"]), 3)
        self.assertEqual(len(result["portfolio_pnls"]), 3)
        self.assertEqual(len(result["portfolio_pnl_percents"]), 3)
        # Note: current_portfolio_value is now calculated differently
        # It's the baseline value at 0% SPY change, which may include recalculated option values
        self.assertGreater(result["current_portfolio_value"], 0)
        self.assertEqual(len(result["position_results"]["AAPL"]), 3)

    def test_simulate_empty_portfolio(self):
        """Test that empty portfolio simulation works correctly."""
        # Simulate with multiple SPY changes
        spy_changes = [-0.05, 0.0, 0.05]
        result = simulate_portfolio([], spy_changes, cash_value=1000.0)

        # Check the results
        self.assertEqual(result["spy_changes"], spy_changes)
        self.assertEqual(result["portfolio_values"], [1000.0, 1000.0, 1000.0])
        self.assertEqual(result["portfolio_pnls"], [0.0, 0.0, 0.0])
        self.assertEqual(result["portfolio_pnl_percents"], [0.0, 0.0, 0.0])
        self.assertEqual(result["position_results"], {})
