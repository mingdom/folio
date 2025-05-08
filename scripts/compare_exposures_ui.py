#!/usr/bin/env python3
"""
Script to compare summary card exposures with position details exposures,
using the same methods as the UI components.

This script loads portfolio data from a CSV file, calculates the summary card values,
and compares them with the sum of exposures from the position details as they would
appear in the UI.
"""

import os
import sys

import pandas as pd

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.folio.components.summary_cards import format_summary_card_values
from src.folio.portfolio import process_portfolio_data


def load_portfolio_data(csv_path):
    """Load portfolio data from a CSV file."""
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception:
        return None


def compare_exposures():
    """Compare summary card exposures with position details exposures."""
    # Try to load the private portfolio data first
    private_csv_path = "private-data/portfolios/portfolio-default.csv"
    sample_csv_path = "sample-data/sample-portfolio.csv"

    if os.path.exists(private_csv_path):
        df = load_portfolio_data(private_csv_path)
    elif os.path.exists(sample_csv_path):
        df = load_portfolio_data(sample_csv_path)
    else:
        return

    if df is None:
        return

    # Process the portfolio data
    result = process_portfolio_data(df)

    # Check the structure of the result
    if isinstance(result, tuple):
        if len(result) == 3:
            # Newer version: (groups, summary, cash_like_positions)
            groups, summary, cash_like_positions = result
        elif len(result) == 2:
            # Possible alternative: (groups, cash_like_positions)
            groups, cash_like_positions = result
            from src.folio.portfolio import calculate_portfolio_summary

            summary = calculate_portfolio_summary(groups, cash_like_positions, 0.0)
    else:
        # If result is not a tuple, it's likely just the groups
        groups = result
        from src.folio.portfolio import calculate_portfolio_summary

        summary = calculate_portfolio_summary(groups, [], 0.0)

    # Ensure we have a valid summary object
    if not hasattr(summary, "to_dict"):
        # Create a minimal summary for testing
        from src.folio.data_model import ExposureBreakdown, PortfolioSummary

        empty_exposure = ExposureBreakdown()
        summary = PortfolioSummary(
            net_market_exposure=0.0,
            portfolio_beta=0.0,
            long_exposure=empty_exposure,
            short_exposure=empty_exposure,
            options_exposure=empty_exposure,
        )

    # Get the summary card values
    summary_dict = summary.to_dict()
    formatted_values = format_summary_card_values(summary_dict)

    # Extract the values from the formatted values
    formatted_values[0]
    net_exposure = formatted_values[1]
    formatted_values[3]
    beta_adjusted_net_exposure = formatted_values[4]
    long_exposure = formatted_values[5]
    short_exposure = formatted_values[7]
    options_exposure = formatted_values[9]
    formatted_values[11]

    # Calculate the sum of exposures from the position details as they would appear in the UI

    # Initialize counters for UI exposures
    total_ui_market_value = 0.0
    total_ui_beta_adjusted_exposure = 0.0
    total_ui_delta_exposure = 0.0

    # Process each group as it would be displayed in the UI

    for group in groups:
        # Get values as they would be displayed in the UI
        market_value = (
            group.net_exposure
        )  # This is what's shown as "Total Value" in the UI
        beta_adjusted = (
            group.beta_adjusted_exposure
        )  # This is what's shown as "Beta-Adjusted Exposure" in the UI
        delta_exposure = (
            group.total_delta_exposure
        )  # This is what's shown as "Total Delta Exposure" in the UI

        # Print the values for this group

        # Add to totals
        total_ui_market_value += market_value
        total_ui_beta_adjusted_exposure += beta_adjusted
        total_ui_delta_exposure += delta_exposure

    # Extract numeric values from formatted strings
    def extract_numeric(value):
        return float(value.replace("$", "").replace(",", ""))

    summary_net_exposure = extract_numeric(net_exposure)
    summary_beta_adjusted_net_exposure = extract_numeric(beta_adjusted_net_exposure)
    extract_numeric(long_exposure)
    extract_numeric(short_exposure)
    summary_options_exposure = extract_numeric(options_exposure)

    # Compare with summary card values

    # Calculate long and short exposures from UI values
    ui_long_exposure = 0.0
    ui_short_exposure = 0.0

    for group in groups:
        if group.stock_position:
            stock = group.stock_position
            if stock.quantity >= 0:  # Long position
                ui_long_exposure += stock.market_value
            else:  # Short position
                ui_short_exposure += stock.market_value  # Already negative

        # Process option positions
        for opt in group.option_positions:
            if opt.delta_exposure >= 0:  # Long position
                ui_long_exposure += opt.delta_exposure
            else:  # Short position
                ui_short_exposure += opt.delta_exposure  # Already negative

    # Determine if the summary card values match the UI values
    if abs(summary_net_exposure - total_ui_market_value) < 0.01:
        pass

    if abs(summary_beta_adjusted_net_exposure - total_ui_beta_adjusted_exposure) < 0.01:
        pass

    if abs(summary_options_exposure - total_ui_delta_exposure) < 0.01:
        pass


if __name__ == "__main__":
    compare_exposures()
