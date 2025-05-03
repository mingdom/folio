"""
Test script to verify data source selection logging.
"""

import logging
import os
import sys

# Configure logging to display all messages at INFO level or higher
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Set log level to INFO
os.environ["LOG_LEVEL"] = "INFO"
os.environ["DATA_SOURCE"] = "fmp"  # Set to FMP to test the data source selection
os.environ["FMP_API_KEY"] = "test_key"  # Set a dummy API key

print("Importing stockdata...")

# Import the stockdata instance
from src.folib.data.stock import stockdata

# This should trigger the data source selection logging
print("Data source selection should be logged above.")
