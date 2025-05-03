import dash_bootstrap_components as dbc
from dash import html

from ..data_model import PortfolioGroup
from ..formatting import format_beta, format_currency


def get_group_ticker(group: PortfolioGroup) -> str:
    """Get the primary ticker for a portfolio group"""
    if group.stock_position:
        return group.stock_position.ticker
    elif group.option_positions:
        return group.option_positions[0].ticker
    return "Unknown"


def create_position_row(group: PortfolioGroup, _metrics: dict) -> dbc.Row:
    """Create a row for a position in the portfolio table

    Args:
        group: PortfolioGroup containing position data
        _metrics: Dictionary of additional metrics to display (currently unused, reserved for future use)

    Returns:
        Dash Bootstrap Components Row for the portfolio table
    """
    ticker = get_group_ticker(group)

    # We decided not to show price in the table as it's confusing with mixed stock/option positions

    return dbc.Row(
        [
            dbc.Col(
                html.Strong(ticker),
                width=2,
                className="text-truncate text-center",
                style={"padding": "0.5rem"},
            ),
            dbc.Col(
                [
                    html.Div([
                        html.Span("Stock" if group.stock_position else ""),
                        html.Span(
                            f" ({len(group.option_positions)} options)"
                            if group.option_positions
                            else ""
                        ),
                    ])
                ],
                width=2,
                className="text-truncate text-center",
            ),
            dbc.Col(
                format_currency(group.net_exposure),
                width=2,
                className="text-truncate text-center",
            ),
            dbc.Col(
                format_beta(
                    group.beta_adjusted_exposure / group.net_exposure
                    if group.net_exposure != 0
                    else 0
                ),
                width=2,
                className="text-truncate text-center",
            ),
            dbc.Col(
                format_currency(group.beta_adjusted_exposure),
                width=2,
                className="text-truncate text-center",
            ),
            dbc.Col(
                html.Div(
                    [
                        dbc.Button(
                            html.I(className="fas fa-chart-line"),
                            id={"type": "position-pnl", "index": ticker},
                            color="primary",
                            size="sm",
                            className="btn-icon",
                        ),
                        dbc.Tooltip(
                            "View position analysis and P&L chart",
                            target={"type": "position-pnl", "index": ticker},
                            placement="left",
                        ),
                    ],
                    className="d-flex justify-content-center",
                ),
                width=2,
            ),
        ],
        className="g-0 border-bottom py-2 position-row",
        id=f"row-{ticker}",
    )


def create_sortable_header(label: str, column_id: str, current_sort: str) -> html.Div:
    """Create a sortable header for the portfolio table

    Args:
        label: The text to display in the header
        column_id: The id of the column, used for sorting
        current_sort: The current sort state in format 'column-direction'

    Returns:
        A clickable header with sort indicator
    """
    current_column, current_direction = (
        current_sort.split("-") if "-" in current_sort else (current_sort, "desc")
    )

    # Determine if this column is currently sorted
    is_sorted = current_column == column_id

    # Add sort indicator
    if is_sorted:
        if current_direction == "desc":
            indicator = html.I(className="fas fa-sort-down ms-1")
        else:
            indicator = html.I(className="fas fa-sort-up ms-1")
    else:
        indicator = html.I(className="fas fa-sort ms-1 text-muted")

    return html.Div(
        [html.Strong(label), indicator],
        id={"type": "sort-header", "column": column_id},
        className="d-flex align-items-center justify-content-center sort-header",
    )


def create_portfolio_table(
    groups: list[PortfolioGroup],
    search: str | None = None,
    sort_by: str = "value-desc",
) -> html.Div:
    """Create the portfolio table with all positions"""
    # Filter groups based on search
    if search:
        search = search.lower()
        filtered_groups = []
        for g in groups:
            ticker = get_group_ticker(g)
            if search in ticker.lower():
                filtered_groups.append(g)
        groups = filtered_groups

    # Sort groups
    sort_key, sort_direction = (
        sort_by.split("-") if "-" in sort_by else (sort_by, "desc")
    )
    if sort_key == "value":
        # Sort by the net exposure value
        groups.sort(key=lambda x: x.net_exposure, reverse=sort_direction == "desc")
    elif sort_key == "beta":
        # Sort by actual beta value (beta_adjusted_exposure / net_exposure)
        groups.sort(
            key=lambda x: x.beta_adjusted_exposure / x.net_exposure
            if x.net_exposure != 0
            else 0,
            reverse=sort_direction == "desc",
        )
    elif sort_key == "exposure":
        # Sort by beta-adjusted exposure since that's the main number shown
        groups.sort(
            key=lambda x: x.beta_adjusted_exposure,
            reverse=sort_direction == "desc",
        )
    # Price sorting removed as we don't show price in the table
    elif sort_key == "ticker":
        groups.sort(
            key=lambda x: get_group_ticker(x).lower(), reverse=sort_direction == "desc"
        )
    elif sort_key == "type":
        # Sort by type - first stocks, then options-only positions
        groups.sort(
            key=lambda x: "1" if x.stock_position else "2",
            reverse=sort_direction == "desc",
        )

    # Create table header with proper thead structure
    header_row = dbc.Row(
        [
            dbc.Col(
                create_sortable_header("Ticker", "ticker", sort_by),
                width=2,
                className="text-truncate text-center",
                style={"padding": "0.5rem"},
            ),
            dbc.Col(
                create_sortable_header("Type", "type", sort_by),
                width=2,
                className="text-truncate text-center",
                style={"padding": "0.5rem"},
            ),
            dbc.Col(
                create_sortable_header("Exposure", "value", sort_by),
                width=2,
                className="text-truncate text-center",
                style={"padding": "0.5rem"},
            ),
            dbc.Col(
                create_sortable_header("Beta", "beta", sort_by),
                width=2,
                className="text-truncate text-center",
                style={"padding": "0.5rem"},
            ),
            dbc.Col(
                create_sortable_header("Beta-Adj Exp", "exposure", sort_by),
                width=2,
                className="text-truncate text-center",
                style={"padding": "0.5rem"},
            ),
            dbc.Col("", width=2, className="text-center", style={"padding": "0.5rem"}),
        ],
        className="g-0 border-bottom py-2 bg-light header-row",
    )

    # Create table rows
    rows = [create_position_row(group, {}) for group in groups]

    # Return a properly structured table with thead and tbody
    return html.Div(
        [
            # Use dbc.Table with proper HTML structure
            dbc.Table(
                [
                    html.Thead(header_row),  # Wrap header in thead
                    html.Tbody(rows),  # Wrap rows in tbody
                ],
                className="portfolio-table table-hover table-borderless w-100",
                responsive=True,
                bordered=False,
                striped=False,
            )
        ],
        className="portfolio-table-container",
    )
