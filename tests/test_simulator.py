"""Tests for the simulator module."""

import pytest

from src.folio.data_model import (
    ExposureBreakdown,
    OptionPosition,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
)
from src.folio.simulator import (
    calculate_percentage_changes,
    simulate_portfolio_with_spy_changes,
)


@pytest.fixture
def sample_stock_position():
    """Create a sample stock position for testing."""
    return StockPosition(
        ticker="AAPL",
        quantity=10,
        beta=1.2,
        market_exposure=1000.0,
        beta_adjusted_exposure=1200.0,
        price=100.0,
        position_type="stock",
        cost_basis=90.0,
        market_value=1000.0,
    )


@pytest.fixture
def sample_option_position():
    """Create a sample option position for testing."""
    return OptionPosition(
        ticker="AAPL",
        position_type="option",
        quantity=1,
        beta=1.2,
        beta_adjusted_exposure=600.0,
        strike=100.0,
        expiry="2025-01-01",
        option_type="CALL",
        delta=0.5,
        delta_exposure=500.0,
        notional_value=1000.0,
        underlying_beta=1.2,
        market_exposure=500.0,
        price=5.0,
        cost_basis=4.0,
        market_value=500.0,
    )


@pytest.fixture
def sample_portfolio_group(sample_stock_position, sample_option_position):
    """Create a sample portfolio group for testing."""
    return PortfolioGroup(
        ticker="AAPL",
        stock_position=sample_stock_position,
        option_positions=[sample_option_position],
        net_exposure=1500.0,
        beta=1.2,
        beta_adjusted_exposure=1800.0,
        total_delta_exposure=500.0,
        options_delta_exposure=500.0,
    )


@pytest.fixture
def sample_portfolio_summary():
    """Create a sample portfolio summary for testing."""
    # Create exposure breakdowns
    long_exposure = ExposureBreakdown(
        stock_exposure=1000.0,
        stock_beta_adjusted=1200.0,
        option_delta_exposure=500.0,
        option_beta_adjusted=600.0,
        total_exposure=1500.0,
        total_beta_adjusted=1800.0,
        description="Long exposure",
        formula="Stock + Options",
        components={
            "Long Stocks Value": 1000.0,
            "Long Options Value": 500.0,
        },
    )

    short_exposure = ExposureBreakdown(
        stock_exposure=0.0,
        stock_beta_adjusted=0.0,
        option_delta_exposure=0.0,
        option_beta_adjusted=0.0,
        total_exposure=0.0,
        total_beta_adjusted=0.0,
        description="Short exposure",
        formula="Stock + Options",
        components={
            "Short Stocks Value": 0.0,
            "Short Options Value": 0.0,
        },
    )

    options_exposure = ExposureBreakdown(
        stock_exposure=0.0,
        stock_beta_adjusted=0.0,
        option_delta_exposure=500.0,
        option_beta_adjusted=600.0,
        total_exposure=500.0,
        total_beta_adjusted=600.0,
        description="Options exposure",
        formula="Options",
        components={
            "Long Options Delta Exp": 500.0,
            "Short Options Delta Exp": 0.0,
            "Net Options Delta Exp": 500.0,
        },
    )

    return PortfolioSummary(
        net_market_exposure=1500.0,
        portfolio_beta=1.2,
        long_exposure=long_exposure,
        short_exposure=short_exposure,
        options_exposure=options_exposure,
        short_percentage=0.0,
        cash_like_positions=[],
        cash_like_value=0.0,
        cash_like_count=0,
        cash_percentage=0.0,
        stock_value=1000.0,
        option_value=500.0,
        portfolio_estimate_value=1500.0,
    )


def test_calculate_percentage_changes():
    """Test the calculate_percentage_changes function."""
    values = [100.0, 110.0, 90.0, 120.0]
    base_value = 100.0

    expected = [0.0, 10.0, -10.0, 20.0]
    result = calculate_percentage_changes(values, base_value)

    # Use pytest.approx to handle floating-point precision issues
    assert pytest.approx(result) == expected


def test_calculate_percentage_changes_with_zero_base():
    """Test the calculate_percentage_changes function with zero base value."""
    values = [100.0, 110.0, 90.0, 120.0]
    base_value = 0.0

    expected = [0.0, 0.0, 0.0, 0.0]
    result = calculate_percentage_changes(values, base_value)

    assert result == expected


def test_simulate_portfolio_with_spy_changes(sample_portfolio_group, monkeypatch):
    """Test the simulate_portfolio_with_spy_changes function."""

    # Mock the recalculate_portfolio_with_prices function
    def mock_recalculate(
        groups,
        price_adjustments,
        cash_like_positions=None,  # noqa: ARG001
        pending_activity_value=0.0,  # noqa: ARG001
    ):
        # Simple mock that returns the original groups and a summary with adjusted values
        from src.folio.data_model import ExposureBreakdown, PortfolioSummary

        # Get the AAPL adjustment factor
        adjustment = price_adjustments.get("AAPL", 1.0)

        # Create a mock summary with adjusted values
        empty_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=0.0,
            option_beta_adjusted=0.0,
            total_exposure=0.0,
            total_beta_adjusted=0.0,
            description="Empty",
            formula="N/A",
            components={},
        )

        summary = PortfolioSummary(
            net_market_exposure=1500.0 * adjustment,
            portfolio_beta=1.2,
            long_exposure=empty_exposure,
            short_exposure=empty_exposure,
            options_exposure=empty_exposure,
            short_percentage=0.0,
            cash_like_positions=[],
            cash_like_value=0.0,
            cash_like_count=0,
            cash_percentage=0.0,
            stock_value=1000.0 * adjustment,
            option_value=500.0 * adjustment,
            portfolio_estimate_value=1500.0 * adjustment,
        )

        return groups, summary

    # Apply the monkeypatch
    import src.folio.simulator

    monkeypatch.setattr(
        src.folio.simulator, "recalculate_portfolio_with_prices", mock_recalculate
    )

    # Test with default spy_changes
    result = simulate_portfolio_with_spy_changes(
        portfolio_groups=[sample_portfolio_group],
        spy_changes=[-0.1, 0.0, 0.1],
    )

    # Check the structure of the result
    assert "spy_changes" in result
    assert "portfolio_values" in result
    assert "portfolio_exposures" in result
    assert "current_value" in result
    assert "current_exposure" in result

    # Check the values
    assert result["spy_changes"] == [-0.1, 0.0, 0.1]

    # For a beta of 1.2:
    # At -10% SPY change: adjustment = 1 + (-0.1 * 1.2) = 0.88
    # At 0% SPY change: adjustment = 1 + (0 * 1.2) = 1.0
    # At 10% SPY change: adjustment = 1 + (0.1 * 1.2) = 1.12
    expected_values = [1500.0 * 0.88, 1500.0, 1500.0 * 1.12]
    expected_exposures = [1500.0 * 0.88, 1500.0, 1500.0 * 1.12]

    # Check with a small tolerance for floating point errors
    assert pytest.approx(result["portfolio_values"]) == expected_values
    assert pytest.approx(result["portfolio_exposures"]) == expected_exposures
    assert pytest.approx(result["current_value"]) == 1500.0
    assert pytest.approx(result["current_exposure"]) == 1500.0


def test_simulate_empty_portfolio():
    """Test simulating an empty portfolio."""
    result = simulate_portfolio_with_spy_changes(
        portfolio_groups=[],
        spy_changes=[-0.1, 0.0, 0.1],
    )

    assert result["spy_changes"] == []
    assert result["portfolio_values"] == []
    assert result["portfolio_exposures"] == []
    assert result["current_value"] == 0.0
    assert result["current_exposure"] == 0.0
