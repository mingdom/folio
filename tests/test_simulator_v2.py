"""
Tests for the simulator v2 module.
"""

import unittest

from src.folio.simulator_v2 import (
    calculate_price_adjustment,
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
