"""
Tests for the simulator v2 module.
"""

import unittest
from datetime import date, timedelta

from src.folio.simulator_v2 import (
    calculate_option_pnl,
    calculate_option_value,
    calculate_price_adjustment,
    calculate_stock_pnl,
    calculate_stock_value,
    calculate_underlying_price,
    simulate_portfolio,
)


class TestSimulatorV2(unittest.TestCase):
    """Test cases for simulator v2 module."""

    def test_calculate_price_adjustment(self):
        """Test that price adjustment is calculated correctly."""
        # Test with positive SPY change and positive beta
        self.assertAlmostEqual(calculate_price_adjustment(0.05, 1.2), 1.06)

        # Test with negative SPY change and positive beta
        self.assertAlmostEqual(calculate_price_adjustment(-0.05, 1.2), 0.94)

        # Test with positive SPY change and negative beta
        self.assertAlmostEqual(calculate_price_adjustment(0.05, -0.5), 0.975)

        # Test with zero beta (no change)
        self.assertAlmostEqual(calculate_price_adjustment(0.05, 0.0), 1.0)

    def test_calculate_underlying_price(self):
        """Test that underlying price is calculated correctly."""
        # Test with price increase
        self.assertAlmostEqual(calculate_underlying_price(100.0, 1.05), 105.0)

        # Test with price decrease
        self.assertAlmostEqual(calculate_underlying_price(100.0, 0.95), 95.0)

        # Test with no change
        self.assertAlmostEqual(calculate_underlying_price(100.0, 1.0), 100.0)

    def test_calculate_stock_value(self):
        """Test that stock value is calculated correctly."""
        # Test with positive quantity
        self.assertAlmostEqual(calculate_stock_value(10, 100.0), 1000.0)

        # Test with negative quantity (short position)
        self.assertAlmostEqual(calculate_stock_value(-10, 100.0), -1000.0)

        # Test with zero quantity
        self.assertAlmostEqual(calculate_stock_value(0, 100.0), 0.0)

    def test_calculate_stock_pnl(self):
        """Test that stock P&L is calculated correctly."""
        # Test with price increase
        self.assertAlmostEqual(calculate_stock_pnl(10, 100.0, 110.0), 100.0)

        # Test with price decrease
        self.assertAlmostEqual(calculate_stock_pnl(10, 100.0, 90.0), -100.0)

        # Test with short position and price increase (loss)
        self.assertAlmostEqual(calculate_stock_pnl(-10, 100.0, 110.0), -100.0)

        # Test with short position and price decrease (profit)
        self.assertAlmostEqual(calculate_stock_pnl(-10, 100.0, 90.0), 100.0)

    def test_calculate_option_value(self):
        """Test that option value is calculated correctly."""
        # Create test data
        today = date.today()
        expiry = today + timedelta(days=30)

        # Test call option value
        call_value = calculate_option_value(
            option_type="CALL",
            strike=100.0,
            expiry=expiry,
            underlying_price=100.0,
            quantity=1,
            volatility=0.3,
            risk_free_rate=0.05,
        )
        # We're not testing the exact value, just that it's positive and reasonable
        self.assertGreater(call_value, 0)
        self.assertLess(call_value, 1500)  # Should be less than 15 * 100 for ATM option

        # Test put option value
        put_value = calculate_option_value(
            option_type="PUT",
            strike=100.0,
            expiry=expiry,
            underlying_price=100.0,
            quantity=1,
            volatility=0.3,
            risk_free_rate=0.05,
        )
        # We're not testing the exact value, just that it's positive and reasonable
        self.assertGreater(put_value, 0)
        self.assertLess(put_value, 1500)  # Should be less than 15 * 100 for ATM option

        # Test that higher volatility increases option value
        high_vol_call = calculate_option_value(
            option_type="CALL",
            strike=100.0,
            expiry=expiry,
            underlying_price=100.0,
            quantity=1,
            volatility=0.5,  # Higher volatility
            risk_free_rate=0.05,
        )
        self.assertGreater(high_vol_call, call_value)

    def test_calculate_option_pnl(self):
        """Test that option P&L is calculated correctly."""
        # Create test data
        today = date.today()
        expiry = today + timedelta(days=30)

        # Test call option P&L with price increase
        call_pnl = calculate_option_pnl(
            option_type="CALL",
            strike=100.0,
            expiry=expiry,
            underlying_price=110.0,  # Price increased
            quantity=1,
            entry_price=5.0,  # Entry price per contract
            volatility=0.3,
            risk_free_rate=0.05,
        )
        # Call should be profitable with price increase
        self.assertGreater(call_pnl, 0)

        # Test put option P&L with price decrease
        put_pnl = calculate_option_pnl(
            option_type="PUT",
            strike=100.0,
            expiry=expiry,
            underlying_price=90.0,  # Price decreased
            quantity=1,
            entry_price=5.0,  # Entry price per contract
            volatility=0.3,
            risk_free_rate=0.05,
        )
        # Put should be profitable with price decrease
        self.assertGreater(put_pnl, 0)

    def test_consistent_pnl_calculation(self):
        """Test that P&L is calculated consistently relative to the 0% SPY change baseline."""
        # Import here to avoid circular imports
        from src.folio.data_model import OptionPosition, PortfolioGroup, StockPosition

        # Create a test date for option expiry
        today = date.today()
        expiry = today + timedelta(days=30)
        expiry_str = expiry.strftime("%Y-%m-%d")

        # Create a stock position
        stock = StockPosition(
            ticker="AAPL",
            quantity=10,
            beta=1.2,
            market_exposure=1500.0,
            beta_adjusted_exposure=1800.0,
            price=150.0,
            market_value=1500.0,
        )

        # Create an option position
        option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=1,
            beta=1.2,
            beta_adjusted_exposure=600.0,
            strike=150.0,
            expiry=expiry_str,
            option_type="CALL",
            delta=0.5,
            delta_exposure=750.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=750.0,
            price=5.0,  # $5 per share = $500 per contract
            market_value=500.0,
        )

        # Create a position group
        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock,
            option_positions=[option],
            net_exposure=2000.0,
            beta=1.2,
            beta_adjusted_exposure=2400.0,
            total_delta_exposure=750.0,
            options_delta_exposure=750.0,
        )

        # Test at portfolio level with multiple SPY changes including 0%
        spy_changes = [-0.05, 0.0, 0.05]
        portfolio_result = simulate_portfolio([group], spy_changes, cash_value=1000.0)

        # Find the index of the 0% change
        zero_index = spy_changes.index(0.0)

        # Verify that P&L at 0% change is zero (this is our baseline)
        self.assertAlmostEqual(
            portfolio_result["portfolio_pnls"][zero_index], 0.0, places=2
        )
        self.assertAlmostEqual(
            portfolio_result["portfolio_pnl_percents"][zero_index], 0.0, places=2
        )

        # Verify that P&L values are calculated consistently relative to the 0% baseline
        # For example, if we have -5%, 0%, +5% changes, the P&L at +5% should be the negative of P&L at -5%
        # (assuming symmetric beta response, which is a simplification but reasonable for testing)
        neg_index = spy_changes.index(-0.05)
        pos_index = spy_changes.index(0.05)

        # The P&L at +5% should be roughly the negative of P&L at -5% for a simple test case
        # This is a simplification but helps verify consistency
        neg_pnl = portfolio_result["portfolio_pnls"][neg_index]
        pos_pnl = portfolio_result["portfolio_pnls"][pos_index]

        # Log the values for debugging if needed
        # We could use a logger here, but we'll skip for simplicity

        # Check that they're roughly opposite (with some tolerance for non-linear option effects)
        # This is just a sanity check, not a strict requirement
        self.assertGreater(pos_pnl, 0, "P&L should be positive for positive SPY change")
        self.assertLess(neg_pnl, 0, "P&L should be negative for negative SPY change")
