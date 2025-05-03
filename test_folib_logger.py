"""
Test script to verify the folib logger implementation.
"""

import os
import sys

# Set log level to DEBUG to see all logs
os.environ["LOG_LEVEL"] = "DEBUG"

# Set DATA_SOURCE to fmp to test the data source selection
os.environ["DATA_SOURCE"] = "fmp"
os.environ["FMP_API_KEY"] = "test_key"

print("Importing stockdata...")

# Import the stockdata instance
from src.folib.data.stock import stockdata

print("Data source selection should be logged above.")
print("Testing complete.")
