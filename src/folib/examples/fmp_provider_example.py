#!/usr/bin/env python3
# ruff: noqa: T201
"""
Example of using the FMP provider with StockOracle.

This script demonstrates how to use the Financial Modeling Prep (FMP) provider
as an alternative to the default Yahoo Finance provider in StockOracle.

Usage:
    python -m src.folib.examples.fmp_provider_example

Note:
    The provider is automatically selected based on the DATA_SOURCE and FMP_API_KEY
    environment variables in the .env file. You can also override these settings
    by setting the environment variables directly:

    Example:
        export DATA_SOURCE="fmp"
        export FMP_API_KEY="your_api_key"
"""

import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from src.folib.data.stock import StockOracle

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Log to stderr
    ],
)
logger = logging.getLogger(__name__)


def main():
    """Run the FMP provider example."""
    print("Starting FMP provider example...")

    # Get provider configuration from environment variables
    data_source = os.environ.get("DATA_SOURCE", "yfinance").lower()
    fmp_api_key = os.environ.get("FMP_API_KEY")

    # Print environment variables for debugging
    print(f"DATA_SOURCE from environment: {data_source}")
    print(f"FMP_API_KEY from environment: {'[SET]' if fmp_api_key else '[NOT SET]'}")

    logger.info(f"DATA_SOURCE from environment: {data_source}")
    logger.info(
        f"FMP_API_KEY from environment: {'[SET]' if fmp_api_key else '[NOT SET]'}"
    )

    # Force using FMP provider for this example
    data_source = "fmp"
    print(f"Using data source: {data_source}")

    # Check if we can use FMP provider
    if data_source == "fmp" and not fmp_api_key:
        print("ERROR: DATA_SOURCE is set to 'fmp' but FMP_API_KEY is not set")
        print("Please set FMP_API_KEY in your .env file or environment")
        logger.error("DATA_SOURCE is set to 'fmp' but FMP_API_KEY is not set")
        logger.error("Please set FMP_API_KEY in your .env file or environment")
        return

    print("Creating StockOracle instance...")

    # Create StockOracle instance with the appropriate provider
    if data_source == "fmp" and fmp_api_key:
        print("Using FMP provider")
        logger.info("Using FMP provider")
        try:
            oracle = StockOracle.get_instance(
                provider_name="fmp",
                fmp_api_key=fmp_api_key,
                cache_dir=".cache_fmp_example",  # Use a separate cache directory for this example
            )
            print("StockOracle instance created successfully")
        except Exception as e:
            print(f"ERROR creating StockOracle instance: {e}")
            logger.error(f"Error creating StockOracle instance: {e}")
            return
    else:
        print("Using YFinance provider")
        logger.info("Using YFinance provider")
        oracle = StockOracle.get_instance(
            cache_dir=".cache_yf_example"  # Use a separate cache directory for this example
        )

    # Test symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    print(f"Test symbols: {symbols}")

    # Print provider information
    print(f"Provider name: {oracle.provider_name}")
    print(f"Provider type: {type(oracle.provider)}")
    print(f"Cache directory: {oracle.cache_dir}")

    logger.info(f"Provider name: {oracle.provider_name}")
    logger.info(f"Provider type: {type(oracle.provider)}")
    logger.info(f"Cache directory: {oracle.cache_dir}")

    # Get current prices
    print("\nGetting current prices...")
    logger.info("Getting current prices...")
    for symbol in symbols:
        try:
            print(f"Fetching price for {symbol}...")
            logger.info(f"Fetching price for {symbol}...")
            price = oracle.get_price(symbol)
            print(f"{symbol}: ${price:.2f}")
            logger.info(f"{symbol}: ${price:.2f}")
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            logger.error(f"Error getting price for {symbol}: {e}")

    # Get beta values
    print("\nGetting beta values...")
    logger.info("\nGetting beta values...")
    for symbol in symbols:
        try:
            print(f"Fetching beta for {symbol}...")
            logger.info(f"Fetching beta for {symbol}...")
            beta = oracle.get_beta(symbol)
            if beta is not None:
                print(f"{symbol} beta: {beta:.2f}")
                logger.info(f"{symbol} beta: {beta:.2f}")
            else:
                print(f"{symbol} beta: Not available")
                logger.info(f"{symbol} beta: Not available")
        except Exception as e:
            print(f"Error getting beta for {symbol}: {e}")
            logger.error(f"Error getting beta for {symbol}: {e}")

    # Get historical data
    print("\nGetting historical data (last 5 days)...")
    logger.info("\nGetting historical data (last 5 days)...")

    # Try with a few different symbols
    symbols_to_try = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "SPY"]
    print(f"Symbols to try: {symbols_to_try}")

    for symbol in symbols_to_try:
        try:
            # Calculate date range for last 5 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)

            # Format dates for display
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            print(f"Trying to get historical data for {symbol}...")
            logger.info(f"Trying to get historical data for {symbol}...")

            # Get historical data
            df = oracle.get_historical_data(symbol, period="5d")

            # Display the data
            print(f"Historical data for {symbol} from {start_str} to {end_str}:")
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            print(f"First few rows:\n{df.head()}")

            logger.info(f"Historical data for {symbol} from {start_str} to {end_str}:")
            logger.info(f"Shape: {df.shape}")
            logger.info(f"Columns: {df.columns.tolist()}")
            logger.info(f"First few rows:\n{df.head()}")

            # If we successfully got data, break out of the loop
            break
        except Exception as e:
            print(f"Error getting historical data for {symbol}: {e}")
            logger.error(f"Error getting historical data for {symbol}: {e}")
            continue
    else:
        print("Could not get historical data for any of the symbols tried.")
        logger.error("Could not get historical data for any of the symbols tried.")


if __name__ == "__main__":
    main()
