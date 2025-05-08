# Refactoring Plan: Market Data Access (v1 Draft)

**Date:** 2025-05-08
**Author:** Gemini Pro

**Goal:** Consolidate market data fetching to a single, simple interface using FMP by default, supporting `get_price` and `get_beta`, with in-session storage and extensibility for future caching.

## 1. Analysis of Current State (`src/folib/data`)

* **Multiple Providers:** Current implementation includes `provider_fmp.py` and `provider_yfinance.py`, inheriting from a base `provider.py`.
* **Orchestration Layers:**
    * `stock.py` (`StockOracle`) acts as a facade, selecting providers and handling beta calculation logic.
    * `stock_data.py` (`StockDataService`, `StockData`) adds another layer for structured data access and caching (in-memory and disk).
* **Usage in `src/cli`:** The CLI interacts with both `stockdata` (singleton `StockOracle`) and `default_stock_service` (`StockDataService` instance), primarily in `src/cli/commands/position.py`.
* **Complexity & Duplication:** Multiple layers address similar concerns (fetching, caching, provider selection), leading to redundancy and complexity. The dual use of `StockOracle` and `StockDataService` is confusing.

## 2. Proposed New Design

* **Consolidate & Simplify:** Deprecate and remove `stock.py`, `stock_data.py`, `provider_yfinance.py`. Consider removing `provider.py` if a base class is not immediately needed.
* **New Core Module:** Introduce `src/folib/data/market_data.py`.
* **Primary Interface (`MarketDataProvider` Class):**
    * Location: `src/folib/data/market_data.py`.
    * Responsibilities:
        * Directly use the `fmpsdk` library for FMP API calls.
        * Manage in-session data caching.
        * Provide `get_price(ticker)` and `get_beta(ticker)` methods.
    * Internal Logic:
        * Both `get_price` and `get_beta` will internally fetch the FMP "company_profile" endpoint for a given ticker.
        * Utilize an internal dictionary (`_session_cache`) keyed by ticker to store fetched profile data (`{'price': ..., 'beta': ..., 'profile': ...}`).
        * Implement a private `_fetch_profile(ticker)` method to handle API calls and cache lookups.

```python
# src/folib/data/market_data.py (Conceptual)
import fmpsdk
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MarketDataProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY is required.")
        # In-session cache: {ticker: {price: value, beta: value, profile: raw_data}}
        self._session_cache: Dict[str, Dict[str, Any]] = {}

    def _fetch_profile(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker_upper = ticker.upper()
        if ticker_upper not in self._session_cache or 'profile' not in self._session_cache[ticker_upper]:
            logger.debug(f"Fetching FMP profile for {ticker_upper}")
            try:
                profile_data = fmpsdk.company_profile(apikey=self.api_key, symbol=ticker_upper)
                if profile_data:
                    profile = profile_data[0]
                    self._session_cache.setdefault(ticker_upper, {})['profile'] = profile
                    self._session_cache[ticker_upper]['price'] = profile.get('price')
                    self._session_cache[ticker_upper]['beta'] = profile.get('beta')
                    return profile
                else:
                    self._session_cache.setdefault(ticker_upper, {})['profile'] = None
                    return None
            except Exception as e:
                logger.error(f"Error fetching FMP profile for {ticker_upper}: {e}")
                self._session_cache.setdefault(ticker_upper, {})['profile'] = None
                return None
        return self._session_cache[ticker_upper].get('profile')

    def get_price(self, ticker: str) -> Optional[float]:
        ticker_upper = ticker.upper()
        if ticker_upper in self._session_cache and self._session_cache[ticker_upper].get('price') is not None:
             return self._session_cache[ticker_upper]['price']
        profile = self._fetch_profile(ticker)
        price = profile.get('price') if profile else None
        if price is not None:
            try: return float(price)
            except (ValueError, TypeError): return None
        return None

    def get_beta(self, ticker: str) -> Optional[float]:
        ticker_upper = ticker.upper()
        if ticker_upper in self._session_cache and self._session_cache[ticker_upper].get('beta') is not None:
             return self._session_cache[ticker_upper]['beta']
        profile = self._fetch_profile(ticker)
        beta = profile.get('beta') if profile else None
        if beta is not None:
            try: return float(beta)
            except (ValueError, TypeError): return None
        return None

    def clear_session_cache(self):
        self._session_cache.clear()
        logger.info("In-session market data cache cleared.")

# Default instance (requires FMP_API_KEY env var)
try:
    market_data_provider = MarketDataProvider()
except ValueError as e:
    logger.error(f"Failed to initialize default MarketDataProvider: {e}")
    market_data_provider = None

## Revisions

**Date:** 2025-05-08

Based on discussion, the following implementation decisions have been made:

1. **Breaking Change:** This refactoring will be a breaking change without backward compatibility. All consuming code will need to be updated.

2. **Testing:** We will add unit tests for the new functionality under `tests/folib`. Existing test coverage should be maintained where applicable.

3. **Error Handling:** We will log errors for debugging purposes but generally let exceptions propagate after logging. No fallback logic will be implemented.

4. **Implementation Approach:** The refactoring will be done in stages:
   - Stage 1: Refactor `folib` to implement the single source of truth for market data with unit tests
   - Stage 2: Refactor `cli` to use the new functions in `folib`

5. **Documentation:** Documentation will be addressed in a later phase.

## Implementation Progress

**Date:** 2025-05-08

### Completed

1. **New Market Data Provider Implementation:**
   - Created `MarketDataProvider` class in `src/folib/data/market_data.py`
   - Implemented in-session caching with `get_price()` and `get_beta()` methods
   - Added comprehensive unit tests in `tests/folib/data/test_market_data.py` (14 test cases)

2. **Updated References:**
   - `src/cli/commands/position.py` now uses `market_data_provider` instead of `stockdata`
   - `src/folio/simulator_v2.py` updated to use `market_data_provider`
   - `src/folio/portfolio.py` updated to use `market_data_provider`
   - `src/folio/utils.py` updated to use `market_data_provider`

3. **Documentation:**
   - Updated `src/folib/data/__init__.py` to reflect the new architecture

4. **Verification:**
   - All tests pass and code passes linting

### Next Steps

1. **File Cleanup:**
   - Remove the deprecated files (`stock.py`, `stock_data.py`, `provider_yfinance.py`)
   - Consider removing `provider.py` if a base class is not immediately needed

2. **Documentation:**
   - Add more detailed documentation for the new `MarketDataProvider` class
   - Update any remaining references to the old market data functionality in documentation

3. **Monitoring:**
   - Monitor for any issues related to the refactoring in production
   - Ensure all edge cases are properly handled
