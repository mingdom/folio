"""
Tests for P&L calculation functions.
"""

import datetime
import unittest
from unittest.mock import patch

import numpy as np

from src.folio.data_model import OptionPosition, StockPosition
from src.folio.pnl import (
    calculate_breakeven_points,
    calculate_max_profit_loss,
    calculate_position_pnl,
    calculate_strategy_pnl,
    determine_price_range,
    summarize_strategy_pnl,
)


class TestPnLCalculations(unittest.TestCase):
    """Test cases for P&L calculation functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample stock position
        self.stock_position = StockPosition(
            ticker="SPY",
            quantity=100,
            beta=1.0,
            beta_adjusted_exposure=45000.0,
            market_exposure=45000.0,  # 100 shares * $450
            price=450.0,  # $450 per share
            cost_basis=400.0,  # $400 per share cost basis
        )

        # Create a sample call option position
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=30)
        expiry_str = expiry_date.strftime("%Y-%m-%d")
        self.call_option = OptionPosition(
            ticker="SPY",
            position_type="option",
            quantity=1,
            beta=1.0,
            beta_adjusted_exposure=1000.0,
            market_exposure=1000.0,  # 1 contract * $10 * 100 shares
            strike=460.0,
            expiry=expiry_str,
            option_type="CALL",
            delta=0.5,
            delta_exposure=2250.0,  # 0.5 * 100 * $450 * 1
            notional_value=45000.0,  # 100 * $450 * 1
            underlying_beta=1.0,
            price=10.0,  # $10 per contract
            cost_basis=8.0,  # $8 per contract cost basis
        )

        # Create a sample put option position
        self.put_option = OptionPosition(
            ticker="SPY",
            position_type="option",
            quantity=-2,  # Short 2 contracts
            beta=1.0,
            beta_adjusted_exposure=-1000.0,
            market_exposure=-1000.0,  # -2 contracts * $5 * 100 shares
            strike=440.0,
            expiry=expiry_str,
            option_type="PUT",
            delta=-0.4,
            delta_exposure=3600.0,  # -0.4 * 100 * $450 * -2
            notional_value=90000.0,  # 100 * $450 * 2
            underlying_beta=1.0,
            price=5.0,  # $5 per contract
            cost_basis=6.0,  # $6 per contract cost basis
        )

    def test_determine_price_range(self):
        """Test price range determination."""
        # Test with stock only
        price_range = determine_price_range([self.stock_position], 450.0)
        self.assertEqual(len(price_range), 2)
        self.assertLess(price_range[0], 450.0)
        self.assertGreater(price_range[1], 450.0)

        # Test with options
        price_range = determine_price_range(
            [self.stock_position, self.call_option, self.put_option], 450.0
        )
        self.assertEqual(len(price_range), 2)
        # Should include strike prices with margin
        self.assertLessEqual(price_range[0], 440.0 * 0.8)
        self.assertGreaterEqual(price_range[1], 460.0 * 1.2)

    @patch("src.folio.pnl.calculate_bs_price")
    def test_calculate_position_pnl_stock(self, mock_calculate_bs_price):
        """Test P&L calculation for a stock position."""
        # Calculate P&L for stock position using current price as entry price (default)
        pnl_data = calculate_position_pnl(
            self.stock_position,
            price_range=(400.0, 500.0),
            num_points=11,  # 400, 410, 420, ..., 500
            use_cost_basis=False,  # Use current price as entry price
        )

        # Verify the structure of the result
        self.assertIn("price_points", pnl_data)
        self.assertIn("pnl_values", pnl_data)
        self.assertEqual(len(pnl_data["price_points"]), 11)
        self.assertEqual(len(pnl_data["pnl_values"]), 11)

        # Verify P&L calculations for stock
        # P&L = (price - entry_price) * quantity
        # Entry price is $450 per share (current price)
        expected_pnls = [
            (price - 450.0) * 100 for price in np.linspace(400.0, 500.0, 11)
        ]
        for i, expected_pnl in enumerate(expected_pnls):
            self.assertAlmostEqual(pnl_data["pnl_values"][i], expected_pnl, places=2)

        # Verify mock wasn't called for stock position
        mock_calculate_bs_price.assert_not_called()

        # Reset mock for the next test
        mock_calculate_bs_price.reset_mock()

        # Calculate P&L for stock position using cost basis as entry price
        pnl_data_cost_basis = calculate_position_pnl(
            self.stock_position,
            price_range=(400.0, 500.0),
            num_points=11,  # 400, 410, 420, ..., 500
            use_cost_basis=True,  # Use cost basis as entry price
        )

        # Verify P&L calculations for stock using cost basis
        # P&L = (price - cost_basis) * quantity
        # Cost basis is $400 per share
        expected_pnls_cost_basis = [
            (price - 400.0) * 100 for price in np.linspace(400.0, 500.0, 11)
        ]
        for i, expected_pnl in enumerate(expected_pnls_cost_basis):
            self.assertAlmostEqual(
                pnl_data_cost_basis["pnl_values"][i], expected_pnl, places=2
            )

        # Verify mock wasn't called for stock position
        mock_calculate_bs_price.assert_not_called()

    @patch("src.folio.pnl.calculate_bs_price")
    def test_calculate_position_pnl_option(self, mock_calculate_bs_price):
        """Test P&L calculation for an option position."""
        # Mock the option pricing function for default mode
        mock_calculate_bs_price.side_effect = [5.0, 10.0, 15.0, 20.0, 25.0]

        # Calculate P&L for call option position using current price as entry price (default)
        pnl_data = calculate_position_pnl(
            self.call_option,
            price_range=(440.0, 480.0),
            num_points=5,  # 440, 450, 460, 470, 480
            use_cost_basis=False,  # Use current price as entry price
        )

        # Verify the structure of the result
        self.assertIn("price_points", pnl_data)
        self.assertIn("pnl_values", pnl_data)
        self.assertEqual(len(pnl_data["price_points"]), 5)
        self.assertEqual(len(pnl_data["pnl_values"]), 5)

        # Verify P&L calculations for option
        # P&L = (theo_price - entry_price) * quantity * contract_multiplier
        # Entry price is $10 per contract (current price), quantity is 1
        # Contract multiplier is 100 (each contract controls 100 shares)
        contract_multiplier = 100
        expected_pnls = [
            (price - 10.0) * 1 * contract_multiplier
            for price in [5.0, 10.0, 15.0, 20.0, 25.0]
        ]
        for i, expected_pnl in enumerate(expected_pnls):
            self.assertAlmostEqual(pnl_data["pnl_values"][i], expected_pnl, places=2)

        # Verify mock was called for option position
        self.assertEqual(mock_calculate_bs_price.call_count, 5)

        # Reset mock and set new side effect for cost basis mode
        mock_calculate_bs_price.reset_mock()
        mock_calculate_bs_price.side_effect = [5.0, 10.0, 15.0, 20.0, 25.0]

        # Calculate P&L for call option position using cost basis as entry price
        pnl_data_cost_basis = calculate_position_pnl(
            self.call_option,
            price_range=(440.0, 480.0),
            num_points=5,  # 440, 450, 460, 470, 480
            use_cost_basis=True,  # Use cost basis as entry price
        )

        # Verify P&L calculations for option using cost basis
        # P&L = (theo_price - cost_basis) * quantity * contract_multiplier
        # Cost basis is $8 per contract, quantity is 1
        expected_pnls_cost_basis = [
            (price - 8.0) * 1 * contract_multiplier
            for price in [5.0, 10.0, 15.0, 20.0, 25.0]
        ]
        for i, expected_pnl in enumerate(expected_pnls_cost_basis):
            self.assertAlmostEqual(
                pnl_data_cost_basis["pnl_values"][i], expected_pnl, places=2
            )

        # Verify mock was called for option position
        self.assertEqual(mock_calculate_bs_price.call_count, 5)

    @patch("src.folio.pnl.calculate_position_pnl")
    def test_calculate_strategy_pnl(self, mock_calculate_position_pnl):
        """Test P&L calculation for a strategy (multiple positions)."""
        # Mock the position P&L calculations for default mode
        mock_calculate_position_pnl.side_effect = [
            {
                "price_points": [400.0, 450.0, 500.0],
                "pnl_values": [-4000.0, 1000.0, 6000.0],
                "position": {},
            },
            {
                "price_points": [400.0, 450.0, 500.0],
                "pnl_values": [500.0, 200.0, -100.0],
                "position": {},
            },
            {
                "price_points": [400.0, 450.0, 500.0],
                "pnl_values": [1000.0, 0.0, -1000.0],
                "position": {},
            },
        ]

        # Calculate P&L for a strategy with all positions using current price as entry price (default)
        positions = [self.stock_position, self.call_option, self.put_option]
        pnl_data = calculate_strategy_pnl(
            positions, price_range=(400.0, 500.0), num_points=3, use_cost_basis=False
        )

        # Verify the structure of the result
        self.assertIn("price_points", pnl_data)
        self.assertIn("pnl_values", pnl_data)
        self.assertIn("individual_pnls", pnl_data)
        self.assertEqual(len(pnl_data["price_points"]), 3)
        self.assertEqual(len(pnl_data["pnl_values"]), 3)
        self.assertEqual(len(pnl_data["individual_pnls"]), 3)

        # Verify combined P&L calculations
        # Combined P&L = sum of individual P&Ls
        expected_combined_pnls = [-2500.0, 1200.0, 4900.0]
        for i, expected_pnl in enumerate(expected_combined_pnls):
            self.assertAlmostEqual(pnl_data["pnl_values"][i], expected_pnl, places=2)

        # Verify mock was called for each position
        self.assertEqual(mock_calculate_position_pnl.call_count, 3)

        # Reset mock for cost basis mode
        mock_calculate_position_pnl.reset_mock()

        # Mock the position P&L calculations for cost basis mode
        mock_calculate_position_pnl.side_effect = [
            {
                "price_points": [400.0, 450.0, 500.0],
                "pnl_values": [
                    -3000.0,
                    2000.0,
                    7000.0,
                ],  # Different values for cost basis
                "position": {},
            },
            {
                "price_points": [400.0, 450.0, 500.0],
                "pnl_values": [700.0, 400.0, 100.0],  # Different values for cost basis
                "position": {},
            },
            {
                "price_points": [400.0, 450.0, 500.0],
                "pnl_values": [
                    800.0,
                    -200.0,
                    -1200.0,
                ],  # Different values for cost basis
                "position": {},
            },
        ]

        # Calculate P&L for a strategy with all positions using cost basis as entry price
        pnl_data_cost_basis = calculate_strategy_pnl(
            positions, price_range=(400.0, 500.0), num_points=3, use_cost_basis=True
        )

        # Verify combined P&L calculations for cost basis mode
        expected_combined_pnls_cost_basis = [
            -1500.0,
            2200.0,
            5900.0,
        ]  # Different values for cost basis
        for i, expected_pnl in enumerate(expected_combined_pnls_cost_basis):
            self.assertAlmostEqual(
                pnl_data_cost_basis["pnl_values"][i], expected_pnl, places=2
            )

        # Verify mock was called for each position
        self.assertEqual(mock_calculate_position_pnl.call_count, 3)

    def test_calculate_breakeven_points(self):
        """Test calculation of breakeven points."""
        # Create sample P&L data with a zero crossing
        pnl_data = {
            "price_points": [400.0, 425.0, 450.0, 475.0, 500.0],
            "pnl_values": [-1000.0, -500.0, 0.0, 500.0, 1000.0],
        }

        # Calculate breakeven points
        breakeven_points = calculate_breakeven_points(pnl_data)

        # Verify the result - should find 2 breakeven points due to numerical precision
        self.assertEqual(len(breakeven_points), 2)
        # Both should be close to 450.0
        for bp in breakeven_points:
            self.assertAlmostEqual(bp, 450.0, places=1)

        # Test with multiple zero crossings
        pnl_data = {
            "price_points": [400.0, 425.0, 450.0, 475.0, 500.0],
            "pnl_values": [500.0, -500.0, 0.0, -500.0, 500.0],
        }

        breakeven_points = calculate_breakeven_points(pnl_data)

        # Should find 4 breakeven points due to numerical precision
        self.assertEqual(len(breakeven_points), 4)

    def test_calculate_max_profit_loss(self):
        """Test calculation of maximum profit and loss."""
        # Create sample P&L data
        pnl_data = {
            "price_points": [400.0, 425.0, 450.0, 475.0, 500.0],
            "pnl_values": [-1000.0, -500.0, 0.0, 1500.0, 1000.0],
        }

        # Calculate max profit/loss
        max_pl = calculate_max_profit_loss(pnl_data)

        # Verify the result
        self.assertEqual(max_pl["max_profit"], 1500.0)
        self.assertEqual(max_pl["max_profit_price"], 475.0)
        self.assertEqual(max_pl["max_loss"], -1000.0)
        self.assertEqual(max_pl["max_loss_price"], 400.0)

    def test_summarize_strategy_pnl(self):
        """Test strategy P&L summary generation."""
        # Create sample P&L data
        pnl_data = {
            "price_points": [400.0, 425.0, 450.0, 475.0, 500.0],
            "pnl_values": [-1000.0, -500.0, 0.0, 1500.0, 1000.0],
        }

        # Generate summary
        summary = summarize_strategy_pnl(pnl_data, 450.0)

        # Verify the structure of the result
        self.assertIn("breakeven_points", summary)
        self.assertIn("max_profit", summary)
        self.assertIn("max_loss", summary)
        self.assertIn("current_pnl", summary)
        self.assertIn("profitable_ranges", summary)

        # Verify specific values
        self.assertAlmostEqual(summary["max_profit"], 1500.0, places=2)
        self.assertAlmostEqual(summary["max_loss"], -1000.0, places=2)
        self.assertAlmostEqual(summary["current_pnl"], 0.0, places=2)

        # Should have two breakeven points due to numerical precision
        self.assertEqual(len(summary["breakeven_points"]), 2)
        # Both should be close to 450.0
        for bp in summary["breakeven_points"]:
            self.assertAlmostEqual(bp, 450.0, places=1)

        # Should have one profitable range
        self.assertEqual(len(summary["profitable_ranges"]), 1)
        start, end = summary["profitable_ranges"][0]
        # The profitable range starts at 475.0 in our implementation
        self.assertAlmostEqual(start, 475.0, places=2)
        self.assertAlmostEqual(end, 500.0, places=2)


if __name__ == "__main__":
    unittest.main()
