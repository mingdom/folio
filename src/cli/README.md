# Folio CLI

A command-line interface for portfolio analysis and simulation, leveraging the `folib` library for core business logic.

## Features

- Load and analyze portfolio data from CSV files
- View portfolio summary metrics and exposures
- List and filter portfolio positions
- Analyze individual positions and their risk metrics
- Interactive shell mode for exploratory analysis

## Usage

### Direct Execution Mode

```bash
# Load a portfolio
python -m src.cli portfolio load path/to/portfolio.csv

# Display portfolio summary
python -m src.cli portfolio summary --file path/to/portfolio.csv

# List portfolio positions
python -m src.cli portfolio list --file path/to/portfolio.csv --type stock --sort value:desc

# Analyze a position
python -m src.cli position SPY details --file path/to/portfolio.csv

# Analyze position risk
python -m src.cli position SPY risk --file path/to/portfolio.csv --show-greeks
```

### Interactive Shell Mode

```bash
# Start the interactive shell
python -m src.cli

# In the shell
folio> portfolio load path/to/portfolio.csv
folio> portfolio summary
folio> portfolio list --type stock --sort value:desc
folio> position SPY details
folio> position SPY risk --show-greeks
folio> help
folio> exit
```

## Default Portfolio

If no portfolio file is specified, the CLI will attempt to load the default portfolio from `private-data/portfolios/portfolio-default.csv`.

## Command Reference

### Portfolio Commands

- `portfolio load <FILE_PATH>`: Load portfolio data from a CSV file
- `portfolio summary`: Display high-level portfolio metrics
- `portfolio list [options]`: List positions with filtering and sorting
  - `--type [stock|option|cash]`: Filter by position type
  - `--focus <TICKERS>`: Focus on specific tickers (comma-separated)
  - `--min-value <VAL>`: Minimum position value
  - `--max-value <VAL>`: Maximum position value
  - `--sort <FIELD[:DIRECTION]>`: Sort by field (ticker, value, beta, exposure)

### Position Commands

- `position <TICKER> details [options]`: View detailed composition of a position
  - `--show-legs`: Show detailed option leg information
- `position <TICKER> risk [options]`: Analyze risk metrics for a position
  - `--show-greeks`: Show option Greeks

### Utility Commands

- `help [COMMAND]`: Display help information
- `exit`: Terminate the interactive session (interactive mode only)

## Testing

### E2E Tests

Run the E2E test scripts to verify the CLI functionality:

```bash
# Test portfolio commands
./src/cli/tests/e2e/test_portfolio_commands.sh

# Test position commands
./src/cli/tests/e2e/test_position_commands.sh
```

### Interactive Testing

Launch the interactive shell and explore the CLI functionality:

```bash
python -m src.cli
```
