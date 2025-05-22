"""
Tests for the to_dict methods added to domain classes.
"""

import datetime

from src.folib.domain import (
    OptionPosition,
    PortfolioSummary,
    StockPosition,
    UnknownPosition,
)


class TestDomainToDictMethods:
    """Tests for the to_dict methods added to domain classes."""

    def test_position_to_dict(self):
        """Test the to_dict method of the Position class."""
        # Arrange
        position = StockPosition(
            ticker="AAPL",
            quantity=10,
            price=150.0,
            cost_basis=1400.0,
        )

        # Act
        result = position.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result["ticker"] == "AAPL"
        assert result["quantity"] == 10
        assert result["price"] == 150.0
        assert result["position_type"] == "stock"
        assert result["market_value"] == 1500.0
        assert result["cost_basis"] == 1400.0

    def test_option_position_to_dict(self):
        """Test the to_dict method of the OptionPosition class."""
        # Arrange
        today = datetime.date.today()
        position = OptionPosition(
            ticker="AAPL",
            quantity=2,
            price=5.0,
            strike=160.0,
            expiry=today + datetime.timedelta(days=30),
            option_type="CALL",
            cost_basis=900.0,
        )

        # Act
        result = position.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result["ticker"] == "AAPL"
        assert result["quantity"] == 2
        assert result["price"] == 5.0
        assert result["position_type"] == "option"
        assert result["market_value"] == 1000.0
        assert result["cost_basis"] == 900.0
        assert result["strike"] == 160.0
        assert result["option_type"] == "CALL"
        assert result["expiry"] == (today + datetime.timedelta(days=30)).isoformat()

    def test_unknown_position_to_dict(self):
        """Test the to_dict method of the UnknownPosition class."""
        # Arrange
        position = UnknownPosition(
            ticker="XYZ123",
            quantity=5,
            price=10.0,
            original_description="Unknown security",
            cost_basis=45.0,
        )

        # Act
        result = position.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result["ticker"] == "XYZ123"
        assert result["quantity"] == 5
        assert result["price"] == 10.0
        assert result["position_type"] == "unknown"
        assert result["market_value"] == 50.0
        assert result["cost_basis"] == 45.0
        assert result["original_description"] == "Unknown security"

    def test_portfolio_summary_to_dict(self):
        """Test the to_dict method of the PortfolioSummary class."""
        # Arrange
        summary = PortfolioSummary(
            total_value=2500.0,
            stock_value=1500.0,
            option_value=1000.0,
            cash_value=0.0,
            unknown_value=0.0,
            pending_activity_value=100.0,
            net_market_exposure=2500.0,
            net_exposure_pct=1.0,
            beta_adjusted_exposure=3000.0,
        )

        # Act
        result = summary.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result["total_value"] == 2500.0
        assert result["stock_value"] == 1500.0
        assert result["option_value"] == 1000.0
        assert result["cash_value"] == 0.0
        assert result["unknown_value"] == 0.0
        assert result["pending_activity_value"] == 100.0
        assert result["net_market_exposure"] == 2500.0
        assert result["beta_adjusted_exposure"] == 3000.0
        # net_exposure_pct is not included in to_dict() output
