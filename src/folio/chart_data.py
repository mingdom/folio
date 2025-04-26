"""Chart data transformation utilities.

This module provides functions to transform portfolio data into formats
suitable for visualization with Plotly charts.
"""

from typing import Any

from .data_model import PortfolioGroup, PortfolioSummary
from .formatting import format_compact_currency, format_currency
from .logger import logger
from .portfolio import calculate_beta_adjusted_net_exposure
from .portfolio_value import (
    calculate_component_percentages,
    get_portfolio_component_values,
)


class ChartColors:
    """Chart color constants for consistent visualization.

    This class defines the color palette used across all charts in the application.
    Use these constants instead of hardcoded hex values to ensure consistency.

    IMPORTANT: These colors are used across all charts and should be kept consistent.
    When adding a new chart, always use these constants instead of defining new colors.
    """

    # Core color palette - used across all charts
    LONG = "#1E8449"  # Green for long positions
    SHORT = "#2F3136"  # Dark gray/black for short positions
    OPTIONS = "#8E44AD"  # Purple for options
    NET = "#2980B9"  # Blue for net values
    CASH = "#8E44AD"  # Same purple as OPTIONS
    PENDING = "#2980B9"  # Same blue as NET


# transform_for_asset_allocation function has been removed in favor of the more accurate Exposure Chart


def transform_for_exposure_chart(
    portfolio_summary: PortfolioSummary, use_beta_adjusted: bool = False
) -> dict[str, Any]:
    """Transform portfolio summary data for the exposure chart.

    Args:
        portfolio_summary: Portfolio summary data from the data model
        use_beta_adjusted: Whether to use beta-adjusted values

    Returns:
        Dict containing data and layout for the bar chart
    """
    logger.debug("Transforming data for exposure chart")

    # Log portfolio summary fields for debugging
    logger.debug(
        f"Portfolio summary net_market_exposure: {portfolio_summary.net_market_exposure}"
    )
    logger.debug(f"Portfolio summary long_exposure: {portfolio_summary.long_exposure}")
    logger.debug(
        f"Portfolio summary short_exposure: {portfolio_summary.short_exposure}"
    )
    logger.debug(
        f"Portfolio summary options_exposure: {portfolio_summary.options_exposure}"
    )

    # Extract values based on whether we want beta-adjusted or not
    if use_beta_adjusted:
        logger.debug("Using beta-adjusted values for exposure chart")
        long_value = portfolio_summary.long_exposure.total_beta_adjusted
        # Show short exposure as negative
        short_value = portfolio_summary.short_exposure.total_beta_adjusted
        options_value = portfolio_summary.options_exposure.total_beta_adjusted
        # Use the utility function for beta-adjusted net exposure
        net_value = calculate_beta_adjusted_net_exposure(
            portfolio_summary.long_exposure.total_beta_adjusted,
            portfolio_summary.short_exposure.total_beta_adjusted,
        )
        logger.debug(
            f"Beta-adjusted values - Long: {long_value}, Short: {short_value}, Options: {options_value}, Net: {net_value}"
        )
    else:
        logger.debug("Using net exposure values for exposure chart")
        long_value = portfolio_summary.long_exposure.total_exposure
        # Show short exposure as negative
        short_value = portfolio_summary.short_exposure.total_exposure
        options_value = portfolio_summary.options_exposure.total_exposure
        # Use the pre-calculated net market exposure
        net_value = portfolio_summary.net_market_exposure
        logger.debug(
            f"Net exposure values - Long: {long_value}, Short: {short_value}, Options: {options_value}, Net: {net_value}"
        )

    # Categories and values for the chart
    categories = ["Long", "Short", "Options", "Net"]
    values = [long_value, short_value, options_value, net_value]

    # Format values for display
    text_values = [format_currency(value) for value in values]

    # Colors for the bars - using ChartColors constants
    colors = [
        ChartColors.LONG,
        ChartColors.SHORT,
        ChartColors.OPTIONS,
        ChartColors.NET,
    ]

    # Create the chart data
    chart_data = {
        "data": [
            {
                "type": "bar",
                "x": categories,
                "y": values,
                "text": text_values,
                "textposition": "auto",
                "hoverinfo": "text",
                "hovertemplate": "<b>%{x}</b><br>%{text}<extra></extra>",
                "marker": {"color": colors, "line": {"width": 0}, "opacity": 0.9},
            }
        ],
        "layout": {
            "title": {
                "text": "Market Exposure"
                + (" (Beta-Adjusted)" if use_beta_adjusted else ""),
                "font": {"size": 16, "color": "#2C3E50"},
                "x": 0.5,  # Center the title
                "xanchor": "center",
            },
            "xaxis": {
                "title": "Exposure Type",
                "titlefont": {"size": 12, "color": "#7F8C8D"},
                "tickfont": {"size": 11},
            },
            "yaxis": {
                "title": "Exposure ($)",
                "titlefont": {"size": 12, "color": "#7F8C8D"},
                "tickfont": {"size": 11},
                "gridcolor": "#ECF0F1",
                "zerolinecolor": "#BDC3C7",
            },
            "margin": {"l": 50, "r": 20, "t": 50, "b": 50, "pad": 4},
            "autosize": True,  # Allow the chart to resize with its container
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "font": {
                "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
            },
        },
    }

    return chart_data


def transform_for_treemap(
    portfolio_groups: list[PortfolioGroup], _group_by: str = "ticker"
) -> dict[str, Any]:
    """Transform portfolio groups data for the treemap chart.

    Args:
        portfolio_groups: List of portfolio groups from the data model
        _group_by: Unused parameter (kept for backward compatibility)

    Returns:
        Dict containing data and layout for the treemap chart
    """
    logger.debug("Transforming data for treemap chart (grouped by ticker)")
    logger.debug(f"Number of portfolio groups: {len(portfolio_groups)}")

    # Log some details about the first few groups for debugging
    for i, group in enumerate(portfolio_groups[:3]):
        logger.debug(f"Group {i} ticker: {group.ticker}")
        logger.debug(f"Group {i} net_exposure: {group.net_exposure}")
        if group.stock_position:
            logger.debug(
                f"Group {i} stock position market_exposure: {group.stock_position.market_exposure}"
            )
        logger.debug(f"Group {i} has {len(group.option_positions)} option positions")

    # Initialize lists for treemap data
    labels = []
    parents = []
    values = []
    texts = []
    colors = []

    # Add root node
    labels.append("Portfolio")
    parents.append("")
    values.append(0)  # Will be sum of children
    texts.append("Portfolio")
    colors.append("#FFFFFF")  # White for root

    # Group by ticker
    # First, collect all unique tickers and calculate their total exposure
    ticker_exposures = {}
    for group in portfolio_groups:
        ticker = group.ticker
        exposure = 0

        # Add stock position exposure
        stock_exposure = 0
        if group.stock_position:
            # Use market exposure for stocks
            stock_exposure = group.stock_position.market_exposure
            logger.debug(f"Ticker {ticker} stock exposure: {stock_exposure}")
            exposure += stock_exposure

        # Add option positions exposure (delta exposure)
        option_exposure = 0
        for option in group.option_positions:
            logger.debug(
                f"Ticker {ticker} option {option.option_type} delta_exposure: {option.delta_exposure}"
            )
            option_exposure += option.delta_exposure

        exposure += option_exposure
        logger.debug(
            f"Ticker {ticker} total exposure: {exposure} (stock: {stock_exposure}, options: {option_exposure})"
        )

        # Store the net exposure value for sizing (not absolute)
        ticker_exposures[ticker] = exposure

    # Sort tickers by absolute exposure (largest first)
    sorted_tickers = sorted(
        ticker_exposures.keys(), key=lambda t: abs(ticker_exposures[t]), reverse=True
    )

    # Add ticker nodes
    for ticker in sorted_tickers:
        # Skip tickers with zero exposure
        if ticker_exposures[ticker] == 0:
            continue

        exposure = ticker_exposures[ticker]
        labels.append(ticker)
        parents.append("Portfolio")
        # Note: We still use abs() here for sizing because treemap requires positive values
        # But we maintain the sign information in the text and color
        values.append(abs(exposure))
        texts.append(f"{ticker}: {format_currency(exposure)}")

        # Color based on long/short - using ChartColors constants
        color = ChartColors.LONG if exposure > 0 else ChartColors.SHORT
        colors.append(color)

    # We don't need to add individual positions anymore - just show the ticker level

    # Create the chart data
    chart_data = {
        "data": [
            {
                "type": "treemap",
                "labels": labels,
                "parents": parents,
                "values": values,
                "text": texts,
                "hoverinfo": "text",
                "marker": {
                    "colors": colors,
                    "line": {"width": 1, "color": "#FFFFFF"},
                    "pad": 3,
                },
                "textfont": {
                    "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
                    "size": 12,
                    "color": "#FFFFFF",
                },
                "hovertemplate": "%{text}<extra></extra>",
            }
        ],
        "layout": {
            "title": {
                "text": "Position Size by Exposure",
                "font": {"size": 16, "color": "#2C3E50"},
                "x": 0.5,  # Center the title
                "xanchor": "center",
            },
            "margin": {"l": 0, "r": 0, "t": 50, "b": 0, "pad": 4},
            "autosize": True,  # Allow the chart to resize with its container
            "paper_bgcolor": "white",
            "font": {
                "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
            },
        },
    }

    return chart_data


# Sector allocation chart has been removed as it's not currently supported


def transform_for_allocations_chart(
    portfolio_summary: PortfolioSummary,
) -> dict[str, Any]:
    """Transform portfolio summary data for the allocations chart.

    This function takes a portfolio summary and transforms it into a format
    suitable for a bar chart showing portfolio allocations. The chart
    has four main categories:
    - Long: Total long exposure (stocks + options combined)
    - Short: Total short exposure (stocks + options combined)
    - Cash: Cash-like positions
    - Pending: Pending activity

    IMPORTANT: Short values are stored as negative numbers in the portfolio summary.
    We maintain these negative values in the chart to show short positions below
    the x-axis, providing a more intuitive visualization of long vs short positions.

    Args:
        portfolio_summary: The portfolio summary to transform

    Returns:
        A dictionary with 'data' and 'layout' keys suitable for a Plotly chart
    """
    logger.debug("Transforming data for allocations chart")

    # Skip empty portfolios
    if portfolio_summary.portfolio_estimate_value == 0:
        logger.warning("Empty portfolio - no data for allocations chart")
        return {
            "data": [],
            "layout": {
                "height": 400,
                "annotations": [
                    {
                        "text": "No portfolio data available",
                        "showarrow": False,
                        "font": {"color": "#7F8C8D"},
                    }
                ],
            },
        }

    # Get component values (short values are negative)
    values = get_portfolio_component_values(portfolio_summary)

    # Calculate percentages
    percentages = calculate_component_percentages(values)

    # Calculate combined values
    long_total = values["long_stock"] + values["long_option"]
    short_total = values["short_stock"] + values["short_option"]

    # Format detailed breakdown for hover text
    long_text = (
        f"Long Total: {format_currency(long_total)} ({percentages['long_total']:.1f}%)<br>"
        f"• Stocks: {format_currency(values['long_stock'])} ({percentages['long_stock']:.1f}%)<br>"
        f"• Options: {format_currency(values['long_option'])} ({percentages['long_option']:.1f}%)"
    )

    short_text = (
        f"Short Total: {format_currency(short_total)} ({percentages['short_total']:.1f}%)<br>"
        f"• Stocks: {format_currency(values['short_stock'])} ({percentages['short_stock']:.1f}%)<br>"
        f"• Options: {format_currency(values['short_option'])} ({percentages['short_option']:.1f}%)"
    )

    cash_text = f"Cash: {format_currency(values['cash'])} ({percentages['cash']:.1f}%)"
    pending_text = (
        f"Pending: {format_currency(values['pending'])} ({percentages['pending']:.1f}%)"
    )

    # Create compact text labels for display on bars
    long_display_text = format_compact_currency(long_total)
    short_display_text = format_compact_currency(short_total)
    cash_display_text = format_compact_currency(values["cash"])
    pending_display_text = format_compact_currency(values["pending"])

    # Create the bar chart data with a single bar for each category
    chart_data = {
        "data": [
            # Long position (single bar with combined value)
            {
                "name": "Long",
                "x": ["Long"],
                "y": [long_total],
                "type": "bar",
                "marker": {"color": ChartColors.LONG},
                "text": [long_display_text],  # Compact text for display
                "textposition": "inside",  # Show text inside bars
                "insidetextanchor": "middle",  # Center text
                "hoverinfo": "text",
                "hovertemplate": "%{text}<br>" + long_text + "<extra></extra>",
                "textfont": {"color": "white", "size": 12},  # Ensure text is visible
            },
            # Short position (single bar with combined value)
            {
                "name": "Short",
                "x": ["Short"],
                "y": [short_total],  # Already negative
                "type": "bar",
                "marker": {"color": ChartColors.SHORT},
                "text": [short_display_text],  # Compact text for display
                "textposition": "inside",  # Show text inside bars
                "insidetextanchor": "middle",  # Center text
                "hoverinfo": "text",
                "hovertemplate": "%{text}<br>" + short_text + "<extra></extra>",
                "textfont": {"color": "white", "size": 12},  # Ensure text is visible
            },
            # Cash (single bar)
            {
                "name": "Cash",
                "x": ["Cash"],
                "y": [values["cash"]],
                "type": "bar",
                "marker": {"color": ChartColors.CASH},
                "text": [cash_display_text],  # Compact text for display
                "textposition": "inside",  # Show text inside bars
                "insidetextanchor": "middle",  # Center text
                "hoverinfo": "text",
                "hovertemplate": "%{text}<br>" + cash_text + "<extra></extra>",
                "textfont": {"color": "white", "size": 12},  # Ensure text is visible
            },
            # Pending (single bar)
            {
                "name": "Pending",
                "x": ["Pending"],
                "y": [values["pending"]],
                "type": "bar",
                "marker": {"color": ChartColors.PENDING},
                "text": [pending_display_text],  # Compact text for display
                "textposition": "inside",  # Show text inside bars
                "insidetextanchor": "middle",  # Center text
                "hoverinfo": "text",
                "hovertemplate": "%{text}<br>" + pending_text + "<extra></extra>",
                "textfont": {"color": "white", "size": 12},  # Ensure text is visible
            },
        ],
        "layout": {
            "title": {
                "text": "Portfolio Allocation",
                "font": {"size": 16, "color": "#2C3E50"},
                "x": 0.5,  # Center the title
                "xanchor": "center",
            },
            "barmode": "relative",  # Use relative mode instead of stack
            "margin": {"l": 60, "r": 60, "t": 50, "b": 40, "pad": 4},
            "autosize": True,  # Allow the chart to resize with its container
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
            "font": {
                "family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
            },
            "showlegend": False,  # Hide legend since bar labels are clear
            "yaxis": {
                "title": "Value ($)",
                "type": "linear",
                "tickformat": "$,.1s",  # Use compact format (K, M, B)
                "gridcolor": "#E5E5E5",
                "exponentformat": "none",  # Hide exponent notation
                "showticklabels": True,
                "nticks": 10,  # More tick marks for better readability
                "showgrid": True,
                "zeroline": True,
                "zerolinecolor": "#000000",
                "zerolinewidth": 2,
                "automargin": True,  # Ensure labels don't get cut off
                "ticklen": 5,  # Longer tick marks
                "tickwidth": 1,  # Slightly thicker ticks
                "tickcolor": "#777777",  # Darker tick color
            },
            "height": 400,  # Increased height for better visualization
        },
    }

    # Calculate the maximum and minimum y-values for setting the y-axis range
    max_value = max(
        long_total,
        values["cash"],
        values["pending"],
        1,  # Ensure we have a non-zero range
    )

    min_value = min(
        short_total,
        0,  # Ensure we include zero in the range
    )

    # Add padding for better visualization
    top_padding = 0.1  # 10% padding on top
    bottom_padding = 0.2  # 20% padding on bottom (more space for negative values)

    # Determine the appropriate y-axis range based on the data
    if abs(min_value) < 0.001:
        # No significant short positions, focus on positive values only
        chart_data["layout"]["yaxis"]["range"] = [
            -max_value * 0.05,  # Small negative space for zero line visibility
            max_value * (1 + top_padding),
        ]
    elif abs(min_value) < max_value * 0.1:
        # Short positions are small (less than 10% of long)
        # Use asymmetric scale with just enough room for short positions
        chart_data["layout"]["yaxis"]["range"] = [
            min_value * (1 + bottom_padding),
            max_value * (1 + top_padding),
        ]
    elif abs(min_value) < max_value * 0.3:
        # Short positions are moderate (10-30% of long)
        # Use moderately asymmetric scale
        chart_data["layout"]["yaxis"]["range"] = [
            min_value * (1 + bottom_padding),
            max_value * (1 + top_padding),
        ]
    else:
        # Short positions are significant (>30% of long)
        # Use a more balanced scale, but still optimized for the actual data
        max_abs = max(abs(max_value), abs(min_value))
        chart_data["layout"]["yaxis"]["range"] = [
            -max_abs * (1 + bottom_padding) if min_value < 0 else -max_value * 0.05,
            max_abs * (1 + top_padding),
        ]

    # Add more tick marks for better readability
    chart_data["layout"]["yaxis"]["nticks"] = 12

    return chart_data


def create_dashboard_metrics(
    portfolio_summary: PortfolioSummary,
) -> list[dict[str, str]]:
    """Create a list of key metrics for the dashboard.

    Args:
        portfolio_summary: Portfolio summary data from the data model

    Returns:
        List of dictionaries with title, value, and help_text for each metric
    """
    logger.debug("Creating dashboard metrics")

    # Define the metrics to display
    metrics = [
        {
            "title": "Total Value",
            "value": format_currency(portfolio_summary.total_value_net),
            "help_text": portfolio_summary.help_text.get("total_value_net", ""),
        },
        {
            "title": "Portfolio Beta",
            "value": f"{portfolio_summary.portfolio_beta:.2f}",
            "help_text": portfolio_summary.help_text.get("portfolio_beta", ""),
        },
        {
            "title": "Long Exposure",
            "value": format_currency(portfolio_summary.long_exposure.total_value),
            "help_text": portfolio_summary.help_text.get("long_exposure", ""),
        },
        {
            "title": "Short Exposure",
            "value": format_currency(portfolio_summary.short_exposure.total_value),
            "help_text": portfolio_summary.help_text.get("short_exposure", ""),
        },
        {
            "title": "Options Exposure",
            "value": format_currency(portfolio_summary.options_exposure.total_value),
            "help_text": portfolio_summary.help_text.get("options_exposure", ""),
        },
    ]

    return metrics
