# Market Data Providers in folib

This document describes the market data provider pattern implemented in `src/folib/data/stock.py` and how to use different providers.

## Overview

The `StockOracle` class in `src/folib/data/stock.py` now supports multiple market data providers through a provider interface. This allows for interchangeable data sources while maintaining a consistent interface.

Currently, two providers are implemented:
1. **Yahoo Finance Provider** (default): Uses the `yfinance` package to fetch market data
2. **Financial Modeling Prep (FMP) Provider**: Uses the FMP API to fetch market data

## Provider Interface

All providers implement the `MarketDataProvider` interface defined in `src/folib/data/provider.py`. This interface defines the following methods:

- `get_price(ticker)`: Get the current price for a ticker
- `get_beta(ticker)`: Get the beta value for a ticker
- `get_historical_data(ticker, period, interval)`: Get historical price data for a ticker
- `is_valid_stock_symbol(ticker)`: Check if a ticker symbol is likely a valid stock symbol

## Configuration

The provider can be configured using environment variables in the `.env` file:

```
# Data Source Configuration
DATA_SOURCE=yfinance  # or "fmp"

# API Keys
FMP_API_KEY=your_financial_modeling_prep_api_key_here
```

When the application starts, it reads these environment variables and initializes the `StockOracle` singleton with the appropriate provider.

## Using Different Providers

### Default Provider (Yahoo Finance)

The default provider is Yahoo Finance, which is used when no provider is specified or when `DATA_SOURCE` is set to `yfinance`:

```python
from src.folib.data.stock import StockOracle

# Using default YFinance provider
oracle = StockOracle.get_instance()
price = oracle.get_price("AAPL")
```

### FMP Provider

To use the FMP provider, you can either:

1. Set the environment variables in the `.env` file:
   ```
   DATA_SOURCE=fmp
   FMP_API_KEY=your_api_key
   ```

2. Or specify the provider name and API key directly in code:
   ```python
   from src.folib.data.stock import StockOracle

   # Using FMP provider
   oracle = StockOracle.get_instance(
       provider_name="fmp",
       fmp_api_key="your_api_key"
   )
   price = oracle.get_price("AAPL")
   ```

## Singleton Pattern

The `StockOracle` class is implemented as a Singleton to ensure only one instance exists throughout the application. This means that once an instance is created with a specific provider, all subsequent calls to `get_instance()` will return the same instance.

If you need to use different providers in the same application, you can create separate instances with different names:

```python
# Using default YFinance provider
oracle_yf = StockOracle.get_instance()

# Using FMP provider
oracle_fmp = StockOracle.get_instance(
    provider_name="fmp",
    fmp_api_key="your_api_key"
)
```

## Caching

Both providers implement caching to improve performance and reduce API calls. By default, cache files are stored in:
- `.cache_yfinance` for the Yahoo Finance provider
- `.cache_fmp` for the FMP provider

You can specify a custom cache directory and TTL (time-to-live) when creating a provider:

```python
oracle = StockOracle.get_instance(
    provider_name="fmp",
    fmp_api_key="your_api_key",
    cache_dir="/custom/cache/dir",
    cache_ttl=3600  # 1 hour in seconds
)
```

## Example Usage

See `src/folib/examples/fmp_provider_example.py` for a complete example of using the FMP provider.

## Adding New Providers

To add a new provider:

1. Create a new provider class in `src/folib/data/` (e.g., `provider_newapi.py`) that implements the `MarketDataProvider` interface
2. Update `StockOracle` to support the new provider
3. Update documentation and examples

## Considerations

- **API Keys**: Some providers (like FMP) require an API key, which should be kept secure and not committed to version control
- **Rate Limits**: Different providers have different rate limits, which should be considered when making API calls
- **Data Availability**: Different providers may have different data availability, especially for historical data
- **Error Handling**: Providers should handle errors gracefully and provide meaningful error messages
