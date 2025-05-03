"""
Logging configuration for folib.

This module provides a logger for all folib modules. It relies on the root logger
configuration in src/folio/logger.py for actual log handling and output.
"""

import logging
import os

# Get log level from environment variable
log_level_str = os.environ.get("LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_str.upper(), logging.INFO)

# Configure the folib logger
folib_logger = logging.getLogger("src.folib")
folib_logger.setLevel(log_level)

# Ensure propagation is enabled to use the root logger's handlers
folib_logger.propagate = True

# Export the logger for use in other modules
logger = folib_logger
