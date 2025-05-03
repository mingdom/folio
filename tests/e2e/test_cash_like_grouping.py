"""Tests for cash-like instrument grouping functionality."""

import pandas as pd
import pytest

from src.folio.data_model import ExposureBreakdown, PortfolioSummary
from src.folio.portfolio import is_cash_or_short_term, process_portfolio_data


def test_is_cash_or_short_term():
    """Test the is_cash_or_short_term function."""
    # Test with beta values
    assert is_cash_or_short_term("SPAXX", beta=0.0) is True
    assert is_cash_or_short_term("FDRXX", beta=0.05) is True
    assert is_cash_or_short_term("SHY", beta=0.09) is True
    assert is_cash_or_short_term("SPY", beta=1.0) is False
    assert is_cash_or_short_term("AAPL", beta=1.2) is False

    # Test with negative beta (should still be considered cash-like if abs < 0.1)
    assert is_cash_or_short_term("GOVT", beta=-0.05) is True


def test_cash_like_positions_identification():
    """Test that cash-like positions are correctly identified during processing."""
    # Create a simple test portfolio with cash-like and non-cash-like positions
    data = {
        "Symbol": ["SPAXX", "SPY", "AAPL", "SHY", "CASH"],
        "Description": [
            "FIDELITY GOVERNMENT MONEY MARKET",
            "SPDR S&P 500 ETF TRUST",
            "APPLE INC",
            "ISHARES 1-3 YEAR TREASURY BOND ETF",
            "CASH",
        ],
        "Quantity": [1000, 10, 20, 50, 0],
        "Last Price": [1.00, 450.00, 180.00, 80.00, 0],
        "Current Value": [1000.00, 4500.00, 3600.00, 4000.00, 2000.00],
        "Type": ["Cash", "ETF", "Stock", "ETF", "CASH"],
        "Percent Of Account": ["5%", "22.5%", "18%", "20%", "10%"],
    }
    df = pd.DataFrame(data)

    # Process the portfolio
    groups, summary, cash_like_positions = process_portfolio_data(df)

    # Check that cash-like positions were identified correctly
    assert len(cash_like_positions) == 3  # SPAXX, SHY, and CASH

    # Check that the tickers are correct
    cash_like_tickers = [pos["ticker"] for pos in cash_like_positions]
    assert "SPAXX" in cash_like_tickers
    assert "SHY" in cash_like_tickers
    assert "CASH" in cash_like_tickers
    assert "SPY" not in cash_like_tickers
    assert "AAPL" not in cash_like_tickers

    # Check that the values are correct
    cash_like_values = {
        pos["ticker"]: pos["market_value"] for pos in cash_like_positions
    }
    assert cash_like_values["SPAXX"] == 1000.00
    assert cash_like_values["SHY"] == 4000.00
    assert cash_like_values["CASH"] == 2000.00


def test_portfolio_summary_cash_like_metrics():
    """Test that the portfolio summary includes cash-like metrics."""
    # Create a simple test portfolio
    data = {
        "Symbol": ["SPAXX", "SPY", "AAPL"],
        "Description": [
            "FIDELITY GOVERNMENT MONEY MARKET",
            "SPDR S&P 500 ETF TRUST",
            "APPLE INC",
        ],
        "Quantity": [1000, 10, 20],
        "Last Price": [1.00, 450.00, 180.00],
        "Current Value": [1000.00, 4500.00, 3600.00],
        "Type": ["Cash", "ETF", "Stock"],
        "Percent Of Account": ["10%", "45%", "36%"],
    }
    df = pd.DataFrame(data)

    # Process the portfolio
    groups, summary, cash_like_positions = process_portfolio_data(df)

    # Check that the summary includes cash-like metrics
    assert summary.cash_like_count == 1  # Only SPAXX
    assert summary.cash_like_value == 1000.00
    assert len(summary.cash_like_positions) == 1
    assert summary.cash_like_positions[0].ticker == "SPAXX"
    assert summary.cash_like_positions[0].market_value == 1000.00

    # Check that the cash-like value is included in the total size
    total_size = (
        summary.long_exposure.total_value
        + summary.short_exposure.total_value
        + summary.cash_like_value
    )
    assert total_size >= summary.cash_like_value


def test_empty_portfolio_creation():
    """Test creating an empty portfolio summary."""
    # Create empty exposure breakdowns for testing
    empty_exposure = ExposureBreakdown(
        stock_exposure=0.0,
        stock_beta_adjusted=0.0,
        option_delta_exposure=0.0,
        option_beta_adjusted=0.0,
        total_exposure=0.0,
        total_beta_adjusted=0.0,
        description="Empty exposure",
        formula="N/A",
        components={},
    )

    # Create an empty portfolio summary directly
    summary = PortfolioSummary(
        net_market_exposure=0.0,
        portfolio_beta=0.0,
        long_exposure=empty_exposure,
        short_exposure=empty_exposure,
        options_exposure=empty_exposure,
        short_percentage=0.0,
        cash_like_positions=[],
        cash_like_value=0.0,
        cash_like_count=0,
        cash_percentage=0.0,
        portfolio_estimate_value=0.0,
    )

    # Check that there are no cash-like positions
    assert summary.cash_like_count == 0
    assert summary.cash_like_value == 0.0
    assert len(summary.cash_like_positions) == 0


def test_only_cash_portfolio():
    """Test a portfolio with only cash-like positions."""
    # Create a portfolio with only cash-like positions
    data = {
        "Symbol": ["SPAXX", "FDRXX", "CASH"],
        "Description": [
            "FIDELITY GOVERNMENT MONEY MARKET",
            "FIDELITY CASH RESERVES",
            "CASH",
        ],
        "Quantity": [1000, 2000, 0],
        "Last Price": [1.00, 1.00, 0],
        "Current Value": [1000.00, 2000.00, 3000.00],
        "Type": ["Cash", "Cash", "CASH"],
        "Percent Of Account": ["16.7%", "33.3%", "50%"],
    }
    df = pd.DataFrame(data)

    # Process the portfolio
    groups, summary, cash_like_positions = process_portfolio_data(df)

    # Check that all positions are identified as cash-like
    assert len(cash_like_positions) == 3
    assert summary.cash_like_count == 3
    assert summary.cash_like_value == 6000.00  # Sum of all values

    # Check that the portfolio estimate value equals the cash-like value for an all-cash portfolio
    assert summary.portfolio_estimate_value == summary.cash_like_value

    # Check that the net market exposure is 0 for an all-cash portfolio
    assert summary.net_market_exposure == 0.0

    # Check that the portfolio beta is 0
    assert summary.portfolio_beta == 0.0


def test_position_deduplication():
    """Test that positions with the same ticker are properly combined."""
    # Create a portfolio with duplicate positions
    data = {
        "Symbol": ["TLT", "TLT", "SPAXX", "SPAXX"],
        "Description": [
            "ISHARES 20+ YEAR TREASURY BOND ETF",
            "ISHARES 20+ YEAR TREASURY BOND ETF",
            "FIDELITY GOVERNMENT MONEY MARKET",
            "FIDELITY GOVERNMENT MONEY MARKET",
        ],
        "Quantity": [100, 50, 1000, 2000],
        "Last Price": [100.00, 100.00, 1.00, 1.00],
        "Current Value": [10000.00, 5000.00, 1000.00, 2000.00],
        "Type": ["Cash", "Margin", "Cash", "Margin"],  # Different account types
        "Percent Of Account": ["55.6%", "27.8%", "5.6%", "11.1%"],
    }
    df = pd.DataFrame(data)

    # Process the portfolio
    groups, summary, cash_like_positions = process_portfolio_data(df)

    # Should have 2 cash-like positions (TLT and SPAXX, each combined)
    assert len(cash_like_positions) == 2

    # Find TLT position
    tlt_position = next(pos for pos in cash_like_positions if pos["ticker"] == "TLT")
    assert tlt_position["market_value"] == 15000.00  # Combined value
    assert tlt_position["quantity"] == 150  # Combined quantity

    # Find SPAXX position
    spaxx_position = next(
        pos for pos in cash_like_positions if pos["ticker"] == "SPAXX"
    )
    assert spaxx_position["market_value"] == 3000.00  # Combined value
    assert spaxx_position["quantity"] == 3000  # Combined quantity


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
