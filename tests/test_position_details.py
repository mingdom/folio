"""Tests for position details component and modal."""

import pytest
from dash import html

from src.folio.components.position_details import create_position_details
from src.folio.data_model import OptionPosition, PortfolioGroup, StockPosition


class TestPositionDetails:
    """Tests for position details component."""

    def test_create_position_details(self):
        """Test that position details can be created correctly."""
        # Create test positions
        stock_position = StockPosition(
            ticker="AAPL",
            quantity=100,
            market_exposure=15000.0,
            beta=1.2,
            beta_adjusted_exposure=18000.0,
        )

        option_position = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            market_exposure=1500.0,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
        )

        # Create portfolio group
        portfolio_group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock_position,
            option_positions=[option_position],
            net_exposure=16500.0,
            beta=1.2,
            beta_adjusted_exposure=19800.0,
            total_delta_exposure=1050.0,
            options_delta_exposure=1050.0,
        )

        # Create position details
        details = create_position_details(portfolio_group)

        # Verify that details is a Dash component
        assert isinstance(details, html.Div)

        # Verify that the ticker is in the title
        assert "AAPL" in details.children[0].children

        # Verify that there are sections for stock, options, and combined metrics
        assert len(details.children[1].children) == 3

    def test_create_position_details_no_stock(self):
        """Test that position details can be created correctly without a stock position."""
        # Create test positions
        option_position = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            market_exposure=1500.0,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
        )

        # Create portfolio group
        portfolio_group = PortfolioGroup(
            ticker="AAPL",
            stock_position=None,
            option_positions=[option_position],
            net_exposure=1500.0,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            total_delta_exposure=1050.0,
            options_delta_exposure=1050.0,
        )

        # Create position details
        details = create_position_details(portfolio_group)

        # Verify that details is a Dash component
        assert isinstance(details, html.Div)

        # Verify that the ticker is in the title
        assert "AAPL" in details.children[0].children

        # Verify that there are sections for options and combined metrics (no stock)
        assert len(details.children[1].children) == 2

    def test_create_position_details_no_options(self):
        """Test that position details can be created correctly without option positions."""
        # Create test positions
        stock_position = StockPosition(
            ticker="AAPL",
            quantity=100,
            market_exposure=15000.0,
            beta=1.2,
            beta_adjusted_exposure=18000.0,
        )

        # Create portfolio group
        portfolio_group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock_position,
            option_positions=[],
            net_exposure=15000.0,
            beta=1.2,
            beta_adjusted_exposure=18000.0,
            total_delta_exposure=0.0,
            options_delta_exposure=0.0,
        )

        # Create position details
        details = create_position_details(portfolio_group)

        # Verify that details is a Dash component
        assert isinstance(details, html.Div)

        # Verify that the ticker is in the title
        assert "AAPL" in details.children[0].children

        # Verify that there are sections for stock and combined metrics (no options)
        assert len(details.children[1].children) == 2

    def test_position_modal_integration(self):
        """Test the full position details modal flow as it would work in the UI.

        This test simulates what happens when a user clicks the 'details' button on a position.
        It tests the entire flow from position data to displaying the modal, ensuring that
        the modal can be created and displayed correctly regardless of the internal implementation.
        """
        # Create position data as it would be stored in the UI
        position_data = {
            "ticker": "AAPL",
            "stock_position": {
                "ticker": "AAPL",
                "quantity": 100,
                "market_exposure": 15000.0,
                "beta": 1.2,
                "beta_adjusted_exposure": 18000.0,
                "position_type": "stock",  # This field comes from to_dict() serialization
            },
            "option_positions": [],
            "net_exposure": 15000.0,
            "beta": 1.2,
            "beta_adjusted_exposure": 18000.0,
            "total_delta_exposure": 0.0,
            "options_delta_exposure": 0.0,
        }

        try:
            # Create a StockPosition from the position data
            stock_position_data = position_data["stock_position"].copy()

            # The position_type field should now be accepted by StockPosition
            # No need to remove it

            stock_position = StockPosition(**stock_position_data)

            # Create a PortfolioGroup manually
            group = PortfolioGroup(
                ticker=position_data["ticker"],
                stock_position=stock_position,
                option_positions=[],
                net_exposure=position_data["net_exposure"],
                beta=position_data["beta"],
                beta_adjusted_exposure=position_data["beta_adjusted_exposure"],
                total_delta_exposure=position_data["total_delta_exposure"],
                options_delta_exposure=position_data["options_delta_exposure"],
            )

            # Now create the position details component
            details = create_position_details(group)

            # Verify that the details component is created correctly
            assert details is not None

            # Verify that the ticker is in the title
            assert "AAPL" in details.children[0].children

            # Verify that the details has the expected sections
            assert len(details.children[1].children) == 2  # Stock and combined metrics

            # Verify that the position_type field is properly stored and returned
            assert stock_position.position_type == "stock"
            assert stock_position.to_dict()["position_type"] == "stock"
        except Exception as e:
            pytest.fail(f"Position modal failed to load: {e}")
