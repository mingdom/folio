# Folio CLI Error Report

This report documents errors and issues found in the Folio CLI output.

## Test Environment

- Date: Fri May  2 09:40:40 PDT 2025
- CLI Command: python -m src.cli
- Default Portfolio: private-data/portfolios/portfolio-default.csv

## Issues Found

### 1 Warning messages in `interactive mode`

```
1:Warning: Input is not a terminal (fd=0).

```


## Summary

The test script executed the following commands:
- `portfolio load private-data/portfolios/portfolio-default.csv`
- `portfolio summary --file private-data/portfolios/portfolio-default.csv`
- `portfolio list --file private-data/portfolios/portfolio-default.csv`
- `portfolio list --file private-data/portfolios/portfolio-default.csv type=stock sort=value:desc`
- `position details SPY --file private-data/portfolios/portfolio-default.csv`
- `position details SPY --file private-data/portfolios/portfolio-default.csv --show-legs`
- `position risk SPY --file private-data/portfolios/portfolio-default.csv`
- `position risk SPY --file private-data/portfolios/portfolio-default.csv --show-greeks`
- Interactive mode with basic commands

All test outputs are available in the `/tmp/folio_cli_test_output` directory.

## Next Steps

1. Review the issues found and prioritize them for fixing
2. Focus on fixing $nan values in the output, as these indicate calculation issues
3. Address any error messages that might affect user experience
4. Create unit tests to prevent regression of fixed issues
