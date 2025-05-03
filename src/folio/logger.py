import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml


def get_environment() -> str:
    """Determine the current environment (local or production)."""
    is_huggingface = (
        os.environ.get("HF_SPACE") == "1" or os.environ.get("SPACE_ID") is not None
    )
    is_docker = os.path.exists("/.dockerenv")

    if is_huggingface or is_docker:
        return "production"
    return "local"


def load_config() -> dict[str, Any]:
    """Load configuration from folio.yaml file."""
    config_path = os.path.join(os.path.dirname(__file__), "folio.yaml")
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # Log error but continue with empty config
        # Can't use logger here as it's not initialized yet
        return {}


def get_log_level(environment: str, config: dict[str, Any]) -> int:
    """Determine the log level based on environment variables and config."""
    # 1. Check environment variable (highest precedence)
    log_level_str = os.environ.get("LOG_LEVEL")
    if log_level_str:
        level = getattr(logging, log_level_str.upper(), None)
        if level is not None:
            return level

    # 2. Check environment-specific config
    logging_config = config.get("app", {}).get("logging", {})
    env_level_str = logging_config.get("environments", {}).get(environment)
    if env_level_str:
        level = getattr(logging, env_level_str.upper(), None)
        if level is not None:
            return level

    # 3. Check default config level
    default_level_str = logging_config.get("level")
    if default_level_str:
        level = getattr(logging, default_level_str.upper(), None)
        if level is not None:
            return level

    # 4. Use hardcoded defaults
    return logging.WARNING if environment == "production" else logging.INFO


def setup_logger() -> logging.Logger:
    """Set up and configure the logger.

    This function configures the logger based on the current environment and configuration.
    Log level precedence: LOG_LEVEL env var > config file > default level.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Determine environment and load config
    environment = get_environment()
    config = load_config()

    # Get log level
    log_level = get_log_level(environment, config)

    # Configure root logger (for third-party libraries)
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)

    # Add a basic handler to the root logger
    root_handler = logging.StreamHandler(sys.stderr)
    root_handler.setFormatter(logging.Formatter("ROOT: %(levelname)s - %(message)s"))
    root_logger.addHandler(root_handler)

    # Create application logger
    logger = logging.getLogger("folio")
    logger.setLevel(logging.DEBUG)  # Allow all levels to handlers
    logger.propagate = False  # Prevent propagation to root

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console_handler)

    # Add file handler (except on Hugging Face)
    is_huggingface = (
        os.environ.get("HF_SPACE") == "1" or os.environ.get("SPACE_ID") is not None
    )
    if not is_huggingface:
        # Get log file name from config
        log_file_name = (
            config.get("app", {}).get("logging", {}).get("file", "folio_latest.log")
        )

        # Create log directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        try:
            file_handler = logging.FileHandler(
                logs_dir / log_file_name, mode="w", encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(file_handler)
        except (PermissionError, OSError) as e:
            # Log to console if file creation fails
            logger.warning(f"Could not create log file: {e}. Logging to console only.")

    # Log initialization
    level_name = logging.getLevelName(log_level)
    logger.info(
        f"Logger initialized with level {level_name} for {environment} environment"
    )
    return logger


# Create and configure logger
logger = setup_logger()
