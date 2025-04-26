"""End-to-end tests for exposure calculations."""

from src.folio.components.summary_cards import format_summary_card_values
from src.folio.formatting import format_currency


class TestExposures:
    """Test exposure calculations."""

    def test_summary_cards_match_position_details(self, processed_portfolio):
        """Test that summary card values match position details."""
        # Get the processed portfolio data
        groups, summary, summary_dict = processed_portfolio

        # Get the summary card values
        formatted_values = format_summary_card_values(summary_dict)

        # Extract the values from the formatted values
        formatted_values[0]  # Portfolio Value
        net_exposure = formatted_values[1]  # Net Exposure
        formatted_values[2]  # Net Exposure Percent
        beta_adjusted_exposure = formatted_values[3]  # Beta-Adjusted Net Exposure
        formatted_values[4]  # Beta-Adjusted Net Exposure Percent
        long_exposure = formatted_values[5]  # Long Exposure
        formatted_values[6]  # Long Exposure Percent
        short_exposure = formatted_values[7]  # Short Exposure
        formatted_values[8]  # Short Exposure Percent
        options_exposure = formatted_values[9]  # Options Exposure
        formatted_values[10]  # Options Exposure Percent
        formatted_values[11]  # Cash Value
        formatted_values[12]  # Cash Percent

        # Extract numeric values from formatted strings
        def extract_numeric(value):
            return float(value.replace("$", "").replace(",", ""))

        summary_net_exposure = extract_numeric(net_exposure)
        summary_beta_adjusted_net_exposure = extract_numeric(beta_adjusted_exposure)
        summary_long_exposure = extract_numeric(long_exposure)
        summary_short_exposure = extract_numeric(short_exposure)
        summary_options_exposure = extract_numeric(options_exposure)

        # Calculate position details exposures as they would appear in the UI
        total_ui_market_value = 0.0
        total_ui_beta_adjusted_exposure = 0.0
        total_ui_delta_exposure = 0.0

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

            # Add to totals
            total_ui_market_value += market_value
            total_ui_beta_adjusted_exposure += beta_adjusted
            total_ui_delta_exposure += delta_exposure

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

        # Print detailed debug information
        for _key, value in summary_dict.items():
            if isinstance(value, dict):
                for _subkey, _subvalue in value.items():
                    pass
            else:
                pass

        summary_dict.get("pending_activity_value", 0.0)


        # Test that summary card values match position details
        assert abs(summary_net_exposure - total_ui_market_value) < 0.01, (
            f"Net Exposure in summary cards ({format_currency(summary_net_exposure)}) does not match the total market value shown in the UI ({format_currency(total_ui_market_value)})"
        )

        assert (
            abs(summary_beta_adjusted_net_exposure - total_ui_beta_adjusted_exposure)
            < 0.01
        ), (
            f"Beta-Adjusted Net Exposure in summary cards ({format_currency(summary_beta_adjusted_net_exposure)}) does not match the total beta-adjusted exposure shown in the UI ({format_currency(total_ui_beta_adjusted_exposure)})"
        )

        assert abs(summary_long_exposure - ui_long_exposure) < 0.01, (
            f"Long Exposure in summary cards ({format_currency(summary_long_exposure)}) does not match the calculated long exposure ({format_currency(ui_long_exposure)})"
        )

        assert abs(summary_short_exposure - ui_short_exposure) < 0.01, (
            f"Short Exposure in summary cards ({format_currency(summary_short_exposure)}) does not match the calculated short exposure ({format_currency(ui_short_exposure)})"
        )

        assert abs(summary_options_exposure - total_ui_delta_exposure) < 0.01, (
            f"Options Exposure in summary cards ({format_currency(summary_options_exposure)}) does not match the total delta exposure shown in the UI ({format_currency(total_ui_delta_exposure)})"
        )
