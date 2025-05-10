"""
Critical tests for portfolio parsing functionality.

This module contains critical tests for the portfolio parsing functionality,
focusing on ensuring that all positions (especially options) are correctly
parsed from portfolio CSV files.

These tests are marked as 'critical' because they verify core functionality
that directly impacts user experience. Failures in these tests indicate
serious issues that must be addressed immediately.

The tests specifically focus on:
1. Correct parsing of option positions, especially those paired with stocks
2. Handling of option symbols with leading spaces or hyphens
3. Ensuring all positions from the CSV are included in the final portfolio

Performance optimizations:
- Module-scoped fixtures to avoid redundant file loading and parsing
- Precompiled regex patterns for faster string matching
- Reduced logging during test execution
"""

import logging
import re
from pathlib import Path

import pytest

from src.folib.data.loader import load_portfolio_from_csv, parse_portfolio_holdings
from src.folib.services.portfolio_service import process_portfolio

# Precompile regex patterns for better performance
OPTION_PATTERN = re.compile(r"CALL|PUT", re.IGNORECASE)
TICKER_PATTERN = re.compile(r"[A-Z]+")
LEADING_HYPHEN_PATTERN = re.compile(r"^\s*-|^\s+-")


@pytest.fixture(scope="module", autouse=True)
def reduce_logging():
    """Reduce logging level during tests to improve performance."""
    # Store original logging levels
    original_levels = {
        "src.folib": logging.getLogger("src.folib").level,
        "src.folio": logging.getLogger("src.folio").level,
    }

    # Set to ERROR level to reduce logging overhead
    logging.getLogger("src.folib").setLevel(logging.ERROR)
    logging.getLogger("src.folio").setLevel(logging.ERROR)

    yield

    # Restore original logging levels
    for logger_name, level in original_levels.items():
        logging.getLogger(logger_name).setLevel(level)


@pytest.fixture(scope="module")
def test_portfolio_path():
    """Return the path to the test portfolio CSV file."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    portfolio_path = project_root / "tests" / "assets" / "test_portfolio.csv"
    assert portfolio_path.exists(), f"Test portfolio file not found at {portfolio_path}"
    return portfolio_path


@pytest.fixture(scope="module")
def test_portfolio_df(test_portfolio_path):
    """Return the loaded DataFrame from the test portfolio CSV file."""
    return load_portfolio_from_csv(test_portfolio_path)


@pytest.fixture(scope="module")
def test_portfolio_holdings(test_portfolio_df):
    """Return the parsed holdings from the test portfolio CSV file."""
    return parse_portfolio_holdings(test_portfolio_df)


@pytest.fixture(scope="module")
def processed_portfolio(test_portfolio_holdings):
    """Return a processed portfolio that can be reused across tests."""
    return process_portfolio(test_portfolio_holdings)


@pytest.mark.critical
def test_option_positions_parsing(test_portfolio_df, processed_portfolio):
    """
    CRITICAL TEST: Verify that all option positions are correctly parsed from the portfolio CSV.

    This test ensures that all option positions, especially those paired with stocks
    (like SPY options paired with SPY stock), are correctly parsed and included in the
    final portfolio. It specifically checks for options with symbols that have leading
    spaces or hyphens, which have been problematic in the past.

    Failure in this test indicates a serious issue with the portfolio parsing logic
    that would result in missing positions for users.
    """
    # Use the cached DataFrame from the fixture
    df = test_portfolio_df

    # Count option positions in the raw CSV by looking for "CALL" or "PUT" in the description
    # Handle NaN values in the Description column
    df["Description"] = df["Description"].fillna("")
    option_rows = df[df["Description"].str.contains(OPTION_PATTERN)]
    expected_option_count = len(option_rows)

    # Get the option symbols from the CSV for later verification
    option_symbols = option_rows["Symbol"].tolist()

    # Use the processed portfolio from the fixture
    portfolio = processed_portfolio

    # Get the actual option positions from the processed portfolio
    actual_option_positions = portfolio.option_positions
    actual_option_count = len(actual_option_positions)

    # Verify the counts match
    assert actual_option_count == expected_option_count, (
        f"Expected {expected_option_count} option positions, but got {actual_option_count}. "
        f"Some option positions are missing from the processed portfolio."
    )

    # Check for specific problematic patterns: options paired with stocks
    # First, get all stock tickers
    stock_tickers = set(pos.ticker for pos in portfolio.stock_positions)

    # Then, find options that have the same underlying as a stock position
    paired_option_symbols = [
        symbol
        for symbol in option_symbols
        if any(stock_ticker in symbol for stock_ticker in stock_tickers)
    ]

    # Verify that all paired options are in the processed portfolio
    for symbol in paired_option_symbols:
        # Extract the underlying ticker from the option symbol
        # Option symbols might have formats like " -SPY250516P550" or similar
        match = TICKER_PATTERN.search(symbol.strip("-").strip())
        if match:
            underlying_ticker = match.group(0)

            # Check if any option position in the portfolio has this underlying
            found = False
            for pos in actual_option_positions:
                if pos.ticker == underlying_ticker:
                    found = True
                    break

            assert found, (
                f"Option with underlying {underlying_ticker} (symbol: {symbol}) "
                f"is missing from the processed portfolio, despite being paired with a stock."
            )

    # Specifically check for SPY options, which were mentioned as problematic
    spy_option_symbols = [s for s in option_symbols if "SPY" in s]
    spy_options_in_portfolio = [
        pos for pos in actual_option_positions if pos.ticker == "SPY"
    ]

    assert len(spy_option_symbols) == len(spy_options_in_portfolio), (
        f"Expected {len(spy_option_symbols)} SPY option positions, "
        f"but found {len(spy_options_in_portfolio)}. "
        f"SPY options in CSV: {spy_option_symbols}, "
        f"SPY options in portfolio: {[pos.ticker for pos in spy_options_in_portfolio]}"
    )


@pytest.mark.critical
def test_option_symbols_with_leading_space_or_hyphen(
    test_portfolio_df, processed_portfolio
):
    """
    CRITICAL TEST: Verify that option symbols with leading spaces or hyphens are correctly parsed.

    This test specifically focuses on option symbols that have leading spaces or hyphens,
    such as " -SPY250516P550", which have been problematic in the past. It ensures that
    these options are correctly identified and included in the final portfolio.

    Failure in this test indicates an issue with the option symbol parsing logic.
    """
    # Use the cached DataFrame from the fixture
    df = test_portfolio_df

    # Find option symbols with leading spaces or hyphens
    # Handle NaN values in the Symbol column
    df["Symbol"] = df["Symbol"].fillna("")
    option_symbols_with_space_or_hyphen = df[
        df["Symbol"].str.strip().str.startswith("-")
        | df["Symbol"].str.contains(LEADING_HYPHEN_PATTERN)
    ]["Symbol"].tolist()

    # Skip the test if no such symbols are found
    if not option_symbols_with_space_or_hyphen:
        pytest.skip("No option symbols with leading spaces or hyphens found in the CSV")

    # Use the processed portfolio from the fixture
    portfolio = processed_portfolio

    # For each problematic symbol, verify it's correctly parsed
    for symbol in option_symbols_with_space_or_hyphen:
        # Get the corresponding row from the CSV
        row = df[df["Symbol"] == symbol].iloc[0]

        # Extract the underlying ticker from the description
        description = row["Description"]
        match = TICKER_PATTERN.search(description)
        if not match:
            continue  # Skip if we can't extract the underlying ticker

        underlying_ticker = match.group(0)

        # Check if there's an option position with this underlying ticker
        found = False
        for pos in portfolio.option_positions:
            if pos.ticker == underlying_ticker:
                found = True
                break

        assert found, (
            f"Option with symbol '{symbol}' (underlying: {underlying_ticker}) "
            f"is missing from the processed portfolio."
        )
