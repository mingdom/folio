"""Tests for AI integration features."""

from src.folio.ai_utils import prepare_portfolio_data_for_analysis
from src.folio.data_model import (
    ExposureBreakdown,
    OptionPosition,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
)


class TestAIIntegration:
    """Tests for AI integration features."""

    def test_prepare_portfolio_data_for_analysis(self):
        """Test that portfolio data can be prepared for AI analysis correctly."""
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

        # Create test exposure breakdowns
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

        # Create portfolio summary
        summary = PortfolioSummary(
            net_market_exposure=16500.0,
            portfolio_beta=1.2,
            long_exposure=exposure,
            short_exposure=exposure,
            options_exposure=exposure,
            short_percentage=0.0,
            cash_like_positions=[],
            cash_like_value=0.0,
            cash_like_count=0,
            portfolio_estimate_value=20000.0,  # Add portfolio value for testing
            pending_activity_value=500.0,  # Add pending activity for testing
        )

        # Test prepare_portfolio_data_for_analysis
        ai_data = prepare_portfolio_data_for_analysis([portfolio_group], summary)

        # Verify the structure of the prepared data
        assert "positions" in ai_data
        assert "summary" in ai_data
        assert "allocations" in ai_data
        assert len(ai_data["positions"]) == 2  # Stock and option position

        # Verify stock position data
        stock_data = next(
            (p for p in ai_data["positions"] if p["position_type"] == "stock"), None
        )
        assert stock_data is not None
        assert stock_data["ticker"] == "AAPL"
        assert stock_data["market_value"] == 15000.0
        assert stock_data["beta"] == 1.2

        # Verify option position data
        option_data = next(
            (p for p in ai_data["positions"] if p["position_type"] == "option"), None
        )
        assert option_data is not None
        assert option_data["ticker"] == "AAPL"
        assert option_data["market_value"] == 1500.0
        assert option_data["option_type"] == "CALL"
        assert option_data["strike"] == 150.0

        # Verify summary data
        assert ai_data["summary"]["net_market_exposure"] == 16500.0
        assert "long_exposure" in ai_data["summary"]
        assert "short_exposure" in ai_data["summary"]
        assert "portfolio_value" in ai_data["summary"]
        assert ai_data["summary"]["portfolio_value"] == 20000.0
        assert "cash_like_value" in ai_data["summary"]

        # Verify allocation data
        allocations = ai_data["allocations"]
        assert "values" in allocations
        assert "percentages" in allocations

        # Verify values and percentages contain expected keys
        values = allocations["values"]
        percentages = allocations["percentages"]
        expected_keys = [
            "long_stock",
            "short_stock",
            "long_option",
            "short_option",
            "cash",
            "pending",
            "total",
        ]
        for key in expected_keys:
            assert key in values
            assert key in percentages

    def test_portfolio_data_conversion_for_chat(self):
        """Test that portfolio data can be properly converted between dict and object formats for the chat feature."""
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

        # Create test exposure breakdowns
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

        # Create portfolio summary
        summary = PortfolioSummary(
            net_market_exposure=16500.0,
            portfolio_beta=1.2,
            long_exposure=exposure,
            short_exposure=exposure,
            options_exposure=exposure,
            short_percentage=0.0,
            cash_like_positions=[],
            cash_like_value=0.0,
            cash_like_count=0,
            portfolio_estimate_value=20000.0,  # Add portfolio value for testing
            pending_activity_value=500.0,  # Add pending activity for testing
        )

        # Convert to dictionary format as would be stored in Dash
        groups_data = [portfolio_group.to_dict()]
        summary_data = summary.to_dict()

        # Test that PortfolioGroup.from_dict works with this data
        restored_groups = [PortfolioGroup.from_dict(g) for g in groups_data]
        assert len(restored_groups) == 1
        assert restored_groups[0].ticker == "AAPL"
        assert restored_groups[0].total_value == 16500.0

        # Test that PortfolioSummary.from_dict works with this data
        restored_summary = PortfolioSummary.from_dict(summary_data)
        assert restored_summary.net_market_exposure == 16500.0
        assert restored_summary.portfolio_estimate_value == 20000.0

        # Test prepare_portfolio_data_for_analysis with the restored objects
        ai_data = prepare_portfolio_data_for_analysis(restored_groups, restored_summary)
        assert "positions" in ai_data
        assert "summary" in ai_data
        assert "allocations" in ai_data
        assert len(ai_data["positions"]) == 2  # Stock and option position

        # Verify allocation data is present
        allocations = ai_data["allocations"]
        assert "values" in allocations
        assert "percentages" in allocations
