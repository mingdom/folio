# Logging in Folio

This document describes how logging is configured and used throughout the Folio codebase.

## Overview

Folio uses Python's built-in `logging` module to provide a flexible and configurable logging system. The codebase is organized into two main modules, each with its own logging configuration:

1. `src/folio/` - The main application module
2. `src/folib/` - The core library module

## Log Levels

Folio uses standard Python logging levels:

| Level    | Value | When to use                                                |
|----------|-------|-----------------------------------------------------------|
| DEBUG    | 10    | Detailed information, typically for debugging              |
| INFO     | 20    | Confirmation that things are working as expected           |
| WARNING  | 30    | Indication that something unexpected happened              |
| ERROR    | 40    | Due to a more serious problem, some functionality is lost  |
| CRITICAL | 50    | A serious error, indicating that the program may be unable to continue |

## Configuration

### Environment Variables

The log level for the entire application can be controlled using the `LOG_LEVEL` environment variable:

```bash
# Set log level to DEBUG
LOG_LEVEL=DEBUG make folio

# Or use the level parameter in make commands
make folio level=DEBUG
make cli level=DEBUG
make test level=DEBUG
make simulate level=DEBUG
make analyze level=DEBUG
```

All make commands that run Python code support the `level` parameter to control the log level.

### Default Log Levels

- **Local Development**: INFO level by default
- **Production**: WARNING level by default

## Logger Modules

### 1. `src/folio/logger.py`

This module configures logging for the main application:

- Creates a root logger that captures logs from all modules
- Creates a specific `folio` logger for application logs
- Configures console and file handlers
- Respects the `LOG_LEVEL` environment variable
- Writes logs to `logs/folio_latest.log`

### 2. `src/folib/logger.py`

This module provides a logger for the core library:

- Creates a `src.folib` logger for all library modules
- Sets the appropriate log level based on the `LOG_LEVEL` environment variable
- Ensures propagation to the root logger for actual log handling
- Relies on the root logger's handlers for output

## Log Output Destinations

Logs are sent to multiple destinations:

1. **Console**: All logs at the configured level and above are displayed in the console
2. **Log Files**: All logs at DEBUG level and above are written to log files in the `logs/` directory

## Using Loggers in Code

### In `src/folio/` modules:

```python
from src.folio.logger import logger

# Then use the logger
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

### In `src/folib/` modules:

```python
from src.folib.logger import logger

# Then use the logger
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

## Log Format

### Console Format

- **folio logger**: `LEVEL: MESSAGE`
- **folib logger**: `LEVEL - MESSAGE`
- **root logger**: `LEVEL - MESSAGE`

### File Format

- `TIMESTAMP - MODULE - LEVEL - MESSAGE`

Example: `2025-05-03 11:10:39,216 - folio - DEBUG - Ticker SPGI stock exposure: 25443.5`

## Important Logging Points

The following key events are logged:

1. **Application Startup**: Logged at INFO level
2. **Data Source Selection**: Logged at INFO level with a prominent prefix
3. **Portfolio Loading**: Logged at INFO level
4. **API Calls**: Logged at INFO level
5. **Errors and Warnings**: Logged at appropriate levels

## Debugging Tips

1. **Increase Log Level**: Set `LOG_LEVEL=DEBUG` to see more detailed logs
2. **Check Log Files**: Examine the log files in the `logs/` directory
3. **Filter Logs**: Use `grep` or other tools to filter logs by module or level

## Implementation Details

### Root Logger Configuration

The root logger is configured in `src/folio/logger.py` to capture logs from all modules, including `src/folib/`:

```python
# Configure root logger (for third-party libraries and src.folib)
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Set root logger level to match the application log level
# This ensures src.folib logs are also displayed
root_logger.setLevel(log_level)

# Add a basic handler to the root logger
root_handler = logging.StreamHandler(sys.stderr)
root_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
root_logger.addHandler(root_handler)
```

### Folib Logger Configuration

The `src/folib/logger.py` module provides a logger for `folib` modules:

```python
# Configure the folib logger
folib_logger = logging.getLogger("src.folib")
folib_logger.setLevel(log_level)

# Ensure propagation is enabled to use the root logger's handlers
folib_logger.propagate = True

# Export the logger for use in other modules
logger = folib_logger
```

## Best Practices

1. **Use Appropriate Log Levels**: Choose the right log level for each message
2. **Include Relevant Context**: Include enough information to understand the log message
3. **Avoid Excessive Logging**: Don't log too much information at high levels
4. **Use Lazy Evaluation**: For expensive operations, use lazy evaluation (e.g., `logger.debug(f"Expensive calculation: {expensive_function() if logger.isEnabledFor(logging.DEBUG) else 'skipped'}")`)
5. **Log Exceptions**: Always log exceptions with traceback information

## Troubleshooting

### Duplicate Logs

If you see duplicate log messages, it might be because:

1. Multiple handlers are configured for the same logger
2. A logger has its own handler and propagation is enabled

### Missing Logs

If logs are not appearing:

1. Check the log level (it might be set too high)
2. Verify that the logger is properly configured
3. Ensure that handlers are attached to the logger

### Log File Issues

If logs are not being written to files:

1. Check that the `logs/` directory exists and is writable
2. Verify that file handlers are properly configured
3. Check for any error messages about file creation failures
