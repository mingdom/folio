import os
import shutil
import pytest
import pandas # Added pandas import as per subtask description
from typer.testing import CliRunner

from src.cli.main import app

# Path to the test portfolio CSV
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(TEST_DIR, "..", "assets")
TEST_PORTFOLIO_PATH = os.path.join(ASSETS_DIR, "test_portfolio.csv")
TEMP_PORTFOLIO_DIR = os.path.join(TEST_DIR, "temp_test_data") # For temporary test files
TEMP_PORTFOLIO_PATH = os.path.join(TEMP_PORTFOLIO_DIR, "test_portfolio_copy.csv")


@pytest.fixture(scope="function")
def runner():
    """Fixture to provide a CliRunner for invoking CLI commands."""
    return CliRunner()


@pytest.fixture(scope="function")
def temp_portfolio_file():
    """Fixture to provide a temporary copy of the test portfolio for each test."""
    os.makedirs(TEMP_PORTFOLIO_DIR, exist_ok=True)
    shutil.copy(TEST_PORTFOLIO_PATH, TEMP_PORTFOLIO_PATH)
    yield TEMP_PORTFOLIO_PATH
    shutil.rmtree(TEMP_PORTFOLIO_DIR)


class TestPositionCommand:
    def test_position_ticker_not_found(self, runner, temp_portfolio_file):
        result = runner.invoke(
            app, ["position", "analyze", "NONEXISTENTTICKER", "-f", temp_portfolio_file]
        )
        assert result.exit_code == 1 # Expecting exit code 1 for errors
        assert "Error: Ticker NONEXISTENTTICKER not found in portfolio" in result.stdout

    def test_position_stock_details_googl(self, runner, temp_portfolio_file):
        result = runner.invoke(app, ["position", "analyze", "GOOGL", "-f", temp_portfolio_file])
        assert result.exit_code == 0
        stdout = result.stdout

        # Stock Details
        assert "[bold]Position Details for GOOGL[/bold]" in stdout
        assert "GOOGL Stock Positions" in stdout
        assert "Quantity" in stdout and "Price" in stdout and "Value" in stdout and "Cost Basis" in stdout
        assert "2,600.00" in stdout  # GOOGL Stock Quantity from CSV
        assert "$155.75" in stdout   # GOOGL Stock Price from CSV
        assert "$404,950.00" in stdout # GOOGL Stock Value from CSV

        # Option Summary (default behavior when --show-legs is not passed)
        assert "GOOGL Option Summary" in stdout
        assert "# of Options" in stdout and "Total Value" in stdout
        # GOOGL has 5 option contracts listed in test_portfolio.csv
        assert "5" in stdout # Count of GOOGL option contracts

        # Risk Analysis
        assert "[bold]Risk Analysis for GOOGL[/bold]" in stdout
        assert "GOOGL Risk Metrics" in stdout
        assert "Market Exposure" in stdout
        assert "Beta-Adjusted Exposure" in stdout
        # Beta is sometimes hard to get for all tickers, so this check is broad.
        # If Beta is consistently available for GOOGL from the service, a specific value could be checked.

        # Greeks should not be displayed by default
        assert "GOOGL Option Greeks" not in stdout

    def test_position_option_details_with_legs_amzn(self, runner, temp_portfolio_file):
        result = runner.invoke(
            app, ["position", "analyze", "AMZN", "-f", temp_portfolio_file, "--show-legs"]
        )
        assert result.exit_code == 0
        stdout = result.stdout

        # Stock Details for AMZN
        assert "[bold]Position Details for AMZN[/bold]" in stdout
        assert "AMZN Stock Positions" in stdout
        assert "1,400.00" in stdout # AMZN Stock Quantity
        assert "$193.10" in stdout  # AMZN Stock Price (193.0999 rounded)
        assert "$270,339.86" in stdout # AMZN Stock Value

        # Option Details (with legs)
        assert "AMZN Option Positions" in stdout
        assert "Type" in stdout and "Strike" in stdout and "Expiry" in stdout
        assert "Quantity" in stdout and "Price" in stdout and "Value" in stdout

        # Specific AMZN option leg: -AMZN250516C190 (CALL, Strike 190, Expiry 2025-05-16, Qty -7.0, Price $5.80)
        assert "CALL" in stdout
        assert "$190.00" in stdout # Strike
        assert "2025-05-16" in stdout # Expiry
        assert "-7.00" in stdout # Quantity
        assert "$5.80" in stdout # Price

        # Greeks should not be displayed if --show-greeks is not passed
        assert "AMZN Option Greeks" not in stdout

    def test_position_option_summary_without_legs_amzn(self, runner, temp_portfolio_file):
        result = runner.invoke(app, ["position", "analyze", "AMZN", "-f", temp_portfolio_file])
        assert result.exit_code == 0
        stdout = result.stdout

        # Option Summary for AMZN
        assert "AMZN Option Summary" in stdout
        assert "# of Options" in stdout and "Total Value" in stdout
        # AMZN has 5 option contracts in test_portfolio.csv
        assert "5" in stdout

    def test_position_option_with_greeks_amzn(self, runner, temp_portfolio_file):
        result = runner.invoke(
            app,
            [
                "position",
                "analyze",
                "AMZN",
                "-f",
                temp_portfolio_file,
                "--show-greeks", # --show-legs is not required to show greeks
            ],
        )
        assert result.exit_code == 0
        stdout = result.stdout

        # Greeks table should be present
        assert "AMZN Option Greeks" in stdout
        assert "Delta" in stdout
        # The exact delta value depends on calculations from `folib`
        # and external data, so we only check for the presence of "Delta".

    def test_position_mixed_stock_and_options_amzn(self, runner, temp_portfolio_file):
        # This test ensures both stock and option sections appear for a mixed position like AMZN.
        result = runner.invoke(app, ["position", "analyze", "AMZN", "-f", temp_portfolio_file])
        assert result.exit_code == 0
        stdout = result.stdout

        # Stock Details
        assert "AMZN Stock Positions" in stdout
        assert "1,400.00" in stdout # AMZN Stock Quantity

        # Option Summary (default when --show-legs is not used)
        assert "AMZN Option Summary" in stdout
        assert "5" in stdout # Number of AMZN option contracts

        # Risk Analysis
        assert "[bold]Risk Analysis for AMZN[/bold]" in stdout
        assert "AMZN Risk Metrics" in stdout

    def test_position_file_not_found(self, runner):
        result = runner.invoke(
            app, ["position", "analyze", "GOOGL", "-f", "nonexistent_portfolio.csv"]
        )
        assert result.exit_code == 1 # Error code from load_portfolio
        assert "Error: Portfolio file not found at path: nonexistent_portfolio.csv" in result.stdout

    def test_position_only_stock_no_options_msci(self, runner, temp_portfolio_file):
        # MSCI has only stock positions in test_portfolio.csv
        result = runner.invoke(app, ["position", "analyze", "MSCI", "-f", temp_portfolio_file])
        assert result.exit_code == 0
        stdout = result.stdout

        # Stock Details
        assert "[bold]Position Details for MSCI[/bold]" in stdout
        assert "MSCI Stock Positions" in stdout
        assert "80.00" in stdout    # MSCI Stock Quantity
        assert "$558.31" in stdout  # MSCI Stock Price
        assert "$44,664.80" in stdout # MSCI Stock Value

        # Option Section should indicate no options
        assert "No option positions found for MSCI" in stdout
        assert "MSCI Option Summary" not in stdout
        assert "MSCI Option Positions" not in stdout

        # Risk Analysis should still be present
        assert "[bold]Risk Analysis for MSCI[/bold]" in stdout
        assert "MSCI Risk Metrics" in stdout

    def test_position_only_options_no_stock_crm(self, runner, temp_portfolio_file):
        # CRM has only option positions in test_portfolio.csv
        result = runner.invoke(app, ["position", "analyze", "CRM", "-f", temp_portfolio_file, "--show-legs"])
        assert result.exit_code == 0
        stdout = result.stdout

        # Stock Section should indicate no stock
        assert "[bold]Position Details for CRM[/bold]" in stdout
        assert "No stock positions found for CRM" in stdout
        assert "CRM Stock Positions" not in stdout

        # Option Details (with legs)
        assert "CRM Option Positions" in stdout
        assert "Type" in stdout and "Strike" in stdout and "Expiry" in stdout
        # CRM has 3 option contracts in the CSV. Check for presence of one type.
        assert "PUT" in stdout # e.g., -CRM250620P290
        assert "CALL" in stdout # e.g., -CRM250919C290
        # Check for a specific detail to confirm legs are shown, e.g. a strike price for CRM option
        assert "$290.00" in stdout # Strike for -CRM250620P290 or -CRM250919C290

        # Risk Analysis
        assert "[bold]Risk Analysis for CRM[/bold]" in stdout
        assert "CRM Risk Metrics" in stdout

        # If --show-greeks is passed, Greeks table should be shown
        result_with_greeks = runner.invoke(app, ["position", "analyze", "CRM", "-f", temp_portfolio_file, "--show-greeks"])
        assert result_with_greeks.exit_code == 0
        assert "CRM Option Greeks" in result_with_greeks.stdout
        assert "Delta" in result_with_greeks.stdout
```
