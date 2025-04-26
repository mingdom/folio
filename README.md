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
- **AI-Powered Insights**: Get personalized investment advice from our AI portfolio advisor
- **Cash & Equivalents Detection**: Automatically identifies money market and cash-like positions
- **Option Analytics**: Detailed metrics for options including implied volatility and Greeks
- **Zero Cost**: Free to use, with no hidden fees or subscriptions

## Key Features

- **Portfolio Summary**: View total exposure, beta, and allocation breakdown
- **Position Details**: Analyze individual positions with detailed metrics
- **AI Portfolio Advisor**: Get personalized investment advice powered by Google's Gemini AI
- **Filtering & Sorting**: Filter by position type and sort by various metrics
- **Real-time Data**: Uses Yahoo Finance API for up-to-date market data
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Dark Mode**: Easy on the eyes for late-night financial analysis

## Getting Started

### Try It Online

The easiest way to try Folio is through our Hugging Face Spaces deployment:
[https://huggingface.co/spaces/mingdom/folio](https://huggingface.co/spaces/mingdom/folio)

### Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mingdom/folio.git
   cd folio
   ```

2. Set up the environment and install dependencies:
   ```bash
   make env
   make install
   ```

3. Run with sample portfolio:
   ```bash
   make portfolio
   ```

4. Or start with a blank slate:
   ```bash
   make folio
   ```

### Development Setup

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Run linting and tests:
   ```bash
   make lint
   make test
   ```

### Docker Deployment

1. Start the application with Docker:
   ```bash
   make docker-up
   ```

2. Access the dashboard at http://localhost:8050

3. View logs (if needed):
   ```bash
   make docker-logs
   ```

For more Docker commands and options, see [DOCKER.md](DOCKER.md).

For information about logging configuration, see [docs/logging.md](docs/logging.md).

## Using Folio

1. **Upload Your Portfolio**: Use the upload button to import a CSV file with your holdings
2. **Explore Your Data**: View summary metrics and detailed breakdowns of your investments
3. **Filter and Sort**: Focus on specific asset types or metrics that matter to you
4. **Get AI Insights**: Click the "Robot Advisor" button to get personalized advice about your portfolio
5. **Export or Share**: Save your analysis or share insights with your financial advisor

## Sample Portfolio

Not ready to upload your own data? Click the "Load Sample Portfolio" button to explore Folio with our demo data.

## Privacy & Security

- **Your Data Stays Private**: All analysis happens in your browser or local environment
- **No Account Required**: Use Folio without creating an account or sharing personal information
- **Open Source**: All code is transparent and available for review

## License

This project is licensed under the MIT License - see the LICENSE file for details.
