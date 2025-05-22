# Folio CLI

A command-line interface for portfolio analysis and simulation, leveraging the `folib` library for core business logic.

## Features

- Load and analyze portfolio data from CSV files
- View portfolio summary metrics and exposures
- List and filter portfolio positions
- Analyze individual positions and their risk metrics
- Interactive shell mode for exploratory analysis

## Getting Started

### Installation

The CLI is part of the Folio project. To use it, you can run:

```bash
# Using make (recommended)
make cli

# Or directly with Python
python -m src.cli
```

### Default Portfolio

If no portfolio file is specified, the CLI will automatically load the default portfolio from `private-data/portfolios/portfolio-default.csv` and display the portfolio summary.

## Usage Modes

### Interactive Shell Mode

The interactive shell provides a persistent session where you can enter commands and maintain state between commands.

```bash
# Start the interactive shell
make cli

# In the shell
folio> portfolio summary
folio> portfolio list type=stock
folio> position SPY details
folio> help
folio> exit
```

### Direct Execution Mode

Every feature is also accessible via direct command calls from the system shell:

```bash
# Display portfolio summary
python -m src.cli portfolio summary --file path/to/portfolio.csv

# List portfolio positions
python -m src.cli portfolio list --file path/to/portfolio.csv type=stock sort=value:desc

# Analyze a position
python -m src.cli position SPY --file path/to/portfolio.csv
```

## Command Reference

### Portfolio Commands

- `portfolio load <FILE_PATH>`
  - Load portfolio data from a CSV file
  - Example: `portfolio load private-data/portfolios/my-portfolio.csv`

- `portfolio summary`
  - Display high-level portfolio metrics including value, exposures, and risk metrics
  - Example: `portfolio summary`

- `portfolio list [filters]`
  - List positions with filtering and sorting
  - Filters:
    - `type=<stock|option|cash>`: Filter by position type
    - `symbol=<TICKER>`: Filter by symbol
    - `min_value=<VALUE>`: Minimum position value
    - `max_value=<VALUE>`: Maximum position value
    - `sort=<FIELD[:DIRECTION]>`: Sort by field (ticker, value, beta, exposure)
  - Examples:
    - `portfolio list type=stock`
    - `portfolio list symbol=AAPL`
    - `portfolio list type=option sort=value:desc`
    - `portfolio list min_value=10000 max_value=50000`

### Position Commands

- `position <TICKER> [options]`
  - Analyze a position group showing both detailed composition and risk metrics
  - Options:
    - `--show-legs`: Show detailed option leg information
    - `--show-greeks`: Show option Greeks (Delta, Gamma, Theta, Vega)
  - Examples:
    - `position SPY` - Basic position analysis
    - `position --show-legs SPY` - Show detailed option legs
    - `position --show-greeks AAPL` - Include option Greeks
    - `position --show-legs --show-greeks TSLA` - Show both legs and Greeks

### Utility Commands

- `help [COMMAND]`
  - Display help information for all commands or a specific command
  - Examples:
    - `help` - Show general help
    - `help portfolio` - Show help for portfolio commands
    - `help position` - Show help for position commands

- `exit`
  - Terminate the interactive session (interactive mode only)

## Examples

### Basic Portfolio Analysis

```
# Load a portfolio
folio> portfolio load private-data/portfolios/portfolio-default.csv

# View portfolio summary
folio> portfolio summary

# List all positions sorted by value
folio> portfolio list sort=value:desc

# List only stock positions
folio> portfolio list type=stock
```

### Position Analysis

```
# Analyze a specific position (shows both details and risk metrics)
folio> position SPY

# Include option Greeks in the analysis
folio> position --show-greeks AAPL

# Show detailed option legs
folio> position --show-legs TSLA

# Show both option legs and Greeks
folio> position --show-legs --show-greeks AAPL
```

## Tips and Tricks

- Use the up/down arrow keys to navigate command history
- Tab completion is available for commands
- The CLI automatically loads the default portfolio on startup
- Portfolio summary is displayed automatically on startup
- Use `help` command to see available commands and options

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
make cli
```
