"""End-to-end tests for portfolio calculations."""

from src.folio.portfolio import calculate_beta_adjusted_net_exposure


class TestPortfolioCalculations:
    """Test portfolio calculations."""

    def test_portfolio_value_matches_components(self, processed_portfolio):
        """Test that portfolio value matches the sum of its components."""
        # Get the processed portfolio data
        groups, summary, summary_dict = processed_portfolio

        # Get the portfolio value and its components
        portfolio_value = summary.portfolio_estimate_value
        stock_value = summary.stock_value
        option_value = summary.option_value
        cash_value = summary.cash_like_value
        pending_value = summary.pending_activity_value

        # Calculate the expected portfolio value
        expected_value = stock_value + option_value + cash_value + pending_value

        # Test that the portfolio value matches the sum of its components
        assert abs(portfolio_value - expected_value) < 0.01, (
            f"Portfolio value ({portfolio_value}) does not match the sum of its components ({expected_value})"
        )

    def test_net_exposure_matches_long_minus_short(self, processed_portfolio):
        """Test that net exposure matches long minus short."""
        # Get the processed portfolio data
        groups, summary, summary_dict = processed_portfolio

        # Get the net exposure and its components
        net_exposure = summary.net_market_exposure
        long_exposure = summary.long_exposure.total_exposure
        short_exposure = summary.short_exposure.total_exposure

        # Calculate the expected net exposure
        expected_net_exposure = (
            long_exposure + short_exposure
        )  # short is already negative

        # Test that the net exposure matches long minus short
        assert abs(net_exposure - expected_net_exposure) < 0.01, (
            f"Net exposure ({net_exposure}) does not match long + short ({expected_net_exposure})"
        )

    def test_beta_adjusted_net_exposure_calculation(self, processed_portfolio):
        """Test that beta-adjusted net exposure is calculated correctly."""
        # Get the processed portfolio data
        groups, summary, summary_dict = processed_portfolio

        # Get the beta-adjusted net exposure and its components
        beta_adjusted_net_exposure = (
            summary.long_exposure.total_beta_adjusted
            + summary.short_exposure.total_beta_adjusted
        )
        long_beta_adjusted = summary.long_exposure.total_beta_adjusted
        short_beta_adjusted = summary.short_exposure.total_beta_adjusted

        # Calculate the expected beta-adjusted net exposure using the utility function
        expected_beta_adjusted_net_exposure = calculate_beta_adjusted_net_exposure(
            long_beta_adjusted, short_beta_adjusted
        )

        # Test that the beta-adjusted net exposure matches the expected value
        assert (
            abs(beta_adjusted_net_exposure - expected_beta_adjusted_net_exposure) < 0.01
        ), (
            f"Beta-adjusted net exposure ({beta_adjusted_net_exposure}) does not match the expected value ({expected_beta_adjusted_net_exposure})"
        )

    def test_portfolio_beta_calculation(self, processed_portfolio):
        """Test that portfolio beta is calculated correctly."""
        # Get the processed portfolio data
        groups, summary, summary_dict = processed_portfolio

        # Get the portfolio beta and its components
        portfolio_beta = summary.portfolio_beta
        net_beta_adjusted_exposure = (
            summary.long_exposure.total_beta_adjusted
            + summary.short_exposure.total_beta_adjusted
        )
        net_market_exposure = summary.net_market_exposure

        # Calculate the expected portfolio beta
        expected_portfolio_beta = (
            net_beta_adjusted_exposure / net_market_exposure
            if net_market_exposure != 0
            else 0.0
        )

        # Test that the portfolio beta matches the expected value
        assert abs(portfolio_beta - expected_portfolio_beta) < 0.01, (
            f"Portfolio beta ({portfolio_beta}) does not match the expected value ({expected_portfolio_beta})"
        )
