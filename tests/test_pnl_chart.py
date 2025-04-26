"""
Unit tests for the P&L chart component.
"""

import unittest

import plotly.graph_objects as go

from src.folio.components.pnl_chart import (
    create_pnl_chart,
    create_pnl_modal,
    create_pnl_summary,
)


class TestPnlChart(unittest.TestCase):
    """Test cases for the P&L chart component."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample data for testing
        self.pnl_data = {
            "price_points": [90.0, 100.0, 110.0],
            "pnl_values": [-1000.0, 0.0, 1000.0],
            "individual_pnls": [
                {
                    "price_points": [90.0, 100.0, 110.0],
                    "pnl_values": [-1000.0, 0.0, 1000.0],
                    "position": {
                        "ticker": "SPY",
                        "position_type": "stock",
                        "quantity": 100,
                        "price": 100.0,
                    },
                },
                {
                    "price_points": [90.0, 100.0, 110.0],
                    "pnl_values": [200.0, 0.0, -200.0],
                    "position": {
                        "ticker": "SPY",
                        "position_type": "option",
                        "option_type": "PUT",
                        "strike": 95.0,
                        "quantity": -1,
                        "price": 5.0,
                    },
                },
            ],
        }

        self.summary = {
            "current_pnl": 0.0,
            "max_profit": 1000.0,
            "max_profit_price": 110.0,
            "max_loss": -1000.0,
            "max_loss_price": 90.0,
            "breakeven_points": [100.0],
        }

        self.current_price = 100.0
        self.ticker = "SPY"

    def test_create_pnl_chart(self):
        """Test creating a P&L chart."""
        # Create chart
        fig = create_pnl_chart(
            self.pnl_data,
            self.summary,
            self.current_price,
            self.ticker,
            mode="default",
        )

        # Verify the chart is a Plotly figure
        self.assertIsInstance(fig, go.Figure)

        # Verify the chart has the correct number of traces
        # 1 for combined P&L, 2 for individual positions, 3 for markers (max profit, max loss, current)
        self.assertEqual(len(fig.data), 6)

        # Verify the chart title contains the ticker
        self.assertIn(self.ticker, fig.layout.title.text)

        # Test with cost basis mode
        fig_cost_basis = create_pnl_chart(
            self.pnl_data,
            self.summary,
            self.current_price,
            self.ticker,
            mode="cost_basis",
        )

        # Verify the chart title contains the ticker
        self.assertIn(self.ticker, fig_cost_basis.layout.title.text)

    def test_create_pnl_summary(self):
        """Test creating a P&L summary component."""
        # Create summary component
        summary_component = create_pnl_summary(self.summary, mode="default")

        # Verify the summary component is a Div
        from dash import html

        self.assertIsInstance(summary_component, html.Div)

        # Verify the summary component contains the expected elements
        self.assertIn("Max Profit", str(summary_component))
        self.assertIn("Max Loss", str(summary_component))
        self.assertIn("Break-even", str(summary_component))

        # Test with cost basis mode (should be the same as default now)
        summary_component_cost_basis = create_pnl_summary(
            self.summary, mode="cost_basis"
        )

        # Verify the summary component contains the same elements
        self.assertIn("Max Profit", str(summary_component_cost_basis))

    def test_create_pnl_modal(self):
        """Test creating a P&L modal."""
        # Create modal
        modal = create_pnl_modal()

        # Verify the modal has the correct ID
        self.assertEqual(modal.id, "pnl-modal")

        # Verify the modal contains the chart
        self.assertIn("pnl-chart", str(modal))

        # Verify the modal contains the summary section
        self.assertIn("pnl-summary", str(modal))


if __name__ == "__main__":
    unittest.main()
