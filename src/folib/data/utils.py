import logging
import re

logger = logging.getLogger(__name__)


def is_valid_stock_symbol(ticker: str) -> bool:
    """
    Check if a ticker symbol is likely a valid stock symbol.

    This function uses a simple regex pattern to check if a ticker symbol follows
    common stock symbol patterns. It's designed to filter out obviously invalid
    symbols before sending them to provider APIs.

    Common stock symbol patterns:
    - 1-5 uppercase letters (most US stocks: AAPL, MSFT, GOOGL)
    - 1-5 uppercase letters with a period (some international stocks: BHP.AX)
    - 1-5 uppercase letters with a hyphen (some ETFs: SPY-X)
    - 1-5 uppercase letters followed by 1-3 uppercase letters after a period (ADRs: SONY.TO)

    Args:
        ticker: The ticker symbol to check

    Returns:
        True if the ticker appears to be a valid stock symbol, False otherwise
    """
    if not ticker:
        return False

    # Simple regex pattern for common stock symbols
    # This covers most US stocks, ETFs, and common international formats
    pattern = r"^[A-Z]{1,5}(\.[A-Z]{1,3}|-[A-Z]{1})?$"

    # Special case for fund symbols that often have numbers and special formats
    fund_pattern = r"^[A-Z]{1,5}[0-9X]{0,3}$"

    # Check if the ticker matches either pattern
    if re.match(pattern, ticker) or re.match(fund_pattern, ticker):
        return True

    # Log invalid symbols for debugging
    logger.debug(f"Symbol '{ticker}' does not match standard stock symbol patterns")
    return False
