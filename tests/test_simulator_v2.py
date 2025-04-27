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
