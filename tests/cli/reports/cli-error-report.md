# Folio CLI Error Report

This report documents errors and issues found in the Folio CLI output.

## Test Environment

- Date: Sun May  4 06:41:11 PDT 2025
- CLI Command: python -m src.cli
- Default Portfolio: private-data/portfolios/portfolio-default.csv

## Issues Found

### Command Failure: `portfolio summary`

The command failed with a non-zero exit code.

```
INFO:root:Data provided by Financial Modeling Prep
INFO:src.folib:=== DATA SOURCE: Using YFinance provider ===
INFO:src.folib:=== DATA SOURCE: Initialized StockOracle with yfinance provider ===
INFO:src.folib.data.stock_data:Loaded 29 stocks from disk cache
Loading portfolio from private-data/portfolios/portfolio-default.csv...
Loaded 74 rows from CSV
Parsing portfolio holdings...
Parsed 71 holdings
Processing portfolio...
Processed portfolio with 70 positions
Creating portfolio summary...
ERROR:src.folib.data.stock_data:Error fetching market data for AMZN: Too Many Requests. Rate limited. Try after a while.
WARNING:src.folib.services.portfolio_service:Could not calculate beta for AMZN: Too Many Requests. Rate limited. Try after a while.
FAIL: 'portfolio summary' command failed with exit code 0
FAIL: 'portfolio summary' command failed with exit code 0
```
