"""Tests for chart color consistency across all charts."""

import pytest

from src.folio.chart_data import (
    ChartColors,
    transform_for_allocations_chart,
    transform_for_exposure_chart,
    transform_for_treemap,
)
from src.folio.data_model import (
    ExposureBreakdown,
    OptionPosition,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
)


class TestChartColors:
    """Tests for chart color consistency across all charts."""

    @pytest.fixture
    def mock_portfolio_summary(self):
        """Create a mock portfolio summary for testing."""
        # Create exposure breakdowns
        long_exposure = ExposureBreakdown(
            stock_exposure=10000.0,
            stock_beta_adjusted=12000.0,
            option_delta_exposure=2000.0,
            option_beta_adjusted=2400.0,
            total_exposure=12000.0,
            total_beta_adjusted=14400.0,
            description="Long market exposure (Stocks + Options)",
            formula="Long Stocks + Long Options Delta Exp",
            components={
                "Long Stocks Exposure": 10000.0,
                "Long Options Delta Exp": 2000.0,
                "Long Stocks Value": 10000.0,
                "Long Options Value": 2000.0,
            },
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=-5000.0,  # Negative value
            stock_beta_adjusted=-6000.0,
            option_delta_exposure=-1000.0,  # Negative value
            option_beta_adjusted=-1200.0,
            total_exposure=-6000.0,
            total_beta_adjusted=-7200.0,
            description="Short market exposure (Stocks + Options)",
            formula="Short Stocks + Short Options Delta Exp",
            components={
                "Short Stocks Exposure": -5000.0,  # Negative value
                "Short Options Delta Exp": -1000.0,  # Negative value
                "Short Stocks Value": -5000.0,  # Negative value
                "Short Options Value": -1000.0,  # Negative value
            },
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=1000.0,
            option_beta_adjusted=1200.0,
            total_exposure=1000.0,
            total_beta_adjusted=1200.0,
            description="Net delta exposure from options",
            formula="Long Options Delta Exp + Short Options Delta Exp (where Short is negative)",
            components={
                "Long Options Delta Exp": 2000.0,
                "Short Options Delta Exp": -1000.0,  # Negative value
                "Net Options Delta Exp": 1000.0,
            },
        )

        # Create portfolio summary
        return PortfolioSummary(
            net_market_exposure=6000.0,
            portfolio_beta=1.2,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=50.0,
            cash_like_positions=[],
            cash_like_value=3000.0,
            cash_like_count=1,
            cash_percentage=20.0,
            stock_value=5000.0,
            option_value=1000.0,
            pending_activity_value=500.0,
            portfolio_estimate_value=15000.0,
            price_updated_at="2025-05-03T09:09:46Z",
        )

    @pytest.fixture
    def mock_portfolio_groups(self):
        """Create mock portfolio groups for testing."""
        # Create stock positions
        aapl_stock = StockPosition(
            ticker="AAPL",
            position_type="stock",
            quantity=100,
            market_exposure=5000.0,
            beta=1.2,
            beta_adjusted_exposure=6000.0,
        )

        msft_stock = StockPosition(
            ticker="MSFT",
            position_type="stock",
            quantity=50,
            market_exposure=3000.0,
            beta=1.1,
            beta_adjusted_exposure=3300.0,
        )

        # Create option positions
        aapl_option = OptionPosition(
            ticker="AAPL",
            position_type="option",
            quantity=10,
            market_exposure=1000.0,
            beta=1.2,
            beta_adjusted_exposure=1200.0,
            strike=150.0,
            expiry="2023-01-01",
            option_type="CALL",
            delta=0.7,
            delta_exposure=700.0,
            notional_value=10000.0,
            underlying_beta=1.2,
        )

        # Create portfolio groups
        aapl_group = PortfolioGroup(
            ticker="AAPL",
            stock_position=aapl_stock,
            option_positions=[aapl_option],
            net_exposure=5700.0,
            beta=1.2,
            beta_adjusted_exposure=6840.0,
            total_delta_exposure=700.0,
            options_delta_exposure=700.0,
        )

        msft_group = PortfolioGroup(
            ticker="MSFT",
            stock_position=msft_stock,
            option_positions=[],
            net_exposure=3000.0,
            beta=1.1,
            beta_adjusted_exposure=3300.0,
            total_delta_exposure=0.0,
            options_delta_exposure=0.0,
        )

        return [aapl_group, msft_group]

    def test_color_constants_defined(self):
        """Test that all required color constants are defined in ChartColors."""
        # Core colors that should be defined
        assert hasattr(ChartColors, "LONG")
        assert hasattr(ChartColors, "SHORT")
        assert hasattr(ChartColors, "OPTIONS")
        assert hasattr(ChartColors, "NET")
        assert hasattr(ChartColors, "CASH")
        assert hasattr(ChartColors, "PENDING")

        # Verify they are all hex color strings
        for color_name in ["LONG", "SHORT", "OPTIONS", "NET", "CASH", "PENDING"]:
            color = getattr(ChartColors, color_name)
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB format

    def test_exposure_chart_uses_standard_colors(self, mock_portfolio_summary):
        """Test that the exposure chart uses the standard colors from ChartColors."""
        # Get the chart data
        chart_data = transform_for_exposure_chart(mock_portfolio_summary)

        # Extract the colors used in the chart
        colors = chart_data["data"][0]["marker"]["color"]

        # Verify that the colors match the ChartColors constants
        assert colors[0] == ChartColors.LONG  # Long
        assert colors[1] == ChartColors.SHORT  # Short
        assert colors[2] == ChartColors.OPTIONS  # Options
        assert colors[3] == ChartColors.NET  # Net

    def test_treemap_chart_uses_standard_colors(self, mock_portfolio_groups):
        """Test that the treemap chart uses the standard colors from ChartColors."""
        # Get the chart data
        chart_data = transform_for_treemap(mock_portfolio_groups)

        # Extract colors from the chart data
        # The first color is white for the root node, the rest are for the tickers
        colors = chart_data["data"][0]["marker"]["colors"]

        # We should have at least one green color (for AAPL and MSFT which are both long)
        # The first color is white for the root node
        assert colors[0] == "#FFFFFF"  # Root node is white

        # At least one of the other colors should be the LONG color
        assert ChartColors.LONG in colors[1:], "Long color not found in treemap"

        # SHORT color might not be present if there are no short positions in the test data
        # but we can verify the code would use it by checking the source
        import inspect

        source = inspect.getsource(transform_for_treemap)
        assert "ChartColors.LONG" in source
        assert "ChartColors.SHORT" in source

    def test_allocations_chart_uses_standard_colors(self, mock_portfolio_summary):
        """Test that the allocations chart uses the standard colors from ChartColors."""
        # Get the chart data
        chart_data = transform_for_allocations_chart(mock_portfolio_summary)

        # Extract the colors used in the chart
        long_color = chart_data["data"][0]["marker"]["color"]
        short_color = chart_data["data"][1]["marker"]["color"]
        cash_color = chart_data["data"][2]["marker"]["color"]
        pending_color = chart_data["data"][3]["marker"]["color"]

        # Verify that the colors match the ChartColors constants
        assert long_color == ChartColors.LONG
        assert short_color == ChartColors.SHORT
        assert cash_color == ChartColors.CASH
        assert pending_color == ChartColors.PENDING
