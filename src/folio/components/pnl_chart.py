"""
P&L chart component for position visualization.

This module provides components for visualizing position P&L across different price points.
It includes a modal for displaying P&L charts and the necessary callbacks for interactivity.
"""

from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback_context, dcc, html

from ..data_model import OptionPosition, PortfolioGroup, StockPosition
from ..formatting import format_currency
from ..logger import logger
from ..pnl import calculate_strategy_pnl, determine_price_range, summarize_strategy_pnl
from .position_details import create_position_details


def create_pnl_chart(
    pnl_data: dict[str, Any],
    summary: dict[str, Any],
    current_price: float,
    ticker: str,
    mode: str = "default",  # noqa: ARG001 - used in layout title
) -> go.Figure:
    """
    Create a Plotly figure for P&L visualization.

    Args:
        pnl_data: P&L data from calculate_strategy_pnl
        summary: Summary data from summarize_strategy_pnl
        current_price: Current price of the underlying
        ticker: Ticker symbol
        mode: Mode used for P&L calculation ("default" or "cost_basis")

    Returns:
        Plotly figure object
    """
    # Create figure
    fig = go.Figure()

    # Plot combined P&L
    fig.add_trace(
        go.Scatter(
            x=pnl_data["price_points"],
            y=pnl_data["pnl_values"],
            mode="lines",
            name=f"{ticker} P&L",
            line=dict(color="#1f77b4", width=3),
        )
    )

    # Plot individual position P&Ls (hidden by default)
    if "individual_pnls" in pnl_data:
        for i, pos_pnl in enumerate(pnl_data["individual_pnls"]):
            position_data = pos_pnl.get("position", {})
            pos_type = position_data.get("position_type", "unknown")
            pos_ticker = position_data.get("ticker", f"Position {i + 1}")

            # Create a more descriptive label for options
            if pos_type == "option":
                option_type = position_data.get("option_type", "")
                strike = position_data.get("strike", 0)
                pos_desc = f"{pos_ticker} {option_type} {strike}"
            else:
                pos_desc = pos_ticker

            fig.add_trace(
                go.Scatter(
                    x=pos_pnl["price_points"],
                    y=pos_pnl["pnl_values"],
                    mode="lines",
                    name=pos_desc,
                    line=dict(dash="dash", width=1.5),
                    opacity=0.7,
                    visible="legendonly",  # Hidden by default, can be toggled in legend
                )
            )

    # Add reference lines
    fig.add_hline(
        y=0,
        line=dict(color="red", width=1, dash="solid"),
        opacity=0.5,
    )

    # Add current price line and annotation
    fig.add_vline(
        x=current_price,
        line=dict(color="green", width=1, dash="dash"),
        opacity=0.7,
    )

    # Add vertical line for current price without text label

    # Add breakeven points (vertical lines only, no text)
    for bp in summary["breakeven_points"]:
        fig.add_vline(
            x=bp,
            line=dict(color="orange", width=1, dash="dot"),
            opacity=0.5,
        )

    # Add max profit/loss points
    max_profit = summary["max_profit"]
    max_profit_price = summary["max_profit_price"]
    fig.add_trace(
        go.Scatter(
            x=[max_profit_price],
            y=[max_profit],
            mode="markers",
            marker=dict(color="green", size=10),
            name="Max Profit",
            showlegend=False,
        )
    )
    # Add marker for max profit with infinity symbol if unbounded
    unbounded_profit = summary.get("unbounded_profit", False)

    # If profit is unbounded, add an infinity arrow pointing up/right
    if unbounded_profit:
        # Add arrow pointing to infinity
        fig.add_annotation(
            x=max_profit_price,
            y=max_profit,
            text="↗∞",  # Up-right arrow with infinity symbol
            showarrow=False,
            font=dict(size=16, color="green"),
            align="center",
        )
    # Otherwise, just show the marker without text

    max_loss = summary["max_loss"]
    max_loss_price = summary["max_loss_price"]
    fig.add_trace(
        go.Scatter(
            x=[max_loss_price],
            y=[max_loss],
            mode="markers",
            marker=dict(color="red", size=10),
            name="Max Loss",
            showlegend=False,
        )
    )
    # Add marker for max loss with infinity symbol if unbounded
    unbounded_loss = summary.get("unbounded_loss", False)

    # If loss is unbounded, add an infinity arrow pointing down/right
    if unbounded_loss:
        # Add arrow pointing to infinity
        fig.add_annotation(
            x=max_loss_price,
            y=max_loss,
            text="↘∞",  # Down-right arrow with infinity symbol
            showarrow=False,
            font=dict(size=16, color="red"),
            align="center",
        )
    # Otherwise, just show the marker without text

    # Add current P&L
    current_pnl = summary["current_pnl"]
    fig.add_trace(
        go.Scatter(
            x=[current_price],
            y=[current_pnl],
            mode="markers",
            marker=dict(color="gold", size=10),
            name="Current Price",
            showlegend=False,
        )
    )
    # No text annotation for current P&L, just the marker

    # Set layout
    fig.update_layout(
        title=f"{ticker} P&L Analysis",
        xaxis_title="Price",
        yaxis_title="P&L ($)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=500,
    )

    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgrey")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgrey")

    return fig


def create_pnl_modal() -> dbc.Modal:
    """
    Create a modal for displaying position analysis with P&L charts and details.

    Returns:
        dbc.Modal: The modal component
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle("Position Analysis"),
                close_button=True,
            ),
            dbc.ModalBody([
                # Tabs for different sections
                dbc.Tabs(
                    [
                        # P&L Analysis Tab
                        dbc.Tab(
                            [
                                # Mode toggle removed
                                # Summary information
                                html.Div(id="pnl-summary", className="mb-3"),
                                # Store for current ticker (for mode toggling)
                                dcc.Store(
                                    id="pnl-current-ticker", storage_type="memory"
                                ),
                                # Loading spinner for the chart
                                dbc.Spinner(
                                    dcc.Graph(
                                        id="pnl-chart",
                                        config={
                                            "displayModeBar": True,
                                            "responsive": True,
                                        },
                                        className="dash-chart",
                                    ),
                                    color="primary",
                                    type="border",
                                    fullscreen=False,
                                ),
                            ],
                            label="P&L Analysis",
                            tab_id="tab-pnl",
                        ),
                        # Position Details Tab
                        dbc.Tab(
                            html.Div(id="pnl-position-details", className="mt-2"),
                            label="Position Details",
                            tab_id="tab-details",
                        ),
                    ],
                    id="position-tabs",
                    active_tab="tab-pnl",
                ),
            ]),
            dbc.ModalFooter(
                dbc.Button(
                    "Close",
                    id="close-pnl-modal",
                    className="ms-auto",
                ),
            ),
        ],
        id="pnl-modal",
        size="xl",
    )


def create_pnl_summary(summary: dict[str, Any], mode: str) -> html.Div:  # noqa: ARG001 - mode param kept for API compatibility
    """
    Create a summary of P&L metrics.

    Args:
        summary: Summary data from summarize_strategy_pnl
        mode: Mode used for P&L calculation ("default" or "cost_basis")

    Returns:
        html.Div: The summary component
    """

    # Format breakeven points
    if summary["breakeven_points"]:
        if len(summary["breakeven_points"]) <= 2:
            be_text = ", ".join([f"${bp:.2f}" for bp in summary["breakeven_points"]])
        else:
            be_text = f"${summary['breakeven_points'][0]:.2f}, ${summary['breakeven_points'][-1]:.2f}"
    else:
        be_text = "None"

    return html.Div([
        dbc.Row([
            # P&L display removed
            dbc.Col(
                [
                    dbc.Card([
                        dbc.CardBody(
                            [
                                html.H6(
                                    "Max Profit",
                                    className="card-subtitle mb-1 text-muted",
                                ),
                                html.H3(
                                    "Unlimited"
                                    if summary.get("unbounded_profit")
                                    else format_currency(summary["max_profit"]),
                                    className="card-title mb-0 text-success",
                                ),
                                html.Small(
                                    ""
                                    if summary.get("unbounded_profit")
                                    else f"at ${summary['max_profit_price']:.2f}",
                                    className="text-muted",
                                ),
                            ],
                            className="p-2 text-center",
                        )
                    ]),
                ],
                width=4,
            ),
            dbc.Col(
                [
                    dbc.Card([
                        dbc.CardBody(
                            [
                                html.H6(
                                    "Max Loss",
                                    className="card-subtitle mb-1 text-muted",
                                ),
                                html.H3(
                                    "Unlimited"
                                    if summary.get("unbounded_loss")
                                    else format_currency(summary["max_loss"]),
                                    className="card-title mb-0 text-danger",
                                ),
                                html.Small(
                                    ""
                                    if summary.get("unbounded_loss")
                                    else f"at ${summary['max_loss_price']:.2f}",
                                    className="text-muted",
                                ),
                            ],
                            className="p-2 text-center",
                        )
                    ]),
                ],
                width=4,
            ),
            dbc.Col(
                [
                    dbc.Card([
                        dbc.CardBody(
                            [
                                html.H6(
                                    "Break-even",
                                    className="card-subtitle mb-1 text-muted",
                                ),
                                html.H3(
                                    be_text,
                                    className="card-title mb-0",
                                ),
                            ],
                            className="p-2 text-center",
                        )
                    ]),
                ],
                width=4,
            ),
        ]),
    ])


def register_callbacks(app):
    """
    Register callbacks for the P&L chart component.

    Args:
        app: The Dash app
    """

    @app.callback(
        [
            Output("pnl-modal", "is_open"),
            Output("pnl-chart", "figure"),
            Output("pnl-summary", "children"),
            Output("pnl-position-details", "children"),
            # Mode toggle outputs removed but kept as no-update for backward compatibility
            Output("pnl-current-ticker", "data"),
            Output("position-tabs", "active_tab"),
        ],
        [
            Input({"type": "position-pnl", "index": ALL}, "n_clicks"),
            Input("close-pnl-modal", "n_clicks"),
        ],
        [
            State("portfolio-groups", "data"),
            State("pnl-modal", "is_open"),
            State("pnl-current-ticker", "data"),
        ],
        # Prevent the callback from firing when the app first loads
        prevent_initial_call=True,
    )
    def toggle_pnl_modal(
        btn_clicks,
        close_clicks,  # noqa: ARG001 - required by Dash
        groups_data,
        is_open,
        current_ticker,
    ):
        """Toggle P&L modal and update chart."""
        ctx = callback_context
        if not ctx.triggered:
            return (
                False,
                {},
                html.Div(),
                html.Div(),
                None,
                "tab-pnl",
            )

        trigger_id = ctx.triggered[0]["prop_id"]
        logger.debug(f"PNL modal trigger: {trigger_id}")

        # Handle close button
        if "close-pnl-modal" in trigger_id:
            return (
                False,
                {},
                html.Div(),
                html.Div(),
                None,  # Clear the current ticker
                "tab-pnl",  # Reset to P&L tab
            )

        # Mode toggle removed
        use_cost_basis = False  # Always use default mode

        # Initialize variables for position data
        ticker = None
        position_data = None

        # Handle position button click
        if "position-pnl" in trigger_id and any(
            clicks for clicks in btn_clicks if clicks
        ):
            # Extract ticker from button ID
            button_id = trigger_id.split(".")[0]
            ticker = button_id.split('"index":"')[1].split('"')[0]

            # Find matching group by ticker
            for group_data in groups_data:
                group_ticker = group_data["ticker"]
                if group_ticker == ticker:
                    position_data = group_data
                    break

        # If modal is already open and we're just changing modes, we need to preserve the modal state
        elif is_open and (
            "pnl-mode-default" in trigger_id or "pnl-mode-cost-basis" in trigger_id
        ):
            # Use the stored ticker to find the position data
            ticker = current_ticker

            if ticker:
                # Find matching group by ticker
                for group_data in groups_data:
                    group_ticker = group_data["ticker"]
                    if group_ticker == ticker:
                        position_data = group_data
                        break

            # If we still don't have position data, show an error
            if not position_data:
                logger.error(
                    f"Cannot determine which position to display when changing modes. Current ticker: {ticker}"
                )
                return (
                    True,  # Keep modal open
                    dash.no_update,  # Keep current chart
                    html.Div(
                        "Error: Cannot determine which position to display. Please close and reopen the modal.",
                        className="alert alert-danger",
                    ),
                    dash.no_update,  # Keep current position details
                    ticker,  # Keep the current ticker
                    dash.no_update,  # Keep current tab
                )

        # Check if we have position data
        if not position_data:
            # If we're trying to open the modal but have no data, show an error
            if "position-pnl" in trigger_id:
                # Only log if ticker is not None to avoid spurious warnings
                if ticker is not None:
                    logger.warning(f"No position data found for ticker {ticker}")
                return (
                    False,
                    {},
                    html.Div("No position data found"),
                    html.Div(),
                    None,  # Clear the ticker
                    "tab-pnl",  # Reset to P&L tab
                )
            # If the modal isn't already open, just keep it closed
            elif not is_open:
                return (
                    False,
                    {},
                    html.Div(),
                    html.Div(),
                    None,  # Clear the ticker
                    "tab-pnl",  # Reset to P&L tab
                )

        # Convert position data to objects
        if position_data:
            # Create stock position if it exists
            stock_position = None
            if position_data["stock_position"]:
                stock_data = position_data["stock_position"]
                stock_position = StockPosition(
                    ticker=stock_data["ticker"],
                    quantity=stock_data["quantity"],
                    price=stock_data["price"],
                    beta=stock_data["beta"],
                    market_exposure=stock_data["market_exposure"],
                    beta_adjusted_exposure=stock_data["beta_adjusted_exposure"],
                    cost_basis=stock_data.get("cost_basis", stock_data["price"]),
                )

            # Create option positions if they exist
            option_positions = []
            for opt_data in position_data["option_positions"]:
                option_position = OptionPosition(
                    ticker=opt_data["ticker"],
                    position_type="option",
                    quantity=opt_data["quantity"],
                    strike=opt_data["strike"],
                    expiry=opt_data["expiry"],
                    option_type=opt_data["option_type"],
                    price=opt_data["price"],
                    delta=opt_data["delta"],
                    delta_exposure=opt_data["delta_exposure"],
                    notional_value=opt_data["notional_value"],
                    beta=opt_data.get("beta", 1.0),
                    beta_adjusted_exposure=opt_data["beta_adjusted_exposure"],
                    market_exposure=opt_data["market_exposure"],
                    underlying_beta=opt_data.get("underlying_beta", 1.0),
                    cost_basis=opt_data.get("cost_basis", opt_data["price"]),
                )
                option_positions.append(option_position)

            # Create portfolio group
            group = PortfolioGroup(
                ticker=position_data["ticker"],
                stock_position=stock_position,
                option_positions=option_positions,
                net_exposure=position_data["net_exposure"],
                beta=position_data["beta"],
                beta_adjusted_exposure=position_data["beta_adjusted_exposure"],
                total_delta_exposure=position_data["total_delta_exposure"],
                options_delta_exposure=position_data["options_delta_exposure"],
            )

            # Get all positions
            all_positions = []
            if group.stock_position:
                all_positions.append(group.stock_position)
            all_positions.extend(group.option_positions)

            # Get current price
            current_price = None
            if group.stock_position:
                current_price = group.stock_position.price
            elif group.option_positions:
                # Try to estimate underlying price from notional value and quantity
                first_option = group.option_positions[0]
                if hasattr(first_option, "notional_value") and hasattr(
                    first_option, "quantity"
                ):
                    # Notional value is 100 * underlying price * abs(quantity)
                    abs_quantity = abs(first_option.quantity)
                    if abs_quantity > 0:
                        current_price = first_option.notional_value / (
                            100 * abs_quantity
                        )

            if current_price is None:
                # Fallback to a default value
                current_price = 100.0
                logger.warning(
                    f"Could not determine current price for {group.ticker}, using default: ${current_price:.2f}"
                )

            # Calculate price range
            price_range = determine_price_range(all_positions, current_price)

            # Calculate P&L
            pnl_data = calculate_strategy_pnl(
                all_positions,
                price_range=price_range,
                num_points=100,
                use_cost_basis=use_cost_basis,
            )

            # Generate summary
            summary = summarize_strategy_pnl(pnl_data, current_price)

            # Create chart
            fig = create_pnl_chart(
                pnl_data,
                summary,
                current_price,
                group.ticker,
                mode="cost_basis" if use_cost_basis else "default",
            )

            # Create summary
            summary_component = create_pnl_summary(
                summary,
                mode="cost_basis" if use_cost_basis else "default",
            )

            # Create position details
            position_details = create_position_details(group)

            return (
                True,
                fig,
                summary_component,
                position_details,
                ticker,  # Store the current ticker
                "tab-pnl",  # Always show P&L tab when opening
            )

        # If we get here, something went wrong
        return (
            False,
            {},
            html.Div("Error loading P&L data"),
            html.Div(),
            None,  # Clear the ticker
            "tab-pnl",  # Reset to P&L tab
        )
