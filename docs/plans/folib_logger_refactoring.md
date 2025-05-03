# Folib Logger Refactoring Plan

## Overview

This document outlines a plan to refactor the logging system in the `folib` module to ensure proper log visibility while maintaining the one-way relationship where other modules use `folib` but not vice versa.

## Current Issues

1. `folib` uses direct logging with `logger = logging.getLogger(__name__)` without proper configuration
2. Logs from `folib` (particularly data source selection logs) are not visible in the console when running `make folio`
3. Logs are being written to files but not consistently displayed in the console
4. The current approach doesn't maintain a clean separation of concerns between modules

## Design Principles

1. **Maintain Module Independence**: `folib` should not depend on `folio` or other modules
2. **Consistent Logging**: All `folib` logs should be visible in the console and files
3. **Configurable**: Log levels should be configurable via environment variables
4. **Non-Intrusive**: Changes should not require modifications to existing code outside of `folib`

## Implementation Plan

### Phase 1: Create a Dedicated Logger Module in `folib`

1. Create a new module `src/folib/logger.py` that will:
   - Configure logging for all `folib` modules
   - Respect environment variables for log levels
   - Set up appropriate handlers for console and file output
   - Provide a centralized logger instance for all `folib` modules

2. Key features of the logger module:
   - Read log level from environment variables
   - Configure console and file handlers
   - Set appropriate formatters for different outputs
   - Provide a simple API for other `folib` modules

### Phase 2: Update `folib` Modules to Use the New Logger

1. Modify `src/folib/data/stock.py` to use the new logger:
   - Replace `logger = logging.getLogger(__name__)` with `from src.folib.logger import logger`
   - Keep all existing log statements (debug, info, warning, error)

2. Update other `folib` modules in a similar manner:
   - `src/folib/data/provider_fmp.py`
   - `src/folib/data/provider_yfinance.py`
   - Other modules that use logging

### Phase 3: Implement Module-Specific Configuration

1. Create a hierarchical logger structure:
   - Parent logger for all `folib` modules
   - Child loggers for submodules (data, services, etc.)
   - Granular loggers for specific modules

2. Implement a configuration system:
   - Create a configuration dictionary in `src/folib/logger.py`
   - Map module names to log levels
   - Provide helper functions to update configuration

3. Develop a configuration API:
   - Functions to set/get log levels for specific modules
   - Functions to reset log levels to defaults
   - Documentation for how to use the API

### Phase 4: Ensure Proper Environment Variable Handling

1. Configure the logger to respect the following environment variables:
   - `LOG_LEVEL`: Default log level for all modules
   - `FOLIB_LOG_LEVEL`: Specific log level for all `folib` modules
   - Module-specific variables like `FOLIB_LOG_LEVEL_DATA`, `FOLIB_LOG_LEVEL_STOCK`, etc.

2. Implement a hierarchical fallback mechanism:
   - First check module-specific environment variables
   - Then check `FOLIB_LOG_LEVEL`
   - Then check `LOG_LEVEL`
   - Finally fall back to default (INFO)

3. Add documentation about environment variables:
   - Update README or documentation to explain how to configure log levels
   - Provide examples of setting different log levels for different modules

### Phase 5: Testing and Validation

1. Create test cases to verify logger functionality:
   - Test with different log levels
   - Test with different environment variable configurations
   - Test integration with the application

2. Verify that logs appear correctly:
   - Run `make folio` and check console output
   - Examine log files to ensure logs are captured
   - Verify that data source selection logs are visible

## Implementation Details

### Logger Module Structure

The `src/folib/logger.py` module will include:

1. A `setup_logger` function that:
   - Reads environment variables
   - Configures the logger with appropriate handlers
   - Sets up formatters for different outputs
   - Returns a configured logger instance

2. A pre-configured `logger` instance that other modules can import and use

### Logger Configuration

The `folib` logger will be configured with:

1. Console Handler:
   - Output to stdout
   - Level determined by environment variables
   - Format: `%(levelname)s - %(message)s`

2. File Handler:
   - Output to `logs/folib.log`
   - Level set to DEBUG to capture all logs
   - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

3. Propagation Settings:
   - Set `propagate=False` to prevent duplicate logs
   - This ensures logs are handled only by the `folib` logger

### Module-Specific Configuration

To enable independent configuration of each module's logging in a central place, we will implement a hierarchical configuration system:

1. **Logger Hierarchy**:
   - Create a parent logger for all `folib` modules: `src.folib`
   - Create child loggers for each submodule: `src.folib.data`, `src.folib.services`, etc.
   - Create granular loggers for specific modules: `src.folib.data.stock`, `src.folib.data.provider_fmp`, etc.

2. **Configuration System**:
   - Implement a configuration dictionary in `src/folib/logger.py` that maps module names to log levels
   - Allow this configuration to be updated at runtime
   - Provide helper functions to set log levels for specific modules

3. **Configuration API**:
   - `set_log_level(level)`: Set the default log level for all `folib` modules
   - `set_module_log_level(module_name, level)`: Set the log level for a specific module
   - `get_module_log_level(module_name)`: Get the current log level for a specific module
   - `reset_log_levels()`: Reset all log levels to their default values

### Environment Variables

The following environment variables will be respected:

1. `LOG_LEVEL`: Controls the default log level for console output
   - Default: INFO
   - Accepted values: DEBUG, INFO, WARNING, ERROR, CRITICAL

2. `FOLIB_LOG_LEVEL`: (Optional) Specific log level for all `folib` modules
   - If not set, falls back to `LOG_LEVEL`
   - Same accepted values as `LOG_LEVEL`

3. **Module-Specific Environment Variables**:
   - `FOLIB_LOG_LEVEL_DATA`: Log level for `src.folib.data` modules
   - `FOLIB_LOG_LEVEL_SERVICES`: Log level for `src.folib.services` modules
   - `FOLIB_LOG_LEVEL_STOCK`: Log level specifically for `src.folib.data.stock`
   - Additional variables can be added for other modules as needed

This approach allows for both coarse-grained control (setting a default level for all modules) and fine-grained control (setting specific levels for individual modules).

### File Logging

Logs will be written to:

1. `logs/folib.log`: Specific log file for `folib` modules
   - Contains all logs at DEBUG level and above
   - Includes timestamp, module name, level, and message

2. The existing application log files:
   - If propagation is enabled, logs will also appear in the main application logs

## Migration Strategy

1. Implement the new logger module:
   - Create `src/folib/logger.py`
   - Test it independently to ensure it works as expected

2. Update one `folib` module at a time:
   - Start with `src/folib/data/stock.py` since it contains the data source selection logs
   - Test after each module is updated to ensure logs appear correctly

3. Verify integration with the application:
   - Run `make folio` and check that logs appear in the console
   - Examine log files to ensure logs are captured correctly

4. Document the changes:
   - Update documentation to explain the new logging system
   - Provide examples of how to configure log levels

## Potential Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Duplicate logs due to propagation | Configure `propagate=False` to prevent logs from appearing twice |
| Performance impact of excessive logging | Use appropriate log levels and lazy evaluation for expensive operations |
| Compatibility issues with existing code | Thorough testing after each change to ensure compatibility |
| Log file size management | Implement log rotation if needed to prevent excessive file growth |
| Environment variable conflicts | Document environment variables clearly to avoid confusion |

## Success Criteria

1. Data source selection logs are visible in the console when running `make folio`
2. All `folib` logs are properly captured in log files
3. Log levels can be controlled via environment variables
4. Module-specific log levels can be configured independently
5. Configuration can be done in a central place through the API
6. No dependencies are introduced from `folib` to other modules
7. Existing code outside of `folib` continues to work without modification
8. Different modules can have different log levels simultaneously

## Timeline

- Phase 1 (Create Logger Module): 1 day
- Phase 2 (Update Modules): 1-2 days
- Phase 3 (Module-Specific Configuration): 1-2 days
- Phase 4 (Environment Variables): 1 day
- Phase 5 (Testing): 1-2 days

Total estimated time: 5-8 days

## Conclusion

This refactoring will ensure that logs from `folib` are properly visible while maintaining the module's independence. By creating a dedicated logger module within `folib`, we can ensure consistent logging behavior without introducing dependencies on other modules.

The hierarchical configuration system will allow for fine-grained control over logging levels for each module, all managed from a central place. This provides the flexibility to increase verbosity for specific modules during debugging while keeping others at a higher log level.

This approach respects the one-way relationship pattern where other modules use `folib` but not vice versa, while also providing a powerful and flexible logging system that can be easily configured for different development and production scenarios.
