"""
Main application module for the Folio app.

This module contains the main application logic for the Folio app.
"""

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Input, Output, State, dcc, html
from dash_bootstrap_templates import load_figure_template

from . import portfolio
from .components import create_premium_chat_component, register_premium_chat_callbacks
from .components.charts import create_dashboard_section
from .components.charts import register_callbacks as register_chart_callbacks
from .components.pnl_chart import create_pnl_modal
from .components.pnl_chart import register_callbacks as register_pnl_callbacks
from .components.portfolio_table import create_portfolio_table
from .components.summary_cards import create_summary_cards
from .data_model import OptionPosition, PortfolioGroup, StockPosition
from .error_utils import handle_callback_error
from .logger import logger
from .security import sanitize_dataframe, validate_csv_upload

# Load the Bootstrap template for Plotly figures
load_figure_template("bootstrap")


def create_header() -> dbc.Card:
    """Create the header section with summary cards"""
    # Use the create_summary_cards function from summary_cards.py
    return create_summary_cards()


def create_empty_state() -> html.Div:
    """Create the empty state with instructions"""
    # Check if private portfolio exists
    private_path = Path(os.getcwd()) / "private-data" / "portfolio-private.csv"
    button_label = (
        "Load Private Portfolio" if private_path.exists() else "Load Sample Portfolio"
    )

    return html.Div(
        [
            html.H4("Welcome to Folio", className="text-center mb-3"),
            html.P(
                "Upload your portfolio CSV file to get started", className="text-center"
            ),
            html.Div(
                [
                    html.I(className="fas fa-upload fa-3x"),
                ],
                className="text-center my-4",
            ),
            html.P(
                "Or try a sample portfolio to explore the features",
                className="text-center mt-3",
            ),
            dbc.Button(
                button_label,
                id="load-sample",
                color="primary",
                className="mx-auto d-block",
            ),
            # Keyboard shortcut hint removed
        ],
        className="empty-state py-5",
    )


def create_upload_section() -> dbc.Card:
    """Create the file upload section with collapsible functionality"""
    return dbc.Card(
        [
            dbc.CardHeader(
                dbc.Button(
                    [
                        html.I(className="fas fa-upload me-2"),
                        html.Span("Upload Portfolio"),
                        html.I(
                            className="fas fa-chevron-down ms-2", id="collapse-icon"
                        ),
                    ],
                    id="upload-collapse-button",
                    color="link",
                    className="text-decoration-none text-dark p-0 d-flex align-items-center",
                ),
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.Collapse(
                dbc.CardBody(
                    [
                        dcc.Upload(
                            id="upload-portfolio",
                            children=html.Div(
                                [
                                    html.I(className="fas fa-file-upload me-2"),
                                    "Drag and Drop or ",
                                    html.A(
                                        "Select a CSV File", className="text-primary"
                                    ),
                                ]
                            ),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "textAlign": "center",
                                "margin": "10px 0",
                            },
                            # Filter for CSV files
                            accept=".csv",
                            multiple=False,
                        ),
                        dcc.Loading(
                            id="upload-loading",
                            type="circle",
                            children=[html.Div(id="upload-status")],
                        ),
                    ]
                ),
                id="upload-collapse",
                is_open=True,  # Initially open
            ),
        ],
        className="mb-3",
    )


def create_filters() -> dbc.InputGroup:
    """Create the search and filter controls"""
    return dbc.InputGroup(
        [
            dbc.Input(
                id="search-input",
                type="text",
                placeholder="Search positions...",
                className="border-end-0",
            ),
            dbc.InputGroupText(
                html.I(className="fas fa-search"),
                className="bg-transparent border-start-0",
            ),
            dbc.Button(
                "All",
                id="filter-all",
                color="primary",
                outline=True,
                className="ms-2",
            ),
            dbc.Button(
                "Stocks",
                id="filter-stocks",
                color="primary",
                outline=True,
                className="ms-2",
            ),
            dbc.Button(
                "Options",
                id="filter-options",
                color="primary",
                outline=True,
                className="ms-2",
            ),
            dbc.Button(
                "Cash",
                id="filter-cash",
                color="primary",
                outline=True,
                className="ms-2",
            ),
        ],
        className="mb-3",
    )


def create_main_table() -> html.Div:
    """Create the main portfolio table"""
    return html.Div(
        [
            html.Div(
                id="portfolio-table",
                className="portfolio-table-container",
            ),
            # Add a Store to track sort state
            dcc.Store(id="sort-state", data={"column": "value", "direction": "desc"}),
        ]
    )


def create_position_modal() -> dbc.Modal:
    """Create the position details modal"""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle("Position Details"),
                close_button=True,
            ),
            dbc.ModalBody(id="position-modal-body"),
        ],
        id="position-modal",
        size="lg",
    )


def create_app(portfolio_file: str | None = None, _debug: bool = False) -> dash.Dash:
    """Create and configure the Dash application"""
    logger.debug("Initializing Dash application")

    # Create Dash app
    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://use.fontawesome.com/releases/v5.15.4/css/all.css",
        ],
        title="Folio",
        # Enable async callbacks
        use_pages=False,
        suppress_callback_exceptions=True,
    )

    # CSS files are automatically loaded from the assets folder
    # main.css imports all other CSS files and applies the theme

    # Use a simpler index_string without inline styles
    app.index_string = """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """

    # Store portfolio file path
    app.portfolio_file = portfolio_file
    logger.debug(f"Portfolio file path set to: {portfolio_file}")

    # Define layout
    app.layout = dbc.Container(
        [
            dcc.Location(id="url", refresh=False),  # Add URL component
            html.Div(html.H2("Folio"), className="app-header my-3"),
            create_upload_section(),  # Always show upload section
            # Wrap the main content in a loading component with gradient border
            html.Div(
                dcc.Loading(
                    id="main-loading",
                    type="circle",
                    children=[
                        html.Div(
                            [
                                # Add visualization dashboard section near the top
                                create_dashboard_section(),
                                # Add filters below visualizations
                                create_filters(),
                                # Move table to the end
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="fas fa-table me-2"
                                                    ),
                                                    html.Span("Portfolio Positions"),
                                                    html.I(
                                                        className="fas fa-chevron-down ms-2",
                                                        id="positions-collapse-icon",
                                                    ),
                                                ],
                                                id="positions-collapse-button",
                                                color="link",
                                                className="text-decoration-none text-dark p-0 d-flex align-items-center w-100 justify-content-between",
                                            ),
                                        ),
                                        dbc.Collapse(
                                            dbc.CardBody(
                                                create_main_table(),
                                            ),
                                            id="positions-collapse",
                                            is_open=True,  # Initially open
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                            ],
                            id="main-content",
                        )
                    ],
                ),
                className="gradient-border",
            ),
            create_pnl_modal(),
            # Empty state container (shown when no data is loaded)
            html.Div(id="empty-state-container"),
            # Add keyboard shortcut listener
            html.Div(id="keyboard-shortcut-listener"),
            # Premium AI Chat Interface
            create_premium_chat_component(),
            # AI Modal
            dbc.Modal(
                [
                    dbc.ModalHeader("AI Portfolio Advisor"),
                    dbc.ModalBody(
                        [
                            html.P("What would you like to know about your portfolio?"),
                            dbc.Textarea(
                                id="ai-query-input",
                                placeholder="Ask about your portfolio...",
                                rows=3,
                                className="mb-3",
                            ),
                            dbc.Button(
                                "Analyze",
                                id="analyze-portfolio-button",
                                color="primary",
                                className="mb-3",
                            ),
                            html.Div(id="ai-analysis-result"),
                        ]
                    ),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Close",
                            id="close-ai-modal",
                            className="ms-auto",
                            n_clicks=0,
                        )
                    ),
                ],
                id="ai-modal",
                size="lg",
                is_open=False,
            ),
            # Stores
            dcc.Store(id="portfolio-data"),
            dcc.Store(id="portfolio-summary"),  # Add portfolio summary store
            dcc.Store(id="portfolio-groups"),  # Add portfolio groups store
            dcc.Store(id="selected-position"),
            dcc.Store(id="loading-output"),  # Add loading output store
            dcc.Store(id="theme-store", storage_type="local"),  # Theme preference store
            dcc.Store(id="ai-analysis-data"),  # Store for AI analysis results
            dcc.Store(
                id="portfolio-table-active-cell"
            ),  # Store for tracking active cell in portfolio table
            # Add initial trigger
            dcc.Store(id="initial-trigger", data=True),
        ],
        fluid=True,
        className="px-4",
    )

    # Add clientside callback to ensure initial trigger fires
    app.clientside_callback(
        """
        function(pathname) {
            return true;
        }
        """,
        Output("initial-trigger", "data"),
        Input("url", "pathname"),
    )

    # Add clientside callback to log portfolio summary data
    app.clientside_callback(
        """
        function(data) {
            console.log("Portfolio Summary Data:", data);
            return window.dash_clientside.no_update;
        }
        """,
        Output("portfolio-summary", "data", allow_duplicate=True),
        Input("portfolio-summary", "data"),
        prevent_initial_call=True,
    )

    # Keyboard shortcut functionality removed as it was causing issues

    # Toggle upload section collapse
    @app.callback(
        [
            Output("upload-collapse", "is_open", allow_duplicate=True),
            Output("collapse-icon", "className"),
        ],
        [Input("upload-collapse-button", "n_clicks")],
        [State("upload-collapse", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_upload_collapse(n_clicks, is_open):
        """Toggle the upload section collapse state"""
        if n_clicks:
            # Toggle the collapse state
            new_state = not is_open
            # Update the icon based on the new state
            icon_class = (
                "fas fa-chevron-up ms-2" if new_state else "fas fa-chevron-down ms-2"
            )
            return new_state, icon_class
        return is_open, "fas fa-chevron-down ms-2"

    # Show/hide empty state based on portfolio data
    @app.callback(
        [
            Output("empty-state-container", "children"),
            Output("main-content", "style"),
            # Also collapse the upload section when data is loaded
            Output("upload-collapse", "is_open"),
        ],
        [Input("portfolio-groups", "data")],
    )
    def toggle_empty_state(groups_data):
        """Show empty state when no data is loaded and collapse upload section when data is loaded"""
        logger.debug(f"TOGGLE_EMPTY_STATE called with groups_data: {bool(groups_data)}")

        if not groups_data:
            # No data, show empty state, hide main content, keep upload open
            logger.debug(
                "TOGGLE_EMPTY_STATE: No data, showing empty state, hiding main content"
            )
            return create_empty_state(), {"display": "none"}, True
        else:
            # Data loaded, hide empty state, show main content, collapse upload
            logger.debug(
                "TOGGLE_EMPTY_STATE: Data loaded, hiding empty state, showing main content"
            )
            return None, {"display": "block"}, False

    # Handle sample portfolio loading
    @app.callback(
        [
            Output("upload-portfolio", "contents"),
            Output("upload-portfolio", "filename"),
        ],
        Input("load-sample", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_sample_portfolio(n_clicks):
        """Load a sample portfolio when the button is clicked"""
        logger.debug(f"LOAD_SAMPLE_PORTFOLIO: Button clicked: {n_clicks}")
        if n_clicks:
            logger.debug("LOAD_SAMPLE_PORTFOLIO: Processing sample portfolio")
            try:
                # First check if private portfolio exists for local debugging
                private_path = (
                    Path(os.getcwd()) / "private-data" / "portfolio-private.csv"
                )
                sample_path = Path(__file__).parent / "assets" / "sample-portfolio.csv"

                # Determine which file to use
                if private_path.exists():
                    logger.debug(f"Found private portfolio at: {private_path}")
                    portfolio_path = private_path
                    filename = "portfolio-private.csv"
                elif sample_path.exists():
                    logger.debug(f"Using sample portfolio at: {sample_path}")
                    portfolio_path = sample_path
                    filename = "sample-portfolio.csv"
                else:
                    logger.warning("Neither private nor sample portfolio found")
                    return None, None

                logger.debug(f"Loading portfolio from: {portfolio_path}")

                # Debug the file content
                with open(portfolio_path, encoding="utf-8") as f:
                    content = f.read()
                    logger.debug(
                        f"Portfolio content (first 100 chars): {content[:100]}"
                    )

                # Read the portfolio file
                with open(portfolio_path, "rb") as f:
                    file_content = f.read()
                    logger.debug(f"Read {len(file_content)} bytes from portfolio file")

                # Validate the file content
                # We'll sanitize it during the normal processing flow
                df = pd.read_csv(portfolio_path)

                # Check for any potentially dangerous content
                df = sanitize_dataframe(df)

                # Re-encode the sanitized dataframe
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_str = csv_buffer.getvalue()

                # Encode the content as base64 for the upload component
                content_type = "text/csv"
                content_string = base64.b64encode(csv_str.encode("utf-8")).decode(
                    "utf-8"
                )

                # Return both the contents and the filename
                return (
                    f"data:{content_type};base64,{content_string}",
                    filename,
                )
            except Exception as e:
                logger.error(f"Error loading sample portfolio: {e}", exc_info=True)
                return None, None
        return None, None

    @app.callback(
        [
            Output("portfolio-data", "data"),
            Output("portfolio-summary", "data"),
            Output("portfolio-groups", "data"),
            Output("loading-output", "data"),  # Changed from "children" to "data"
            Output("upload-status", "children"),
            Output(
                "portfolio-table-active-cell", "data"
            ),  # Changed from portfolio-table.active_cell
        ],
        [
            Input("initial-trigger", "data"),
            Input("url", "pathname"),
            Input("upload-portfolio", "contents"),
        ],
        [
            State("upload-portfolio", "filename"),
        ],
    )
    def update_portfolio_data(_initial_trigger, _pathname, contents, filename):
        """Update portfolio data when triggered"""
        try:
            logger.debug("Loading portfolio data...")
            ctx = dash.callback_context
            trigger_id = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
            logger.debug(f"Trigger: {trigger_id}")

            # Handle file upload if provided
            if contents and "upload-portfolio.contents" in trigger_id:
                try:
                    logger.debug(f"Processing uploaded file: {filename}")
                    # Validate and sanitize the CSV file
                    df, error = validate_csv_upload(contents, filename)
                    if error:
                        raise ValueError(error)

                    logger.debug(
                        f"Successfully read and validated {len(df)} rows from uploaded file {filename}"
                    )
                    status = html.Div(
                        f"Successfully loaded {filename}", className="text-success"
                    )
                except ValueError as e:
                    logger.error(f"CSV validation error: {e}")
                    error_msg = f"Error loading file: {e!s}"
                    error_div = html.Div(error_msg, className="text-danger")
                    return [], {}, [], error_msg, error_div, None
            elif app.portfolio_file:
                # Use default portfolio file
                try:
                    # Try to read the CSV file with standard settings
                    df = pd.read_csv(app.portfolio_file)
                except pd.errors.ParserError as e:
                    logger.warning(f"Parser error with standard settings: {e}")
                    # Try again with more flexible quoting to handle commas in option symbols
                    df = pd.read_csv(app.portfolio_file, quoting=3)  # QUOTE_NONE
                logger.debug(f"Successfully read {len(df)} rows from portfolio file")
                status = html.Div(
                    "Using default portfolio file", className="text-muted"
                )
            else:
                # No data available
                return (
                    [],
                    {},
                    [],
                    "",
                    html.Div("Please upload a portfolio file", className="text-muted"),
                    None,
                )

            # Process portfolio data with automatic price updates
            groups, summary, cash_like_positions = portfolio.process_portfolio_data(
                df, update_prices=True
            )
            logger.debug(
                f"Successfully processed {len(groups)} portfolio groups and {len(cash_like_positions)} cash-like positions"
            )
            # Continue with the original summary if price update fails

            # Convert to Dash-compatible format
            groups_data = [g.to_dict() for g in groups]
            summary_data = summary.to_dict()
            logger.debug(f"Summary data keys: {list(summary_data.keys())}")
            logger.debug(
                f"Portfolio estimate value: {summary_data.get('portfolio_estimate_value', 'NOT FOUND')}"
            )
            portfolio_data = df.to_dict("records")

            return portfolio_data, summary_data, groups_data, "", status, None

        except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
            # Handle expected data errors with user-friendly messages
            logger.error(f"Data error loading portfolio: {e}", exc_info=True)
            error_msg = f"Error loading portfolio: {e!s}"
            error_div = html.Div(error_msg, className="text-danger")
            return [], {}, [], error_msg, error_div, None
        except (ImportError, NameError, AttributeError, TypeError) as e:
            # These are programming errors that should be fixed, not handled
            logger.critical(f"Critical programming error: {e}", exc_info=True)
            error_msg = f"A critical error occurred. Please report this issue: {e!s}"
            error_div = html.Div(error_msg, className="text-danger")
            # Re-raise for development environments to see the full traceback
            if app.debug:
                raise
            return [], {}, [], error_msg, error_div, None
        except Exception as e:
            # Unexpected errors should be logged and reported
            logger.critical(
                f"Unexpected error updating portfolio data: {e}", exc_info=True
            )
            error_msg = f"An unexpected error occurred: {e!s}"
            error_div = html.Div(error_msg, className="text-danger")
            # Re-raise for development environments to see the full traceback
            if app.debug:
                raise
            return [], {}, [], error_msg, error_div, None

    # Register summary cards callbacks
    from .components.summary_cards import register_callbacks

    register_callbacks(app)

    # Register P&L chart callbacks
    register_pnl_callbacks(app)

    @app.callback(
        Output("portfolio-table", "children"),
        [
            Input("portfolio-groups", "data"),
            Input("search-input", "value"),
            Input("filter-all", "n_clicks"),
            Input("filter-stocks", "n_clicks"),
            Input("filter-options", "n_clicks"),
            Input("filter-cash", "n_clicks"),
            Input("sort-state", "data"),  # Add sort state input
        ],
        [State("portfolio-summary", "data")],  # Add portfolio summary as state
    )
    def update_portfolio_table(
        groups_data,
        search,
        _all_clicks,
        _stocks_clicks,
        _options_clicks,
        _cash_clicks,
        sort_state,
        summary_data,
    ):
        """Update portfolio table based on filters and sorting"""
        logger.debug("Updating portfolio table")
        try:
            if not groups_data:
                return html.Tr(
                    html.Td(
                        "No portfolio data available",
                        colSpan=6,
                        className="text-center",
                    )
                )

            # Convert data back to PortfolioGroup objects
            groups = []
            for g in groups_data:
                # Filter out attributes that don't exist in Position class
                stock_position = None
                if g["stock_position"]:
                    stock_position_data = g["stock_position"].copy()
                    # Remove attributes that don't exist in StockPosition class
                    if "sector" in stock_position_data:
                        stock_position_data.pop("sector")
                    if "is_cash_like" in stock_position_data:
                        stock_position_data.pop("is_cash_like")
                    if "position_type" in stock_position_data:
                        stock_position_data.pop("position_type")
                    stock_position = StockPosition(**stock_position_data)
                option_positions = [
                    OptionPosition(**opt) for opt in g["option_positions"]
                ]
                group = PortfolioGroup(
                    ticker=g["ticker"],
                    stock_position=stock_position,
                    option_positions=option_positions,
                    net_exposure=g["net_exposure"],
                    beta=g["beta"],
                    beta_adjusted_exposure=g["beta_adjusted_exposure"],
                    total_delta_exposure=g["total_delta_exposure"],
                    options_delta_exposure=g["options_delta_exposure"],
                )
                groups.append(group)

            # Determine which filter button was clicked
            ctx = dash.callback_context
            if ctx.triggered:
                button_id = ctx.triggered[0]["prop_id"].split(".")[0]
                logger.debug(f"Filter button clicked: {button_id}")
            else:
                button_id = "filter-all"  # Default to showing all

            # Get cash-like positions from summary data
            cash_like_positions = []
            if summary_data and "cash_like_positions" in summary_data:
                # Convert cash-like positions to PortfolioGroup objects
                for pos in summary_data["cash_like_positions"]:
                    # Create a StockPosition
                    stock_pos = StockPosition(
                        ticker=pos["ticker"],
                        quantity=pos["quantity"],
                        beta=pos["beta"],
                        market_exposure=pos.get(
                            "market_exposure", pos.get("market_value", 0.0)
                        ),  # Use market_exposure or fall back to market_value
                        beta_adjusted_exposure=pos["beta_adjusted_exposure"],
                    )

                    # Create a PortfolioGroup with just this stock position
                    cash_group = PortfolioGroup(
                        ticker=pos["ticker"],
                        stock_position=stock_pos,
                        option_positions=[],
                        net_exposure=pos.get(
                            "market_exposure", pos.get("market_value", 0.0)
                        ),
                        beta=pos["beta"],
                        beta_adjusted_exposure=pos["beta_adjusted_exposure"],
                        total_delta_exposure=0.0,
                        options_delta_exposure=0.0,
                    )
                    cash_like_positions.append(cash_group)

            # Apply filters based on button clicked
            filtered_groups = []
            if button_id == "filter-all":
                # Include all positions (including cash-like)
                filtered_groups = groups + cash_like_positions
            elif button_id == "filter-stocks":
                # Only include groups with stock positions (excluding cash-like)
                filtered_groups = [g for g in groups if g.stock_position]
            elif button_id == "filter-options":
                # Only include groups with option positions
                filtered_groups = [g for g in groups if g.option_positions]
            elif button_id == "filter-cash":
                # Only include cash-like positions
                filtered_groups = cash_like_positions
            else:
                # Default to all positions
                filtered_groups = groups + cash_like_positions

            # Apply search filter if provided
            if search:
                search = search.lower()
                filtered_groups = [
                    g
                    for g in filtered_groups
                    if (
                        (g.stock_position and search in g.stock_position.ticker.lower())
                        or any(
                            search in opt.ticker.lower() for opt in g.option_positions
                        )
                    )
                ]

            # Get sort information
            sort_column = sort_state.get("column", "value")
            sort_direction = sort_state.get("direction", "desc")
            sort_by = f"{sort_column}-{sort_direction}"

            # Create table with sorting applied
            return create_portfolio_table(filtered_groups, search, sort_by)

        except (ValueError, KeyError) as e:
            # Handle expected data errors
            logger.error(f"Data error updating portfolio table: {e}", exc_info=True)
            return html.Tr(
                html.Td(
                    f"Error loading portfolio data: {e!s}",
                    colSpan=6,
                    className="text-center text-danger",
                )
            )
        except (ImportError, NameError, AttributeError, TypeError) as e:
            # These are programming errors that should be fixed, not handled
            logger.critical(
                f"Critical programming error in table update: {e}", exc_info=True
            )
            # Re-raise for development environments to see the full traceback
            if app.debug:
                raise
            return html.Tr(
                html.Td(
                    f"A critical error occurred. Please report this issue: {e!s}",
                    colSpan=6,
                    className="text-center text-danger",
                )
            )
        except Exception as e:
            # Unexpected errors should be logged and reported
            logger.critical(
                f"Unexpected error updating portfolio table: {e}", exc_info=True
            )
            # Re-raise for development environments to see the full traceback
            if app.debug:
                raise
            return html.Tr(
                html.Td(
                    f"An unexpected error occurred: {e!s}",
                    colSpan=6,
                    className="text-center text-danger",
                )
            )

    # Position details modal callbacks removed - functionality integrated into P&L modal

    def _create_portfolio_group_from_data(position_data):
        """Helper function to create a PortfolioGroup from position data"""
        stock_position = None
        if position_data["stock_position"]:
            stock_position_data = position_data["stock_position"].copy()
            # Remove attributes that don't exist in Position class
            if "sector" in stock_position_data:
                stock_position_data.pop("sector")
            if "is_cash_like" in stock_position_data:
                stock_position_data.pop("is_cash_like")
            stock_position = StockPosition(**stock_position_data)

        option_positions = [
            OptionPosition(**opt) for opt in position_data["option_positions"]
        ]

        return PortfolioGroup(
            ticker=position_data["ticker"],
            stock_position=stock_position,
            option_positions=option_positions,
            net_exposure=position_data["net_exposure"],
            beta=position_data["beta"],
            beta_adjusted_exposure=position_data["beta_adjusted_exposure"],
            total_delta_exposure=position_data["total_delta_exposure"],
            options_delta_exposure=position_data["options_delta_exposure"],
        )

    # Old chat panel toggle callback removed - using premium chat component instead

    # Old dash-chat callback removed - using premium chat component instead

    # Add callback to handle column sorting
    @app.callback(
        Output("sort-state", "data"),
        [Input({"type": "sort-header", "column": ALL}, "n_clicks")],
        [State("sort-state", "data")],
    )
    @handle_callback_error(
        default_return=None, error_message="Error updating sort state"
    )
    def update_sort_state(_header_clicks, current_sort_state):
        """Update sort state when a column header is clicked"""
        ctx = dash.callback_context

        if not ctx.triggered:
            return current_sort_state

        trigger_id = ctx.triggered[0]["prop_id"]
        if not trigger_id or "sort-header" not in trigger_id:
            return current_sort_state

        # Extract column name from trigger ID (in format {"type":"sort-header","column":"value"}.n_clicks)

        column_data = json.loads(trigger_id.split(".")[0])
        clicked_column = column_data.get("column")

        if not clicked_column:
            logger.debug(f"No column found in trigger data: {column_data}")
            return current_sort_state

        # Update sort direction if same column clicked, otherwise reset to descending
        if clicked_column == current_sort_state.get("column"):
            new_direction = (
                "asc" if current_sort_state.get("direction") == "desc" else "desc"
            )
        else:
            new_direction = "desc"

        logger.debug(f"Sorting by {clicked_column} in {new_direction} order")
        return {"column": clicked_column, "direction": new_direction}

    # Add callbacks for collapsible chart sections
    @app.callback(
        [
            Output("dashboard-collapse", "is_open"),
            Output("dashboard-collapse-icon", "className"),
        ],
        [Input("dashboard-collapse-button", "n_clicks")],
        [State("dashboard-collapse", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_dashboard_collapse(n_clicks, is_open):
        """Toggle the dashboard section collapse state"""
        if n_clicks:
            # Toggle the collapse state
            new_state = not is_open
            # Update the icon based on the new state
            icon_class = (
                "fas fa-chevron-up ms-2" if new_state else "fas fa-chevron-down ms-2"
            )
            return new_state, icon_class
        return is_open, "fas fa-chevron-down ms-2"

    # Add callbacks for main section collapses
    for section in ["summary", "charts"]:

        @app.callback(
            [
                Output(f"{section}-collapse", "is_open"),
                Output(f"{section}-collapse-icon", "className"),
            ],
            [Input(f"{section}-collapse-button", "n_clicks")],
            [State(f"{section}-collapse", "is_open")],
            prevent_initial_call=True,
        )
        def toggle_chart_collapse(n_clicks, is_open, _section=section):
            """Toggle the chart section collapse state"""
            if n_clicks:
                # Toggle the collapse state
                new_state = not is_open
                # Update the icon based on the new state
                icon_class = (
                    "fas fa-chevron-up ms-2"
                    if new_state
                    else "fas fa-chevron-down ms-2"
                )
                return new_state, icon_class
            return is_open, "fas fa-chevron-down ms-2"

    # Add callback for positions collapse
    @app.callback(
        [
            Output("positions-collapse", "is_open"),
            Output("positions-collapse-icon", "className"),
        ],
        [Input("positions-collapse-button", "n_clicks")],
        [State("positions-collapse", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_positions_collapse(n_clicks, is_open):
        """Toggle the positions section collapse state"""
        if n_clicks:
            # Toggle the collapse state
            new_state = not is_open
            # Update the icon based on the new state
            icon_class = (
                "fas fa-chevron-up ms-2" if new_state else "fas fa-chevron-down ms-2"
            )
            return new_state, icon_class
        return is_open, "fas fa-chevron-down ms-2"

    # Register chart callbacks
    register_chart_callbacks(app)

    # Register premium chat callbacks
    register_premium_chat_callbacks(app)  # This is now an alias for register_callbacks

    return app


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Folio - Portfolio Dashboard")
    parser.add_argument(
        "--portfolio",
        type=str,
        help="Path to portfolio CSV file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to run the server on",
    )
    args = parser.parse_args()

    # Validate portfolio file if provided
    portfolio_file = None
    if args.portfolio:
        portfolio_file = Path(args.portfolio)
        if not portfolio_file.exists():
            logger.error(f"Portfolio file not found: {portfolio_file}")
            return 1
        portfolio_file = str(portfolio_file)

    # Initialize and run app
    app = AppHolder.init_app(portfolio_file, args.debug)

    # Display a helpful message about where to access the app
    is_docker = os.path.exists("/.dockerenv")
    is_huggingface = (
        os.environ.get("HF_SPACE") == "1" or os.environ.get("SPACE_ID") is not None
    )

    if is_huggingface:
        logger.info("\n\n🚀 Folio is running on Hugging Face Spaces!")
        logger.info("📊 Access the dashboard at the URL provided by Hugging Face\n")
    elif is_docker and args.host == "0.0.0.0":
        logger.info("\n\n🚀 Folio is running inside a Docker container!")
        logger.info(f"📊 Access the dashboard at: http://localhost:{args.port}")
        logger.info(
            f"💻 (The app is bound to {args.host}:{args.port} inside the container)\n"
        )
    else:
        logger.info("\n\n🚀 Folio is running!")
        logger.info(f"📊 Access the dashboard at: http://localhost:{args.port}\n")

    app.run(debug=args.debug, port=args.port, host=args.host)
    return 0


# Create a class to hold the app instance
class AppHolder:
    """Class to hold the app instance"""

    app = None
    server = None

    @classmethod
    def init_app(cls, portfolio_file: str | None = None, debug: bool = False):
        """Initialize the app for WSGI servers"""
        if cls.app is None:
            cls.app = create_app(portfolio_file, debug)
            cls.server = cls.app.server
        return cls.app


# Create the app instance for Uvicorn to use
app = AppHolder.init_app()
server = AppHolder.server

if __name__ == "__main__":
    sys.exit(main())
