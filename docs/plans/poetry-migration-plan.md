# Poetry Migration Plan for Folio Project

## Overview

This document outlines a step-by-step plan for migrating the Folio project from its current Make-based dependency management to Poetry, while maintaining backward compatibility throughout the transition.

Notes on goals:
- Use Poetry for dependency management while keeping Make for convenient command shortcuts
- No need to add `poetry` specific targets in the Makefile, just update existing targets to use Poetry under the hood
- Makefile and Poetry will be complementary tools, with Poetry handling dependencies and Make providing user-friendly commands

## Migration Checklist

- [X] Phase 1: Initial Poetry Setup
- [X] Phase 2: Dependency Management Migration
- [X] Phase 2b: Documentation: add new `Poetry.md` to note all the Poetry commands. Keep this updated throughout.
- [X] Phase 3: Command Migration (Basic)
- [X] Phase 4: Command Migration (Advanced)
- [X] Phase 5: Full Poetry Integration
- [X] Phase 5a: Update README.md including how to install Poetry
- [X] Phase 6: Update Docker configuration to work with Poetry
- [X] Phase 7: Decision: Keep Makefile as complementary tool for convenient command shortcuts
- [X] Phase 8: Remove legacy requirements files (requirements.txt and requirements-dev.txt)
- [X] Phase 9: Cleanup - Remove outdated targets and scripts
- [X] Phase 10: Additional Cleanup - Update remaining scripts, .gitignore, and remove custom git hooks
- [X] Phase 11: Bug Fixes - Update Dash API usage from run_server() to run()
- [X] Phase 12: Remove Redundant Features - Remove simulator target (functionality integrated into focli)
- [X] Phase 13: Docker Fix - Update Dockerfile to use --no-root flag for Poetry installation
- [X] Phase 14: Docker Port Fix - Change Docker port to avoid conflicts
- [X] Phase 15: Docker Optimization - Minimize files copied to Docker image

## Phase 1: Initial Poetry Setup

### Goals
- Install Poetry
- Create initial `pyproject.toml` configuration
- Ensure Poetry can coexist with current Make-based system

### Steps

1. **Install Poetry**

   ```bash
   # For macOS/Linux
   curl -sSL https://install.python-poetry.org | python3 -

   # For Windows
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```

2. **Initialize Poetry in the project**

   ```bash
   # Navigate to project root
   cd /path/to/folio

   # Initialize Poetry (this will create a new pyproject.toml)
   poetry init
   ```

3. **Configure Poetry settings**

   ```bash
   # Configure Poetry to create virtual environments in the project directory
   poetry config virtualenvs.in-project true
   ```

4. **Create initial pyproject.toml**

   Create or update the `pyproject.toml` file with project metadata:

   ```toml
   [tool.poetry]
   name = "folio"
   version = "0.1.0"
   description = "Portfolio analysis and visualization tools"
   authors = ["Dong Ming <d3ming@gmail.com>"]
   readme = "README.md"
   packages = [{include = "src"}]

   [tool.poetry.dependencies]
   python = "^3.9"  # Adjust based on your minimum Python version

   [tool.poetry.group.dev.dependencies]

   [build-system]
   requires = ["poetry-core"]
   build-backend = "poetry.core.masonry.api"
   ```

5. **Add Make target for Poetry setup**

   Add a new target to the Makefile to set up Poetry:

   ```makefile
   .PHONY: poetry-setup
   poetry-setup:
       @echo "Setting up Poetry..."
       @if ! command -v poetry &> /dev/null; then \
           echo "Poetry not found. Installing..."; \
           curl -sSL https://install.python-poetry.org | python3 -; \
       fi
       @poetry config virtualenvs.in-project true
       @echo "Poetry setup complete. You can now run 'make poetry-install'."
   ```

## Phase 2: Dependency Management Migration

### Goals
- Migrate dependencies from requirements files to Poetry
- Ensure all dependencies are correctly specified
- Create a Poetry lock file

### Steps

1. **Migrate core dependencies**

   Add core dependencies from `requirements.txt` to Poetry:

   ```bash
   poetry add pandas==2.2.1 numpy==1.26.4 QuantLib requests PyYAML==6.0.1 yfinance dash dash-bootstrap-components dash-bootstrap-templates gunicorn google-generativeai
   ```

2. **Migrate development dependencies**

   Add development dependencies from `requirements-dev.txt` to Poetry:

   ```bash
   poetry add --group dev ruff pytest rich
   ```

3. **Verify dependencies**

   Ensure all dependencies are correctly installed:

   ```bash
   poetry show
   ```

4. **Add Make target for Poetry install**

   Add a new target to the Makefile to install dependencies with Poetry:

   ```makefile
   .PHONY: poetry-install
   poetry-install:
       @echo "Installing dependencies with Poetry..."
       @if ! command -v poetry &> /dev/null; then \
           echo "Poetry not found. Please run 'make poetry-setup' first."; \
           exit 1; \
       fi
       @poetry install
       @echo "Dependencies installed successfully with Poetry."
   ```

5. **Update existing install target to support both methods**

   Update the existing `install` target to support both methods:

   ```makefile
   .PHONY: install
   install:
       @echo "Installing dependencies..."
       @if command -v poetry &> /dev/null && [ -f "poetry.lock" ]; then \
           echo "Using Poetry for dependency management..."; \
           make poetry-install; \
       else \
           echo "Using traditional pip for dependency management..."; \
           if [ ! -d "$(VENV_DIR)" ]; then \
               echo "Virtual environment not found. Please run 'make env' first."; \
               exit 1; \
           fi; \
           mkdir -p $(LOGS_DIR); \
           (echo "=== Installation Log $(TIMESTAMP) ===" && \
           echo "Starting installation at: $$(date)" && \
           (source $(VENV_DIR)/bin/activate && \
           $(PYTHON) -m pip install --upgrade pip && \
           bash $(SCRIPTS_DIR)/install-reqs.sh) 2>&1 && \
           echo "Setting script permissions..." && \
           chmod +x $(SCRIPTS_DIR)/*.sh && \
           chmod +x $(SCRIPTS_DIR)/*.py && \
           echo "Installation complete at: $$(date)") | tee $(LOGS_DIR)/install_$(TIMESTAMP).log; \
           echo "Installation log saved to: $(LOGS_DIR)/install_$(TIMESTAMP).log"; \
           echo "To install git hooks, run 'make hooks'"; \
       fi
   ```

## Phase 3: Command Migration (Basic)

### Goals
- Update basic Make commands to use Poetry directly
- Maintain the same user interface for Make commands
- Make Poetry the default for all commands

### Steps

1. **Update the `env` target to use Poetry**

   Replace the traditional virtual environment setup with Poetry:

   ```makefile
   # Set up virtual environment
   .PHONY: env
   env:
       @echo "Setting up virtual environment with Poetry..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Installing..."; \
           curl -sSL https://install.python-poetry.org | $(PYTHON) -; \
       fi
       @$(POETRY) config virtualenvs.in-project true
       @echo "Creating Poetry virtual environment..."
       @$(POETRY) env use $(PYTHON)
       @echo "Virtual environment created successfully."
       @echo "NOTE: To activate the virtual environment in your current shell, run: poetry shell"
       @echo "The virtual environment will be automatically activated for all make commands."
   ```

2. **Update the `install` target to use Poetry**

   Simplify the install target to use Poetry directly:

   ```makefile
   # Install dependencies
   .PHONY: install
   install:
       @echo "Installing dependencies..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @mkdir -p $(LOGS_DIR)
       @(echo "=== Installation Log $(TIMESTAMP) ===" && \
       echo "Starting installation at: $$(date)" && \
       $(POETRY) install && \
       echo "Setting script permissions..." && \
       chmod +x $(SCRIPTS_DIR)/*.sh && \
       chmod +x $(SCRIPTS_DIR)/*.py && \
       echo "Installation complete at: $$(date)") | tee $(LOGS_DIR)/install_$(TIMESTAMP).log
       @echo "Installation log saved to: $(LOGS_DIR)/install_$(TIMESTAMP).log"
       @echo "To install git hooks, run 'make hooks'"
   ```

3. **Update the `lint` target to use Poetry**

   Simplify the lint target to use Poetry directly:

   ```makefile
   # Lint Python code
   .PHONY: lint
   lint:
       @echo "Running linter (ruff)..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @mkdir -p $(LOGS_DIR)
       @(echo "=== Code Check Log $(TIMESTAMP) ===" && \
       echo "Starting checks at: $$(date)" && \
       $(POETRY) run ruff check --fix --unsafe-fixes . \
       2>&1) | tee $(LOGS_DIR)/code_check_latest.log
       @echo "Check log saved to: $(LOGS_DIR)/code_check_latest.log"
   ```

4. **Update the `test` target to use Poetry**

   Simplify the test target to use Poetry directly:

   ```makefile
   # Test targets
   .PHONY: test test-e2e
   test:
       @echo "Running unit tests..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @mkdir -p $(LOGS_DIR)
       @(echo "=== Test Run Log $(TIMESTAMP) ===" && \
       echo "Starting tests at: $$(date)" && \
       $(POETRY) run pytest tests/ -v 2>&1) | tee $(LOGS_DIR)/test_latest.log
       @echo "Test log saved to: $(LOGS_DIR)/test_latest.log"
   ```

## Phase 4: Command Migration (Advanced)

### Goals
- Update application-specific commands to use Poetry directly
- Maintain the same user interface for Make commands
- Ensure all functionality works with Poetry

### Steps

1. **Update the `test-e2e` target to use Poetry**

   Simplify the test-e2e target to use Poetry directly:

   ```makefile
   test-e2e:
       @echo "Running end-to-end tests..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @if [ ! -f "private-data/test/test-portfolio.csv" ]; then \
           echo "Warning: Test portfolio file not found at private-data/test/test-portfolio.csv"; \
           echo "E2E tests will try to use sample-data/sample-portfolio.csv instead."; \
       fi
       @mkdir -p $(LOGS_DIR)
       @(echo "=== E2E Test Run Log $(TIMESTAMP) ===" && \
       echo "Starting E2E tests at: $$(date)" && \
       $(POETRY) run pytest tests/e2e/ -v 2>&1) | tee $(LOGS_DIR)/test_e2e_latest.log
       @echo "E2E test log saved to: $(LOGS_DIR)/test_e2e_latest.log"
   ```

2. **Update the `folio` target to use Poetry**

   Simplify the folio target to use Poetry directly:

   ```makefile
   folio:
       @echo "Starting portfolio dashboard with debug mode..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @LOG_LEVEL=$(if $(log),$(log),INFO) \
       $(POETRY) run python -m src.folio.app --port 8051 --debug $(if $(portfolio),--portfolio $(portfolio),)
   ```

3. **Update the `portfolio` target to use Poetry**

   Simplify the portfolio target to use Poetry directly:

   ```makefile
   portfolio:
       @echo "Starting portfolio dashboard with sample portfolio.csv and debug mode..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @LOG_LEVEL=$(if $(log),$(log),INFO) \
       $(POETRY) run python -m src.folio.app --port 8051 --debug --portfolio src/folio/assets/sample-portfolio.csv
   ```

4. **Update the `port` target to use Poetry**

   Simplify the port target to use Poetry directly:

   ```makefile
   port:
       @echo "Running portfolio analysis..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @$(POETRY) run python src/lab/portfolio.py "$(if $(csv),$(csv),src/folio/assets/sample-portfolio.csv)"
   ```

5. **Update the `simulator` target to use Poetry**

   Simplify the simulator target to use Poetry directly:

   ```makefile
   simulator:
       @echo "Running SPY simulator..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @$(POETRY) run python ./scripts/folio-simulator.py $(if $(range),--range $(range),) $(if $(steps),--steps $(steps),) $(if $(focus),--focus $(focus),) $(if $(detailed),--detailed,)
   ```

6. **Update the `focli` target to use Poetry**

   Simplify the focli target to use Poetry directly:

   ```makefile
   focli:
       @echo "Starting Folio CLI interactive shell..."
       @if ! command -v $(POETRY) &> /dev/null; then \
           echo "Poetry not found. Please run 'make env' first."; \
           exit 1; \
       fi
       @$(POETRY) run python src/focli/focli.py
   ```

7. **Update the help text to reflect Poetry integration**

   Update the help text to inform users about Poetry integration:

   ```makefile
   @echo ""
   @echo "Note: All targets now use Poetry under the hood for dependency management"
   @echo ""
   ```

## Phase 5: Full Poetry Integration

### Goals
- Complete the migration to Poetry
- Update documentation
- Consider removing legacy Make targets

### Steps

1. **Update project documentation**

   Update README.md and other documentation to reflect the new Poetry-based workflow:

   ```markdown
   ## Development Setup

   ### Using Poetry (Recommended)

   1. Install Poetry:
      ```bash
      curl -sSL https://install.python-poetry.org | python3 -
      ```

   2. Install dependencies:
      ```bash
      poetry install
      ```

   3. Activate the virtual environment:
      ```bash
      poetry shell
      ```

   4. Run the application:
      ```bash
      poetry run folio
      ```

   ### Using Make (Legacy)

   1. Set up the virtual environment:
      ```bash
      make env
      ```

   2. Install dependencies:
      ```bash
      make install
      ```

   3. Run the application:
      ```bash
      make folio
      ```
   ```

2. **Consider adding Poetry plugin for pre-commit hooks**

   ```bash
   poetry add --group dev pre-commit
   ```

   Update `.pre-commit-config.yaml` to work with Poetry.

3. **Update CI/CD pipelines**

   Update any CI/CD pipelines to use Poetry for dependency installation and testing.

4. **Consider deprecating legacy Make targets**

   Once the team is comfortable with Poetry, consider adding deprecation warnings to legacy Make targets:

   ```makefile
   .PHONY: env
   env:
       @echo "WARNING: 'make env' is deprecated. Please use 'make poetry-setup' and 'poetry install' instead."
       @echo "Setting up virtual environment..."
       @bash $(SCRIPTS_DIR)/setup-venv.sh
       @echo "Activating virtual environment..."
       @echo "NOTE: To use the virtual environment in your current shell, run: source activate-venv.sh"
       @echo "The virtual environment will be automatically activated for all make commands."
   ```

## Benefits of This Migration Approach

1. **Gradual Adoption**: Team members can continue using familiar Make commands while gradually adopting Poetry.
2. **No Disruption**: Existing workflows continue to function throughout the migration.
3. **Better Dependency Management**: Poetry's lock file ensures consistent environments across all developers.
4. **Simplified Commands**: Poetry provides a more consistent interface for common operations.
5. **Modern Python Practices**: Aligns the project with current Python packaging standards.

## Conclusion

This migration plan provides a path to adopt Poetry for dependency management while maintaining the convenience of Make commands. By following this phased approach, we've successfully integrated Poetry without disrupting existing workflows.

The primary benefits achieved are:

1. **Modern Dependency Management**: Poetry provides robust dependency resolution and lock files for consistent environments.
2. **Simplified Virtual Environment Handling**: Poetry automatically manages virtual environments.
3. **Convenient Command Interface**: Make continues to provide short, memorable commands for common operations.
4. **Best of Both Worlds**: We're leveraging the strengths of both tools - Poetry for dependencies and Make for user interface.

The decision to keep Make as a complementary tool rather than replacing it entirely recognizes that Make excels at providing simple command shortcuts, while Poetry excels at dependency management. This hybrid approach gives us the benefits of both tools.
