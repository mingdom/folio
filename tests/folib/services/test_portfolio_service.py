"""
Tests for the portfolio service module.

This module contains tests for the portfolio service functionality,
focusing on portfolio processing, position classification, and summary calculation.
"""

from unittest.mock import patch

from src.folib.domain import PortfolioHolding
from src.folib.services.portfolio_service import (
    _get_pending_activity,
    _is_pending_activity,
    create_portfolio_summary,
    process_portfolio,
)


class TestPendingActivity:
    """Tests for pending activity detection and processing."""

    def test_is_pending_activity(self):
        """Test the _is_pending_activity function."""
        # Test with various pending activity patterns
        assert _is_pending_activity("PENDING ACTIVITY") is True
        assert _is_pending_activity("pending activity") is True
        assert _is_pending_activity("Pending Activity") is True
        assert _is_pending_activity("PENDING") is True
        assert _is_pending_activity("UNSETTLED") is True

        # Test with non-pending activity strings
        assert _is_pending_activity("AAPL") is False
        assert _is_pending_activity("CASH") is False
        assert _is_pending_activity("") is False
        assert _is_pending_activity(None) is False

    def test_get_pending_activity(self):
        """Test the _get_pending_activity function."""
        # Create test holdings
        holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150.0,
                value=1500.0,
            ),
            PortfolioHolding(
                symbol="PENDING ACTIVITY",
                description="Pending Activity",
                quantity=1,
                price=0.0,
                value=500.0,
            ),
            PortfolioHolding(
                symbol="MSFT",
                description="MICROSOFT CORP",
                quantity=5,
                price=300.0,
                value=1500.0,
            ),
        ]

        # Test that pending activity is correctly identified and summed
        assert _get_pending_activity(holdings) == 500.0

        # Test with multiple pending activities
        holdings.append(
            PortfolioHolding(
                symbol="PENDING",
                description="Pending Deposit",
                quantity=1,
                price=0.0,
                value=200.0,
            )
        )
        assert _get_pending_activity(holdings) == 700.0

        # Test with no pending activity
        no_pending_holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150.0,
                value=1500.0,
            ),
            PortfolioHolding(
                symbol="MSFT",
                description="MICROSOFT CORP",
                quantity=5,
                price=300.0,
                value=1500.0,
            ),
        ]
        assert _get_pending_activity(no_pending_holdings) == 0.0

        # Test with pending activity that has zero value
        zero_value_holdings = [
            PortfolioHolding(
                symbol="PENDING ACTIVITY",
                description="Pending Activity",
                quantity=1,
                price=0.0,
                value=0.0,
            ),
        ]
        assert _get_pending_activity(zero_value_holdings) == 0.0

    def test_process_portfolio_with_pending_activity(self):
        """Test that process_portfolio correctly handles pending activity."""
        # Create test holdings with pending activity
        holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150.0,
                value=1500.0,
            ),
            PortfolioHolding(
                symbol="PENDING ACTIVITY",
                description="Pending Activity",
                quantity=1,
                price=0.0,
                value=500.0,
            ),
        ]

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock to return False for is_cash_like
            mock_oracle.is_cash_like.return_value = False
            mock_oracle.get_beta.return_value = 1.0

            # Process the portfolio
            portfolio = process_portfolio(holdings)
            summary = create_portfolio_summary(portfolio)

            # Check that pending activity is correctly extracted
            assert portfolio.pending_activity_value == 500.0
            assert summary.pending_activity_value == 500.0

            # Check that pending activity is not included in the portfolio holdings
            assert len(portfolio.groups) == 1
            assert portfolio.groups[0].ticker == "AAPL"

    def test_process_portfolio_with_fidelity_pending_activity(self):
        """Test that process_portfolio correctly handles Fidelity-style pending activity."""
        # Create test holdings with Fidelity-style pending activity
        # Format: Z26522634,GMX,Pending Activity,,,,,$529535.51,,,,,,,,
        holdings = [
            PortfolioHolding(
                symbol="AAPL",
                description="APPLE INC",
                quantity=10,
                price=150.0,
                value=1500.0,
            ),
            PortfolioHolding(
                symbol="Pending Activity",
                description="",
                quantity=0,
                price=0.0,
                value=529535.51,
            ),
        ]

        # Mock the stock oracle to avoid external API calls
        with patch("src.folib.services.portfolio_service.stockdata") as mock_oracle:
            # Configure the mock to return False for is_cash_like
            mock_oracle.is_cash_like.return_value = False
            mock_oracle.get_beta.return_value = 1.0

            # Process the portfolio
            portfolio = process_portfolio(holdings)
            summary = create_portfolio_summary(portfolio)

            # Check that pending activity is correctly extracted
            assert portfolio.pending_activity_value == 529535.51
            assert summary.pending_activity_value == 529535.51

            # Check that pending activity is not included in the portfolio holdings
            assert len(portfolio.groups) == 1
            assert portfolio.groups[0].ticker == "AAPL"
