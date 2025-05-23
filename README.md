---
title: Folio - Financial Portfolio Dashboard
emoji: 📊
colorFrom: indigo
colorTo: purple
sdk: docker
sdk_version: "latest"
app_file: app.py
pinned: false
---

## Project Focus

The Folio project is currently focused on the command-line interface (`src/cli`) as the primary way to interact with the portfolio analysis tools. The web interface (`src/folio/`) is considered deprecated and is not actively maintained. All core business logic resides in the `src/folib/` library.

# Folio - Financial Portfolio Dashboard

Folio is a powerful web-based dashboard for analyzing and optimizing your investment portfolio. Get professional-grade insights into your stocks, options, and other financial instruments with an intuitive, user-friendly interface.

## Why Folio?

- **Comprehensive Portfolio Analysis**: Get a detailed overview of your financial holdings.
- **Smart Risk Assessment**: Understand your portfolio's risk profile with beta analysis
- **Cash & Equivalents Detection**: Automatically identifies money market and cash-like positions
- **Option Analytics**: Detailed metrics for options including delta exposure and notional value
- **Zero Cost**: Free to use, with no hidden fees or subscriptions

## Key Features

- **Portfolio Summary**: View total exposure, beta, and allocation breakdown
- **Position Details**: Analyze individual positions with detailed metrics
- **Position Grouping**: Automatically groups stocks with their related options
- **Filtering & Sorting**: Filter by position type and sort by various metrics
- **Real-time Data**: Uses Yahoo Finance API for up-to-date market data

## Getting Started

### Local Installation

1. **Install Poetry**:
   We use `poetry` under the hood to manage dependencies.
   ```bash
   # For macOS/Linux
   curl -sSL https://install.python-poetry.org | python3 -

   # For Windows
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```
   For detailed installation instructions, visit [Poetry's official documentation](https://python-poetry.org/docs/#installation).

2. **Clone the repository**:
   ```bash
   git clone https://github.com/mingdom/folio.git
   cd folio
   ```

3. **Install dependencies**:
   ```bash
   # Using Poetry
   poetry install
   poetry env activate

   # Using Make:
   make install
   make env
   ```

4. **Run the application**:
   ```bash
   make cli
   ```

### Development Workflow

Our project uses Poetry for dependency management and Make for convenient command shortcuts.

1. **Set up pre-commit hooks**:
   ```bash
   make hooks
   ```

2. **Common development commands**:
   ```bash
   # Run linting
   make lint

   # Run tests
   make test

   # Start the interactive CLI (includes SPY simulator functionality)
   make cli
   ```

3. **Working with Poetry's environment**:
   ```bash
   # Activate Poetry's shell (recommended for development)
   poetry shell

   # After activating, you can run commands directly:
   python -m src.cli
   pytest
   ruff check .
   ```

For detailed Poetry commands and information, see [docs/Poetry.md](docs/Poetry.md).

### Docker Deployment

**Note:** The Docker deployment runs the deprecated web interface and is not recommended for the primary CLI usage.

```bash
# Start the application
make docker-up

# View logs
make docker-logs

# Stop the application
make docker-down
```

The dashboard will be available at http://localhost:8050

### Documentation

- [Docker Commands](DOCKER.md) - Detailed Docker usage
- [Logging Configuration](docs/logging.md) - Configure logging
- [Project Architecture](docs/project-design.md) - Codebase structure and design
- [Poetry Commands](docs/Poetry.md) - Detailed Poetry usage

## Using Folio (CLI)

The Folio CLI provides various commands to analyze your portfolio. Here's a general workflow:

1. **Prepare Your Portfolio CSV**: Ensure your portfolio data is in a CSV file format. Refer to `sample-data/sample-portfolio.csv` for an example.
2. **Run Commands**: Use commands like `portfolio`, `position`, `summary`, etc., to view different aspects of your portfolio.
   ```bash
   # Example: View portfolio summary
   python -m src.cli summary --portfolio path/to/your/portfolio.csv
   ```
3. **Explore Options**: Most commands offer options for filtering, sorting, and customizing the output. Use the `--help` flag with any command to see available options.
   ```bash
   python -m src.cli summary --help
   ```
4. **Analyze Data**: Interpret the output to gain insights into your investments. The CLI provides detailed metrics for individual positions and overall portfolio performance.

## Sample Portfolio

You can use the sample portfolio data located at `sample-data/sample-portfolio.csv` to explore Folio's CLI features.

For example, to view the summary of the sample portfolio:
```bash
python -m src.cli summary --portfolio sample-data/sample-portfolio.csv
```

## Privacy & Security

- **Your Data Stays Private**: All analysis happens in your local environment.
- **No Account Required**: Use Folio without creating an account or sharing personal information.
- **Open Source**: All code is transparent and available for review.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
