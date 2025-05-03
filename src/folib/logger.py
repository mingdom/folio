"""
Logging configuration for folib.

This module configures logging for all folib modules, ensuring logs are
properly displayed in the console and written to files.
"""

import logging
import os
import sys

# Get log level from environment variable
log_level_str = os.environ.get("LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_str.upper(), logging.INFO)

# Configure the folib logger
folib_logger = logging.getLogger("src.folib")
folib_logger.setLevel(log_level)

# Ensure propagation is enabled (this is the default, but we're being explicit)
folib_logger.propagate = True

# Add a console handler if one doesn't exist yet
# This ensures logs are visible even if the root logger isn't configured yet
if not any(isinstance(handler, logging.StreamHandler) for handler in folib_logger.handlers):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    folib_logger.addHandler(console_handler)

# Export the logger for use in other modules
logger = folib_logger
