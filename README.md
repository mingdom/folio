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

# Folio - Financial Portfolio Dashboard

Folio is a powerful web-based dashboard for analyzing and optimizing your investment portfolio. Get professional-grade insights into your stocks, options, and other financial instruments with an intuitive, user-friendly interface.

## Why Folio?

- **Complete Portfolio Visibility**: See your entire financial picture in one place
- **Smart Risk Assessment**: Understand your portfolio's risk profile with beta analysis
- **Cash & Equivalents Detection**: Automatically identifies money market and cash-like positions
- **Option Analytics**: Detailed metrics for options including delta exposure and notional value
- **Zero Cost**: Free to use, with no hidden fees or subscriptions

## Key Features

- **Portfolio Summary**: View total exposure, beta, and allocation breakdown
- **Position Details**: Analyze individual positions with detailed metrics
- **Position Grouping**: Automatically groups stocks with their related options
- **P&L Visualization**: See potential profit/loss scenarios for option strategies
- **Filtering & Sorting**: Filter by position type and sort by various metrics
- **Real-time Data**: Uses Yahoo Finance API for up-to-date market data
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Getting Started

### Try It Online

The easiest way to try Folio is through our Hugging Face Spaces deployment:
[https://huggingface.co/spaces/mingdom/folio](https://huggingface.co/spaces/mingdom/folio)

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
   make folio
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
   make focli
   ```

3. **Working with Poetry's environment**:
   ```bash
   # Activate Poetry's shell (recommended for development)
   poetry shell

   # After activating, you can run commands directly:
   python -m src.folio.app
   pytest
   ruff check .
   ```

For detailed Poetry commands and information, see [docs/Poetry.md](docs/Poetry.md).

### Docker Deployment

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

## Using Folio

1. **Upload Your Portfolio**: Use the upload button to import a CSV file with your holdings
2. **Explore Your Data**: View summary metrics and detailed breakdowns of your investments
3. **Filter and Sort**: Focus on specific asset types or metrics that matter to you
4. **Analyze Positions**: Click on any position to see detailed metrics and P&L scenarios
5. **Export or Share**: Save your analysis or share insights with your financial advisor

## Sample Portfolio

Not ready to upload your own data? Click the "Load Sample Portfolio" button to explore Folio with our demo data.

## Privacy & Security

- **Your Data Stays Private**: All analysis happens in your browser or local environment
- **No Account Required**: Use Folio without creating an account or sharing personal information
- **Open Source**: All code is transparent and available for review

## License

This project is licensed under the MIT License - see the LICENSE file for details.
