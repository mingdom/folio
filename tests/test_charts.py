"""Tests for chart components and visualizations."""

import dash_bootstrap_components as dbc
import pytest
from dash import html

from src.folio.app import create_app
from src.folio.chart_data import transform_for_exposure_chart, transform_for_treemap
from src.folio.components.charts import (
    create_dashboard_section,
    create_exposure_chart,
    create_position_treemap,
)
from src.folio.data_model import (
    ExposureBreakdown,
    OptionPosition,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
)


class TestChartComponents:
    """Tests for individual chart components."""

    def test_create_exposure_chart(self):
        """Test that exposure chart can be created correctly."""
        # Create the chart component
        chart = create_exposure_chart()

        # Verify that chart is a Dash component
        assert isinstance(chart, html.Div)

        # Verify that the chart contains a Graph component with the correct ID
        graph_component = None
        button_net_component = None
        button_beta_component = None

        # Find the essential components without assuming specific structure
        def find_components(component):
            nonlocal graph_component, button_net_component, button_beta_component
            if hasattr(component, "id"):
                if component.id == "exposure-chart":
                    graph_component = component
                elif component.id == "exposure-net-btn":
                    button_net_component = component
                elif component.id == "exposure-beta-btn":
                    button_beta_component = component

            # Recursively check children
            if hasattr(component, "children") and component.children:
                if isinstance(component.children, list):
                    for child in component.children:
                        find_components(child)
                else:
                    find_components(component.children)

        find_components(chart)

        # Verify essential components exist
        assert graph_component is not None, "Graph component not found"
        assert button_net_component is not None, "Net exposure button not found"
        assert button_beta_component is not None, "Beta-adjusted button not found"

        # Verify button properties
        assert button_net_component.children == "Net Exposure"
        assert button_beta_component.children == "Beta-Adjusted"

    def test_create_position_treemap(self):
        """Test that position treemap can be created correctly."""
        # Create the chart component
        chart = create_position_treemap()

        # Verify that chart is a Dash component
        assert isinstance(chart, html.Div)

        # Verify that the chart contains a Graph component with the correct ID
        graph_found = False
        hidden_div_found = False
        hidden_input_found = False
        hidden_input_value = None

        # Check for the graph component
        for child in chart.children:
            if hasattr(child, "id") and child.id == "position-treemap":
                graph_found = True

            # Check for the hidden div containing the input
            if (
                isinstance(child, html.Div)
                and hasattr(child, "style")
                and child.style.get("display") == "none"
            ):
                hidden_div_found = True

                # Check for the hidden input inside the div
                if (
                    hasattr(child, "children")
                    and hasattr(child.children, "id")
                    and child.children.id == "treemap-group-by"
                ):
                    hidden_input_found = True
                    hidden_input_value = child.children.value

        # Verify essential components exist
        assert graph_found, "Graph component not found"
        assert hidden_div_found, "Hidden div not found"
        assert hidden_input_found, "Hidden input not found"

        # Verify hidden input properties
        assert hidden_input_value == "ticker", "Hidden input value is incorrect"

    def test_create_dashboard_section(self):
        """Test that dashboard section can be created correctly."""
        # Create the dashboard section
        dashboard = create_dashboard_section()

        # Verify that dashboard is a Dash component
        assert isinstance(dashboard, html.Div)
        assert dashboard.id == "dashboard-section"

        # Verify that dashboard has the expected structure
        assert len(dashboard.children) == 2  # Summary section and charts section

        # Verify charts section
        charts_section = dashboard.children[1]
        assert isinstance(charts_section, dbc.Card)

        # Verify collapse component
        collapse = charts_section.children[1]
        assert collapse.id == "charts-collapse"
        assert collapse.is_open is True  # Initially open

        # Verify chart cards
        card_body = collapse.children
        assert isinstance(card_body, dbc.CardBody)

        # There should be 3 chart cards (exposure, treemap, allocations)
        chart_cards = card_body.children
        assert len(chart_cards) == 3

        # Verify card titles
        assert "Market Exposure" in str(chart_cards[0])
        assert "Position Size by Exposure" in str(chart_cards[1])
        assert "Portfolio Allocation" in str(chart_cards[2])


class TestChartDataTransformation:
    """Tests for chart data transformation functions."""

    @pytest.fixture
    def mock_portfolio_summary(self):
        """Create a mock portfolio summary for testing."""
        # Create exposure breakdowns
        long_exposure = ExposureBreakdown(
            stock_exposure=10000.0,
            option_delta_exposure=2000.0,
            total_exposure=12000.0,
            total_beta_adjusted=14400.0,
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=-5000.0,
            option_delta_exposure=-1000.0,
            total_exposure=-6000.0,
            total_beta_adjusted=-7200.0,
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            option_delta_exposure=1000.0,
            total_exposure=1000.0,
            total_beta_adjusted=1200.0,
        )

        # Create portfolio summary
        return PortfolioSummary(
            net_market_exposure=6000.0,
            portfolio_beta=1.2,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=0.33,
            cash_like_value=4000.0,
            cash_like_count=1,
            cash_percentage=0.4,
            portfolio_estimate_value=10000.0,
        )

    @pytest.fixture
    def mock_portfolio_groups(self):
        """Create mock portfolio groups for testing."""
        # Create stock positions
        aapl_stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            market_exposure=5000.0,
            beta=1.2,
            beta_adjusted_exposure=6000.0,
        )

        msft_stock = StockPosition(
            ticker="MSFT",
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

    def test_transform_for_exposure_chart(self, mock_portfolio_summary):
        """Test that exposure chart data is transformed correctly."""
        # Test with beta-adjusted values (default)
        chart_data = transform_for_exposure_chart(
            mock_portfolio_summary, use_beta_adjusted=True
        )

        # Verify chart data structure
        assert "data" in chart_data
        assert "layout" in chart_data

        # Verify data contains the expected traces
        data = chart_data["data"]
        assert len(data) == 1  # One trace for the bar chart

        # Verify the trace has the expected structure
        trace = data[0]
        assert trace["type"] == "bar"
        assert len(trace["x"]) == 4  # Long, Short, Net, Options
        assert len(trace["y"]) == 4  # Values for each category

        # Test with non-beta-adjusted values
        chart_data = transform_for_exposure_chart(
            mock_portfolio_summary, use_beta_adjusted=False
        )

        # Verify the title reflects non-beta-adjusted values
        assert "Beta-Adjusted" not in chart_data["layout"]["title"]

    def test_transform_for_treemap(self, mock_portfolio_groups):
        """Test that treemap data is transformed correctly."""
        chart_data = transform_for_treemap(mock_portfolio_groups)

        # Verify chart data structure
        assert "data" in chart_data
        assert "layout" in chart_data

        # Verify data contains the expected traces
        data = chart_data["data"]
        assert len(data) == 1  # One trace for the treemap

        # Verify the trace has the expected structure
        trace = data[0]
        assert trace["type"] == "treemap"

        # Verify the treemap has the expected data points
        assert "Portfolio" in trace["labels"]
        assert "AAPL" in trace["labels"]
        assert "MSFT" in trace["labels"]

        # Verify the values are absolute exposures
        values = trace["values"]
        assert len(values) > 2  # Root + at least 2 tickers


class TestChartIntegration:
    """Integration tests for chart components."""

    @pytest.fixture
    def mock_portfolio_summary(self):
        """Create a mock portfolio summary for testing."""
        # Create exposure breakdowns
        long_exposure = ExposureBreakdown(
            stock_exposure=10000.0,
            option_delta_exposure=2000.0,
            total_exposure=12000.0,
            total_beta_adjusted=14400.0,
        )

        short_exposure = ExposureBreakdown(
            stock_exposure=-5000.0,
            option_delta_exposure=-1000.0,
            total_exposure=-6000.0,
            total_beta_adjusted=-7200.0,
        )

        options_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            option_delta_exposure=1000.0,
            total_exposure=1000.0,
            total_beta_adjusted=1200.0,
        )

        # Create portfolio summary
        return PortfolioSummary(
            net_market_exposure=6000.0,
            portfolio_beta=1.2,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=0.33,
            cash_like_value=4000.0,
            cash_like_count=1,
            cash_percentage=0.4,
            portfolio_estimate_value=10000.0,
        )

    @pytest.fixture
    def mock_portfolio_groups(self):
        """Create mock portfolio groups for testing."""
        # Create stock positions
        aapl_stock = StockPosition(
            ticker="AAPL",
            quantity=100,
            market_exposure=5000.0,
            beta=1.2,
            beta_adjusted_exposure=6000.0,
        )

        msft_stock = StockPosition(
            ticker="MSFT",
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

    def test_chart_callbacks_registration(self):
        """Test that chart callbacks are properly registered."""
        # Create the app
        app = create_app()

        # Check that the callbacks for charts are registered
        callbacks = app.callback_map

        # Asset Allocation Chart has been removed in favor of the more accurate Exposure Chart
        # We no longer need to check for its callback

        # Check for exposure chart callback
        exposure_chart_callback_found = False
        for callback_id in callbacks.keys():
            if "exposure-chart.figure" in callback_id:
                exposure_chart_callback_found = True
                break

        assert exposure_chart_callback_found, "Exposure chart callback not registered"

        # Check for position treemap callback
        treemap_callback_found = False
        for callback_id in callbacks.keys():
            if "position-treemap.figure" in callback_id:
                treemap_callback_found = True
                break

        assert treemap_callback_found, "Position treemap callback not registered"

    def test_dashboard_section_in_app_layout(self):
        """Test that dashboard section is included in the app layout."""
        # Create the app
        app = create_app()

        # Get the layout
        layout = app.layout

        # Define the expected component IDs
        expected_ids = [
            # Asset Allocation Chart has been removed in favor of the more accurate Exposure Chart
            "exposure-chart",
            "position-treemap",
            "allocations-chart",  # Added allocations chart
            "charts-collapse",
            "charts-collapse-button",
            "charts-collapse-icon",
            "exposure-net-btn",
            "exposure-beta-btn",
            "treemap-group-by",
        ]

        # Find all components with IDs in the layout
        found_ids = set()

        def find_components(component):
            """Recursively find all components with IDs in the layout."""
            if hasattr(component, "id") and component.id is not None:
                found_ids.add(component.id)

            if hasattr(component, "children"):
                if isinstance(component.children, list):
                    for child in component.children:
                        find_components(child)
                elif component.children is not None:
                    find_components(component.children)

        # Search the layout
        find_components(layout)

        # Check that all expected IDs are found
        for component_id in expected_ids:
            assert component_id in found_ids, (
                f"Component {component_id} not found in layout"
            )
