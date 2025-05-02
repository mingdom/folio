"""
Tests for the portfolio calculation functions.
"""

from src.folib.calculations.portfolio import (
    calculate_portfolio_metrics,
    create_value_breakdowns,
)


class TestCreateValueBreakdowns:
    """Tests for the create_value_breakdowns function."""

    def test_create_value_breakdowns_with_all_values(self):
        """Test creating value breakdowns with all values populated."""
        # Arrange
        long_stocks = {"value": 1500.0, "beta_adjusted": 1800.0}
        short_stocks = {"value": -500.0, "beta_adjusted": -600.0}
        long_options = {
            "value": 1000.0,
            "beta_adjusted": 1200.0,
            "delta_exposure": 600.0,
        }
        short_options = {
            "value": -300.0,
            "beta_adjusted": -360.0,
            "delta_exposure": -180.0,
        }

        # Act
        long_value, short_value, options_value = create_value_breakdowns(
            long_stocks, short_stocks, long_options, short_options
        )

        # Assert
        assert long_value == 1500.0
        assert short_value == 500.0  # Absolute value of -500.0
        assert options_value == 1300.0  # 1000.0 + 300.0

    def test_create_value_breakdowns_with_zero_values(self):
        """Test creating value breakdowns with zero values."""
        # Arrange
        long_stocks = {"value": 0.0, "beta_adjusted": 0.0}
        short_stocks = {"value": 0.0, "beta_adjusted": 0.0}
        long_options = {"value": 0.0, "beta_adjusted": 0.0, "delta_exposure": 0.0}
        short_options = {"value": 0.0, "beta_adjusted": 0.0, "delta_exposure": 0.0}

        # Act
        long_value, short_value, options_value = create_value_breakdowns(
            long_stocks, short_stocks, long_options, short_options
        )

        # Assert
        assert long_value == 0.0
        assert short_value == 0.0
        assert options_value == 0.0


class TestCalculatePortfolioMetrics:
    """Tests for the calculate_portfolio_metrics function."""

    def test_calculate_portfolio_metrics_with_long_and_short(self):
        """Test calculating portfolio metrics with both long and short positions."""
        # Arrange
        long_value = 1500.0
        short_value = 500.0

        # Act
        net_exposure, portfolio_beta, short_percentage = calculate_portfolio_metrics(
            long_value, short_value
        )

        # Assert
        assert net_exposure == 1000.0  # 1500.0 - 500.0
        assert portfolio_beta == 1.0  # Simplified implementation
        assert short_percentage == 25.0  # 500.0 / 2000.0 * 100

    def test_calculate_portfolio_metrics_with_zero_values(self):
        """Test calculating portfolio metrics with zero values."""
        # Arrange
        long_value = 0.0
        short_value = 0.0

        # Act
        net_exposure, portfolio_beta, short_percentage = calculate_portfolio_metrics(
            long_value, short_value
        )

        # Assert
        assert net_exposure == 0.0
        assert portfolio_beta == 1.0  # Simplified implementation
        assert short_percentage == 0.0  # No division by zero
