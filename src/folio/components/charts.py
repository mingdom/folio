"""Chart components for the Folio dashboard.

This module provides reusable chart components for visualizing portfolio data.
Each component is designed to work with the data model and can be integrated
into the main dashboard layout. It also includes the callbacks for chart interactivity.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from ..chart_data import (
    create_dashboard_metrics,
    transform_for_allocations_chart,
    transform_for_exposure_chart,
    transform_for_treemap,
)
from ..data_model import PortfolioGroup, PortfolioSummary
from ..logger import logger
from .summary_cards import create_summary_cards


def get_chart_config():
    """Get standard chart configuration with scroll zoom disabled.

    Returns:
        dict: Chart configuration with scroll zoom disabled
    """
    return {
        "displayModeBar": False,
        "responsive": True,
        "staticPlot": False,
        "doubleClick": "reset",
        "showTips": True,
        "scrollZoom": False,  # Disable scroll zoom to prevent interference with page scrolling
    }


# Asset Allocation Chart has been removed in favor of the more accurate Exposure Chart


def create_exposure_chart():
    """Create an exposure bar chart component."""
    logger.debug("Creating exposure chart component")
    return html.Div(
        [
            dcc.Graph(
                id="exposure-chart",
                config=get_chart_config(),
                className="dash-chart",
                # Add an empty figure to ensure proper initialization
                figure={
                    "data": [],
                    "layout": {
                        "height": 300,
                        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
                        "paper_bgcolor": "white",
                        "plot_bgcolor": "white",
                        "autosize": True,
                    },
                },
                style={"width": "100%", "height": "100%"},
            ),
            # Add controls for toggling between net and beta-adjusted
            html.Div(
                dbc.ButtonGroup(
                    [
                        dbc.Button(
                            "Net Exposure",
                            id="exposure-net-btn",
                            color="primary",
                            outline=True,
                            size="sm",
                            n_clicks=0,
                            className="px-3",
                        ),
                        dbc.Button(
                            "Beta-Adjusted",
                            id="exposure-beta-btn",
                            color="primary",
                            outline=True,
                            size="sm",
                            active=True,
                            n_clicks=0,
                            className="px-3",
                        ),
                    ],
                    size="sm",
                    className="chart-toggle-buttons",
                ),
                className="d-flex justify-content-center mt-3",
            ),
        ],
        className="mb-4",
    )


def create_position_treemap():
    """Create a position treemap component."""
    logger.debug("Creating position treemap component")
    return html.Div(
        [
            dcc.Graph(
                id="position-treemap",
                config=get_chart_config(),
                className="dash-chart",
                # Add an empty figure to ensure proper initialization
                figure={
                    "data": [],
                    "layout": {
                        "height": 400,
                        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
                        "paper_bgcolor": "white",
                        "autosize": True,
                    },
                },
                style={"width": "100%", "height": "100%"},
            ),
            # Hidden input to maintain the 'ticker' grouping without a visible toggle
            html.Div(
                dbc.Input(
                    id="treemap-group-by",
                    type="hidden",
                    value="ticker",  # Always group by ticker
                ),
                style={"display": "none"},
            ),
        ],
        className="mb-4",
    )


def create_allocations_chart():
    """Create a portfolio allocations stacked bar chart component."""
    logger.debug("Creating allocations chart component")
    return html.Div(
        [
            dcc.Graph(
                id="allocations-chart",
                config=get_chart_config(),
                className="dash-chart",
                # Add an empty figure to ensure proper initialization
                figure={
                    "data": [],
                    "layout": {
                        "height": 300,
                        "margin": {"l": 60, "r": 60, "t": 50, "b": 40},
                        "paper_bgcolor": "white",
                        "plot_bgcolor": "white",
                        "autosize": True,
                    },
                },
                style={"width": "100%", "height": "100%"},
            ),
        ],
        className="mb-4",
    )


# Sector chart removed for now - will be implemented in a separate task


def create_dashboard_section():
    """Create the dashboard section with all charts.

    Returns:
        html.Div: A div containing all dashboard components
    """
    logger.debug("Creating dashboard section with charts")

    # Import the summary cards component

    # Create the summary section using the dedicated component
    summary_section = create_summary_cards()

    # Create the charts section
    charts_section = dbc.Card(
        [
            dbc.CardHeader(
                dbc.Button(
                    [
                        html.I(className="fas fa-chart-bar me-2"),
                        html.Span("Portfolio Visualizations"),
                        html.I(
                            className="fas fa-chevron-down ms-2",
                            id="charts-collapse-icon",
                        ),
                    ],
                    id="charts-collapse-button",
                    color="link",
                    className="text-decoration-none text-dark p-0 d-flex align-items-center w-100 justify-content-between",
                ),
            ),
            dbc.Collapse(
                dbc.CardBody([
                    # Asset Allocation Chart has been removed in favor of the more accurate Exposure Chart
                    # Market Exposure Chart (in its own card)
                    dbc.Card(
                        [
                            dbc.CardHeader("Market Exposure"),
                            dbc.CardBody([
                                create_exposure_chart(),
                            ]),
                        ],
                        className="mb-4 chart-card",
                    ),
                    # Position Treemap (in its own card)
                    dbc.Card(
                        [
                            dbc.CardHeader("Position Size by Exposure"),
                            dbc.CardBody([
                                create_position_treemap(),
                            ]),
                        ],
                        className="mb-4 chart-card",
                    ),
                    # Portfolio Allocations Chart (in its own card)
                    dbc.Card(
                        [
                            dbc.CardHeader("Portfolio Allocation"),
                            dbc.CardBody([
                                create_allocations_chart(),
                            ]),
                        ],
                        className="mb-4 chart-card",
                    ),
                ]),
                id="charts-collapse",
                is_open=True,  # Initially open
            ),
        ],
        className="mb-3",
    )

    # We don't need to create the positions section here as it's already in app.py

    # Combine all sections
    return html.Div(
        [
            summary_section,
            charts_section,
            # positions_section is handled in app.py
        ],
        id="dashboard-section",
    )


def register_callbacks(app):
    """Register callbacks for chart interactivity.

    Args:
        app: The Dash application instance
    """
    logger.debug("Registering chart callbacks")

    # Dashboard metrics callback
    @app.callback(
        Output("dashboard-metrics", "children"),
        [Input("portfolio-summary", "data")],
    )
    def update_dashboard_metrics(summary_data):
        """Update the dashboard metrics based on portfolio summary data."""
        if not summary_data:
            return html.Div("No portfolio data available")

        try:
            # Convert the JSON data back to a PortfolioSummary object
            portfolio_summary = PortfolioSummary.from_dict(summary_data)

            # Create metric cards
            metrics = create_dashboard_metrics(portfolio_summary)

            # Create a row of metric cards
            return dbc.Row([
                dbc.Col(
                    html.Div(
                        [
                            html.H5(metric["title"], className="metric-title"),
                            html.H3(metric["value"], className="metric-value"),
                            html.Div(
                                metric["help_text"],
                                className="metric-help-text small text-muted",
                            ),
                        ],
                        className="metric-card",
                    ),
                    width=3,
                )
                for metric in metrics
            ])
        except Exception as e:
            logger.error(f"Error updating dashboard metrics: {e}", exc_info=True)
            return html.Div(f"Error loading metrics: {e!s}", className="text-danger")

    # Asset Allocation Chart callback has been removed in favor of the more accurate Exposure Chart

    # Exposure Chart callback
    @app.callback(
        [
            Output("exposure-chart", "figure"),
            Output("exposure-net-btn", "active"),
            Output("exposure-beta-btn", "active"),
        ],
        [
            Input("portfolio-summary", "data"),
            Input("exposure-net-btn", "n_clicks"),
            Input("exposure-beta-btn", "n_clicks"),
        ],
        [
            State("exposure-net-btn", "active"),
            State("exposure-beta-btn", "active"),
        ],
    )
    def update_exposure_chart(
        summary_data, _net_clicks, _beta_clicks, net_active, beta_active
    ):
        """Update the exposure chart based on user selection."""
        if not summary_data:
            # Return empty figure if no data
            logger.debug("No summary data for exposure chart")
            return ({"data": [], "layout": {"height": 300}}, True, False)

        try:
            # Log the summary data for debugging
            logger.debug(
                f"Exposure chart summary data keys: {list(summary_data.keys())}"
            )

            # Determine which view to use based on button clicks
            ctx = dash.callback_context
            if not ctx.triggered:
                # Default to beta-adjusted view
                use_beta_adjusted = True
                net_active = False
                beta_active = True
            else:
                button_id = ctx.triggered[0]["prop_id"].split(".")[0]
                if button_id == "exposure-net-btn":
                    use_beta_adjusted = False
                    net_active = True
                    beta_active = False
                elif button_id == "exposure-beta-btn":
                    use_beta_adjusted = True
                    net_active = False
                    beta_active = True
                else:
                    # If triggered by data update, maintain current state
                    use_beta_adjusted = beta_active
                    # Keep button states as they are

            logger.debug(f"Using beta-adjusted: {use_beta_adjusted}")

            # Convert the JSON data back to a PortfolioSummary object
            try:
                logger.debug("Attempting to deserialize PortfolioSummary")
                portfolio_summary = PortfolioSummary.from_dict(summary_data)
                logger.debug("Successfully deserialized PortfolioSummary")
            except Exception as deser_err:
                logger.error(
                    f"Error deserializing PortfolioSummary: {deser_err}", exc_info=True
                )
                # Check if pending_activity_value is missing
                if "pending_activity_value" not in summary_data:
                    logger.warning("pending_activity_value missing from summary_data")
                    # Add it with a default value
                    summary_data["pending_activity_value"] = 0.0
                    try:
                        portfolio_summary = PortfolioSummary.from_dict(summary_data)
                        logger.debug(
                            "Successfully deserialized after adding pending_activity_value"
                        )
                    except Exception as retry_err:
                        logger.error(
                            f"Still failed after adding pending_activity_value: {retry_err}",
                            exc_info=True,
                        )
                        raise
                else:
                    raise

            # Transform the data for the chart
            try:
                logger.debug("Transforming data for exposure chart")
                chart_data = transform_for_exposure_chart(
                    portfolio_summary, use_beta_adjusted
                )
                logger.debug("Successfully transformed data for exposure chart")
                return chart_data, net_active, beta_active
            except Exception as transform_err:
                logger.error(
                    f"Error transforming data for exposure chart: {transform_err}",
                    exc_info=True,
                )
                raise
        except Exception as e:
            logger.error(f"Error updating exposure chart: {e}", exc_info=True)
            error_figure = {
                "data": [],
                "layout": {
                    "height": 300,
                    "annotations": [
                        {
                            "text": f"Error: {e!s}",
                            "showarrow": False,
                            "font": {"color": "red"},
                        }
                    ],
                },
            }
            # Return error figure and maintain button states
            return error_figure, net_active, beta_active

    # Position Treemap callback
    @app.callback(
        Output("position-treemap", "figure"),
        [
            Input("portfolio-groups", "data"),
            Input("treemap-group-by", "value"),
        ],
    )
    def update_position_treemap(groups_data, group_by):
        """Update the position treemap based on user selection."""
        if not groups_data:
            # Return empty figure if no data
            logger.debug("No groups data for treemap chart")
            return {"data": [], "layout": {"height": 400}}

        try:
            # Log the groups data for debugging
            logger.debug(f"Treemap groups data count: {len(groups_data)}")
            if groups_data:
                logger.debug(f"First group keys: {list(groups_data[0].keys())}")

            # Convert the JSON data back to a list of PortfolioGroup objects
            try:
                logger.debug("Attempting to deserialize PortfolioGroups")
                portfolio_groups = []
                for i, group in enumerate(groups_data):
                    try:
                        portfolio_group = PortfolioGroup.from_dict(group)
                        portfolio_groups.append(portfolio_group)
                    except Exception as group_err:
                        logger.error(
                            f"Error deserializing group {i}: {group_err}", exc_info=True
                        )
                        # Log the problematic group data
                        logger.debug(f"Problematic group data: {group}")
                        raise
                logger.debug(
                    f"Successfully deserialized {len(portfolio_groups)} PortfolioGroups"
                )
            except Exception as deser_err:
                logger.error(
                    f"Error deserializing PortfolioGroups: {deser_err}", exc_info=True
                )
                raise

            # Transform the data for the chart
            try:
                logger.debug("Transforming data for treemap chart")
                chart_data = transform_for_treemap(portfolio_groups, group_by)
                logger.debug("Successfully transformed data for treemap chart")
                return chart_data
            except Exception as transform_err:
                logger.error(
                    f"Error transforming data for treemap chart: {transform_err}",
                    exc_info=True,
                )
                raise
        except Exception as e:
            logger.error(f"Error updating position treemap: {e}", exc_info=True)
            return {
                "data": [],
                "layout": {
                    "height": 400,
                    "annotations": [
                        {
                            "text": f"Error: {e!s}",
                            "showarrow": False,
                            "font": {"color": "red"},
                        }
                    ],
                },
            }

    # Allocations Chart callback
    @app.callback(
        Output("allocations-chart", "figure"),
        [Input("portfolio-summary", "data")],
    )
    def update_allocations_chart(summary_data):
        """Update the allocations chart based on portfolio summary data."""
        if not summary_data:
            # Return empty figure if no data
            logger.debug("No summary data for allocations chart")
            return {"data": [], "layout": {"height": 300}}

        try:
            # Convert the JSON data back to a PortfolioSummary object
            try:
                logger.debug(
                    "Attempting to deserialize PortfolioSummary for allocations chart"
                )
                portfolio_summary = PortfolioSummary.from_dict(summary_data)
                logger.debug(
                    "Successfully deserialized PortfolioSummary for allocations chart"
                )
            except Exception as deser_err:
                logger.error(
                    f"Error deserializing PortfolioSummary for allocations chart: {deser_err}",
                    exc_info=True,
                )
                # Check if pending_activity_value is missing
                if "pending_activity_value" not in summary_data:
                    logger.warning("pending_activity_value missing from summary_data")
                    # Add it with a default value
                    summary_data["pending_activity_value"] = 0.0
                    try:
                        portfolio_summary = PortfolioSummary.from_dict(summary_data)
                        logger.debug(
                            "Successfully deserialized after adding pending_activity_value"
                        )
                    except Exception as retry_err:
                        logger.error(
                            f"Still failed after adding pending_activity_value: {retry_err}",
                            exc_info=True,
                        )
                        raise
                else:
                    raise

            # Transform the data for the chart
            try:
                logger.debug("Transforming data for allocations chart")
                chart_data = transform_for_allocations_chart(portfolio_summary)
                logger.debug("Successfully transformed data for allocations chart")
                return chart_data
            except Exception as transform_err:
                logger.error(
                    f"Error transforming data for allocations chart: {transform_err}",
                    exc_info=True,
                )
                raise
        except Exception as e:
            logger.error(f"Error updating allocations chart: {e}", exc_info=True)
            return {
                "data": [],
                "layout": {
                    "height": 300,
                    "annotations": [
                        {
                            "text": f"Error: {e!s}",
                            "showarrow": False,
                            "font": {"color": "red"},
                        }
                    ],
                },
            }

    # Sector Chart callback
    # Sector chart callback removed - will be implemented in a separate task


# For backward compatibility
register_chart_callbacks = register_callbacks
