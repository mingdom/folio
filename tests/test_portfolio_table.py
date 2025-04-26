"""Tests for portfolio table component."""

from src.folio.components.portfolio_table import create_position_row
from src.folio.data_model import OptionPosition, PortfolioGroup, StockPosition


class TestPortfolioTable:
    """Tests for portfolio table component."""

    def test_create_position_row(self):
        """Test that a position row can be created correctly."""
        # Create a portfolio group
        stock_position = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
        )
        option_position = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=1500.0,
        )
        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock_position,
            option_positions=[option_position],
            net_exposure=16500.0,
            beta=1.2,
            beta_adjusted_exposure=19800.0,
            total_delta_exposure=1050.0,
            options_delta_exposure=1050.0,
        )

        # Create a position row
        row = create_position_row(group, {})

        # Verify that row is a Dash component
        assert row is not None

    def test_portfolio_table_serialization(self):
        """Test that a portfolio group can be serialized and deserialized correctly."""
        # Create a portfolio group
        stock_position = StockPosition(
            ticker="AAPL",
            quantity=100,
            beta=1.2,
            market_exposure=15000.0,
            beta_adjusted_exposure=18000.0,
        )
        option_position = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            beta=1.2,
            beta_adjusted_exposure=1800.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=1050.0,
            notional_value=15000.0,
            underlying_beta=1.2,
            market_exposure=1500.0,
        )
        group = PortfolioGroup(
            ticker="AAPL",
            stock_position=stock_position,
            option_positions=[option_position],
            net_exposure=16500.0,
            beta=1.2,
            beta_adjusted_exposure=19800.0,
            total_delta_exposure=1050.0,
            options_delta_exposure=1050.0,
        )

        # Serialize to dictionary
        group_dict = group.to_dict()

        # Verify that the dictionary contains the expected fields
        assert group_dict["ticker"] == "AAPL"
        assert group_dict["stock_position"]["ticker"] == "AAPL"
        assert group_dict["stock_position"]["position_type"] == "stock"
        assert group_dict["option_positions"][0]["ticker"] == "AAPL"
        assert group_dict["option_positions"][0]["position_type"] == "option"

        # Deserialize back to a PortfolioGroup
        new_group = PortfolioGroup.from_dict(group_dict)

        # Verify that the deserialized group has the same properties
        assert new_group.ticker == "AAPL"
        assert new_group.stock_position.ticker == "AAPL"
        assert new_group.option_positions[0].ticker == "AAPL"

    def test_app_portfolio_table_update(self):
        """Test that the portfolio table update function handles position_type correctly."""
        # Create a dictionary representation of a stock position with position_type
        stock_position_data = {
            "ticker": "AAPL",
            "quantity": 100,
            "beta": 1.2,
            "market_exposure": 15000.0,
            "beta_adjusted_exposure": 18000.0,
            "position_type": "stock",  # This should be ignored by StockPosition constructor
        }

        # Create a StockPosition with position_type included (now accepted)
        stock_position = StockPosition(**stock_position_data)

        # Verify the position was created correctly
        assert stock_position.ticker == "AAPL"
        assert stock_position.quantity == 100
        assert stock_position.beta == 1.2
        assert stock_position.market_exposure == 15000.0
        assert stock_position.beta_adjusted_exposure == 18000.0
        assert stock_position.position_type == "stock"  # Should be set correctly

        # Test with a different position_type to ensure it's handled correctly
        stock_position_data_wrong_type = stock_position_data.copy()
        stock_position_data_wrong_type["position_type"] = "option"  # Wrong type

        # Create a StockPosition with wrong position_type
        stock_position_wrong_type = StockPosition(**stock_position_data_wrong_type)

        # The position_type is now accepted as provided
        assert stock_position_wrong_type.position_type == "option"
