"""Summary cards component for the Folio dashboard.

This module provides the summary cards component for displaying portfolio metrics
at the top of the dashboard. It includes functions for creating the cards and
formatting the values.
"""

import dash_bootstrap_components as dbc
from dash import Input, Output, html

from ..formatting import format_currency
from ..logger import logger
from ..portfolio import calculate_beta_adjusted_net_exposure


def error_values():
    """Return error values for summary cards.

    This function provides a consistent set of error values for the summary cards
    when data is missing or invalid.

    Returns:
        Tuple of error formatted values for all summary cards
    """
    return (
        "Error",  # Portfolio Value
        "Error",  # Net Exposure
        "Data missing",  # Net Exposure Percent
        "Error",  # Beta-Adjusted Net Exposure
        "Data missing",  # Beta-Adjusted Net Exposure Percent
        "Error",  # Long Exposure
        "Data missing",  # Long Exposure Percent
        "Error",  # Short Exposure
        "Data missing",  # Short Exposure Percent
        "Error",  # Options Exposure
        "Data missing",  # Options Exposure Percent
        "Error",  # Cash Value
        "Data missing",  # Cash Percent
    )


def format_summary_card_values(summary_data):
    """Format summary card values from summary data.

    This function takes the portfolio summary data and formats it for display
    in the summary cards. It handles missing values and calculates derived metrics.

    Args:
        summary_data: Dictionary containing portfolio summary data

    Returns:
        Tuple of formatted values for all summary cards
    """
    logger.debug(f"Formatting summary cards with data: {summary_data}")

    # Return error values if summary_data is invalid
    if not summary_data or not isinstance(summary_data, dict):
        logger.error(f"Invalid summary data: {type(summary_data)}")
        return error_values()

    # Check for required keys
    required_keys = [
        "net_market_exposure",
        "portfolio_beta",
        "long_exposure",
        "short_exposure",
        "options_exposure",
        "cash_like_value",
    ]
    missing_keys = [key for key in required_keys if key not in summary_data]

    # Try to fix missing portfolio_estimate_value
    if "portfolio_estimate_value" not in summary_data:
        if "net_market_exposure" in summary_data and "cash_like_value" in summary_data:
            net_market_exposure = summary_data.get("net_market_exposure", 0.0)
            cash_like_value = summary_data.get("cash_like_value", 0.0)
            summary_data["portfolio_estimate_value"] = (
                net_market_exposure + cash_like_value
            )
            logger.debug(
                f"Calculated portfolio_estimate_value: {summary_data['portfolio_estimate_value']}"
            )
        else:
            missing_keys.append("portfolio_estimate_value")

    # Return error values if any required keys are still missing
    if missing_keys:
        logger.error(f"Missing required keys in summary data: {missing_keys}")
        return error_values()

    # Helper function to get exposure value (supports both total_exposure and total_value field names)
    def get_exposure_value(exposure_dict):
        if not isinstance(exposure_dict, dict):
            return 0.0
        return exposure_dict.get(
            "total_exposure", exposure_dict.get("total_value", 0.0)
        )

    # Extract values with defaults
    portfolio_estimate_value = summary_data.get("portfolio_estimate_value", 0.0)
    net_market_exposure = summary_data.get("net_market_exposure", 0.0)
    cash_like_value = summary_data.get("cash_like_value", 0.0)

    # Get exposure values
    long_exposure = summary_data.get("long_exposure", {})
    short_exposure = summary_data.get("short_exposure", {})
    options_exposure = summary_data.get("options_exposure", {})

    # Get total exposure values
    long_total_exposure = get_exposure_value(long_exposure)
    short_total_exposure = get_exposure_value(short_exposure)
    options_total_exposure = get_exposure_value(options_exposure)

    # Get beta-adjusted values
    long_total_beta_adjusted = long_exposure.get("total_beta_adjusted", 0.0)
    short_total_beta_adjusted = short_exposure.get("total_beta_adjusted", 0.0)

    # Calculate beta-adjusted net exposure using the utility function
    # Note: options_total_beta_adjusted is already included in long/short, so we don't add it separately
    # Note: Cash-like positions have beta of 0, so they don't contribute to beta-adjusted exposure
    beta_adjusted_net_exposure = calculate_beta_adjusted_net_exposure(
        long_total_beta_adjusted, short_total_beta_adjusted
    )

    # Calculate percentages of portfolio value
    if portfolio_estimate_value > 0:
        net_exposure_percent = (net_market_exposure / portfolio_estimate_value) * 100
        beta_adjusted_percent = (
            beta_adjusted_net_exposure / portfolio_estimate_value
        ) * 100
        long_exposure_percent = (long_total_exposure / portfolio_estimate_value) * 100
        short_exposure_percent = (
            abs(short_total_exposure) / portfolio_estimate_value
        ) * 100
        options_exposure_percent = (
            abs(options_total_exposure) / portfolio_estimate_value
        ) * 100
        cash_percent = (cash_like_value / portfolio_estimate_value) * 100
    else:
        net_exposure_percent = 0
        beta_adjusted_percent = 0
        long_exposure_percent = 0
        short_exposure_percent = 0
        options_exposure_percent = 0
        cash_percent = 0

    # Format the percentages
    net_exposure_percent_str = f"{net_exposure_percent:.1f}% of portfolio"
    beta_adjusted_percent_str = f"{beta_adjusted_percent:.1f}% of portfolio"
    long_exposure_percent_str = f"{long_exposure_percent:.1f}% of portfolio"
    short_exposure_percent_str = f"{short_exposure_percent:.1f}% of portfolio"
    options_exposure_percent_str = f"{options_exposure_percent:.1f}% of portfolio"
    cash_percent_str = f"{cash_percent:.1f}% of portfolio"

    # Format the values for display
    try:
        return (
            # Portfolio Value
            format_currency(portfolio_estimate_value),
            # Net Exposure
            format_currency(net_market_exposure),
            net_exposure_percent_str,
            # Beta-Adjusted Net Exposure
            format_currency(beta_adjusted_net_exposure),
            beta_adjusted_percent_str,
            # Long Exposure
            format_currency(long_total_exposure),
            long_exposure_percent_str,
            # Short Exposure
            format_currency(short_total_exposure),
            short_exposure_percent_str,
            # Options Exposure
            format_currency(options_total_exposure),
            options_exposure_percent_str,
            # Cash & Equivalents
            format_currency(cash_like_value),
            cash_percent_str,
        )
    except Exception as e:
        logger.error(f"Error formatting values: {e}")
        return error_values()


def create_portfolio_value_card():
    """Create the portfolio value card."""
    # Create the portfolio value component
    portfolio_value = html.H5(
        id="portfolio-value",
        className="card-title text-primary",
        children="$0.00",  # Default value
    )

    # Create the card with the portfolio value component nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Portfolio Value",
                        className="card-subtitle",
                    ),
                    portfolio_value,  # Nest the component here
                ]),
                className="mb-3",
                id="portfolio-value-card",
            ),
            dbc.Tooltip(
                "Total value of your portfolio including all positions and cash. This represents your total investment and is used to calculate percentage allocations.",
                target="portfolio-value-card",
                placement="top",
            ),
        ],
        width=3,
    )


def create_net_exposure_card():
    """Create the net exposure card."""
    # Create the components
    total_value = html.H5(
        id="total-value",
        className="card-title text-primary",
        children="$0.00",  # Default value
    )

    total_value_percent = html.P(
        id="total-value-percent",
        className="card-text text-muted",
        children="",  # Default value
    )

    # Create the card with the components nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Net Exposure",
                        className="card-subtitle",
                    ),
                    total_value,  # Nest the component here
                    total_value_percent,  # Nest the component here
                ]),
                className="mb-3",
                id="total-value-card",
            ),
            dbc.Tooltip(
                "Net market exposure (Long - Short) showing your directional bias. A positive value indicates net long exposure, while negative indicates net short. Use this to understand your overall market stance.",
                target="total-value-card",
                placement="top",
            ),
        ],
        width=4,  # Adjusted width for new layout
    )


def create_long_exposure_card():
    """Create the long exposure card."""
    # Create the components
    long_exposure = html.H5(
        id="long-exposure",
        className="card-title text-success",
        children="$0.00",  # Default value
    )

    long_exposure_percent = html.P(
        id="long-exposure-percent",
        className="card-text text-muted",
        children="",  # Default value
    )

    # Create the card with the components nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Long Exposure",
                        className="card-subtitle",
                    ),
                    long_exposure,  # Nest the component here
                    long_exposure_percent,  # Nest the component here
                ]),
                className="mb-3",
                id="long-exposure-card",
            ),
            dbc.Tooltip(
                "Total long market exposure from stocks and options (not beta-adjusted). This shows your total bullish positioning and is used to calculate your gross exposure.",
                target="long-exposure-card",
                placement="top",
            ),
        ],
        width=4,  # Adjusted width for new layout
    )


def create_short_exposure_card():
    """Create the short exposure card."""
    # Create the components
    short_exposure = html.H5(
        id="short-exposure",
        className="card-title text-danger",
        children="$0.00",  # Default value
    )

    short_exposure_percent = html.P(
        id="short-exposure-percent",
        className="card-text text-muted",
        children="",  # Default value
    )

    # Create the card with the components nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Short Exposure",
                        className="card-subtitle",
                    ),
                    short_exposure,  # Nest the component here
                    short_exposure_percent,  # Nest the component here
                ]),
                className="mb-3",
                id="short-exposure-card",
            ),
            dbc.Tooltip(
                "Total short market exposure from stocks and options (not beta-adjusted). This shows your total bearish positioning and helps measure your hedging level.",
                target="short-exposure-card",
                placement="top",
            ),
        ],
        width=4,  # Adjusted width for new layout
    )


def create_options_exposure_card():
    """Create the options exposure card."""
    # Create the components
    options_exposure = html.H5(
        id="options-exposure",
        className="card-title text-info",
        children="$0.00",  # Default value
    )

    options_exposure_percent = html.P(
        id="options-exposure-percent",
        className="card-text text-muted",
        children="",  # Default value
    )

    # Create the card with the components nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Options Exposure",
                        className="card-subtitle",
                    ),
                    options_exposure,  # Nest the component here
                    options_exposure_percent,  # Nest the component here
                ]),
                className="mb-3",
                id="options-exposure-card",
            ),
            dbc.Tooltip(
                "Net delta-adjusted exposure from all options (not beta-adjusted). This shows how your options positions affect your overall market exposure, with each option weighted by its delta.",
                target="options-exposure-card",
                placement="top",
            ),
        ],
        width=4,  # Adjusted width for new layout
    )


def create_cash_card():
    """Create the cash card."""
    # Create the components
    cash_like_value = html.H5(
        id="cash-like-value",
        className="card-title text-secondary",
        children="$0.00",  # Default value
    )

    cash_like_percent = html.P(
        id="cash-like-percent",
        className="card-text text-muted",
        children="",  # Default value
    )

    # Create the card with the components nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Cash & Equivalents",
                        className="card-subtitle",
                    ),
                    cash_like_value,  # Nest the component here
                    cash_like_percent,  # Nest the component here
                ]),
                className="mb-3",
                id="cash-like-card",
            ),
            dbc.Tooltip(
                "Total value of cash and cash-equivalent positions (money market funds, T-bills, etc.). This represents your defensive positioning and available buying power.",
                target="cash-like-card",
                placement="top",
            ),
        ],
        width=4,  # Adjusted width for new layout
    )


def create_beta_adjusted_exposure_card():
    """Create the beta-adjusted net exposure card."""
    # Create the components
    beta_adjusted_exposure = html.H5(
        id="beta-adjusted-exposure",
        className="card-title text-primary",
        children="$0.00",  # Default value
    )

    beta_adjusted_percent = html.P(
        id="beta-adjusted-percent",
        className="card-text text-muted",
        children="",  # Default value
    )

    # Create the card with the component nested inside it
    return dbc.Col(
        [
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "Beta-Adjusted Net Exposure",
                        className="card-subtitle",
                    ),
                    beta_adjusted_exposure,  # Nest the component here
                    beta_adjusted_percent,  # Nest the component here
                ]),
                className="mb-3",
                id="beta-adjusted-exposure-card",
            ),
            dbc.Tooltip(
                "Net exposure adjusted for each position's beta, showing true market risk. This risk-adjusted measure accounts for the fact that high-beta stocks have more market impact than low-beta stocks of the same value.",
                target="beta-adjusted-exposure-card",
                placement="top",
            ),
        ],
        width=4,  # Adjusted width for new layout
    )


def create_summary_cards():
    """Create the header section with summary cards.

    Returns:
        dbc.Card: A card containing all summary cards
    """
    logger.debug("Creating summary cards")

    # Create all the cards
    net_exposure_card = create_net_exposure_card()
    beta_adjusted_exposure_card = create_beta_adjusted_exposure_card()
    long_exposure_card = create_long_exposure_card()
    short_exposure_card = create_short_exposure_card()
    options_exposure_card = create_options_exposure_card()
    cash_card = create_cash_card()

    # Create the portfolio value banner card
    portfolio_value_banner = dbc.Card(
        dbc.CardBody([
            html.Div(
                [
                    html.H4(
                        [
                            html.Span(
                                "Total Portfolio Value: ", className="text-muted"
                            ),
                            html.Span(
                                id="portfolio-value",
                                children="$0.00",
                                className="text-primary",
                            ),
                        ],
                        className="text-center mb-0",
                    ),
                ],
                className="d-flex justify-content-center",
            ),
        ]),
        className="mb-3",
        style={
            "background-color": "#f8f9fa"
        },  # Light gray background to make it stand out
    )

    # Create the summary card with all the components nested inside it
    return dbc.Card(
        dbc.CardBody([
            html.H4("Portfolio Summary", className="text-center mb-3"),
            portfolio_value_banner,
            dbc.Row(
                [
                    net_exposure_card,
                    beta_adjusted_exposure_card,
                    long_exposure_card,
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    short_exposure_card,
                    options_exposure_card,
                    cash_card,
                ],
                className="mb-3",
            ),
        ]),
        className="mb-3",
        id="summary-card",
    )


def register_callbacks(app):
    """Register callbacks for summary cards.

    Args:
        app: The Dash app
    """
    logger.debug("Registering summary cards callbacks")
    # Debug logging for callback registration
    logger.debug(
        f"Callback map before summary cards registration: {len(app.callback_map)} callbacks"
    )

    @app.callback(
        [
            Output("portfolio-value", "children"),
            Output("total-value", "children"),
            Output("total-value-percent", "children"),
            Output("beta-adjusted-exposure", "children"),
            Output("beta-adjusted-percent", "children"),
            Output("long-exposure", "children"),
            Output("long-exposure-percent", "children"),
            Output("short-exposure", "children"),
            Output("short-exposure-percent", "children"),
            Output("options-exposure", "children"),
            Output("options-exposure-percent", "children"),
            Output("cash-like-value", "children"),
            Output("cash-like-percent", "children"),
        ],
        [Input("portfolio-summary", "data")],
        # Prevent initial call to avoid errors when data is not yet loaded
        prevent_initial_call=False,
    )
    def update_summary_cards(summary_data):
        """Update summary cards with latest data"""
        logger.debug("Updating summary cards")
        logger.debug(f"Summary data type: {type(summary_data)}")

        # Log the structure of the summary data
        if summary_data:
            logger.debug("Summary data keys: %s", list(summary_data.keys()))
            for key in summary_data.keys():
                if isinstance(summary_data[key], dict):
                    logger.debug(f"  {key} (dict): {list(summary_data[key].keys())}")
                elif isinstance(summary_data[key], list):
                    logger.debug(f"  {key} (list): {len(summary_data[key])} items")
                else:
                    logger.debug(f"  {key}: {summary_data[key]}")
        else:
            # Return error values when no summary data is available (normal during initial load)
            return error_values()

        try:
            # Call the format function
            formatted_values = format_summary_card_values(summary_data)

            # Log the formatted values
            logger.debug(f"Formatted summary card values: {formatted_values}")

            return formatted_values
        except Exception as e:
            # Log the error with full stack trace
            logger.error(f"Error in update_summary_cards: {e}", exc_info=True)
            return error_values()

    # Debug logging for callback registration
    logger.debug(
        f"Callback map after summary cards registration: {len(app.callback_map)} callbacks"
    )
