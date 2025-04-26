# Poetry Commands for Folio Project

This document provides a reference for common Poetry commands used in the Folio project.

## Installation

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Configure Poetry to create virtual environments in the project directory
poetry config virtualenvs.in-project true
```

## Basic Commands

### Environment Management

```bash
# Create/initialize a virtual environment
poetry env use python3

# Activate the virtual environment
poetry shell

# Exit the virtual environment
exit  # or Ctrl+D
```

### Dependency Management

```bash
# Install all dependencies from pyproject.toml
poetry install

# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Note: The dev group includes both development tools (linting, testing)
# and CLI tools (focli interactive shell)

# Update all dependencies
poetry update

# Update a specific dependency
poetry update package-name

# Show installed packages
poetry show

# Show dependency tree
poetry show --tree
```

## Running Commands

```bash
# Run a command within the virtual environment
poetry run python -m src.folio.app

# Run the linter
poetry run ruff check --fix --unsafe-fixes .

# Run tests
poetry run pytest tests/

# Run end-to-end tests
poetry run pytest tests/e2e/
```

## Project Commands

These commands replace the traditional Make commands:

```bash
# Start the portfolio dashboard
poetry run python -m src.folio.app --port 8051 --debug

# Start the portfolio dashboard with sample portfolio
poetry run python -m src.folio.app --port 8051 --debug --portfolio src/folio/assets/sample-portfolio.csv

# Run the SPY simulator
poetry run python ./scripts/folio-simulator.py

# Start the Folio CLI interactive shell
poetry run python src/!focli/focli.py
```

## Advanced Commands

```bash
# Export dependencies to requirements.txt
poetry export -f requirements.txt --output requirements.txt

# Export development dependencies
poetry export --with dev -f requirements.txt --output requirements-dev.txt

# Build the project
poetry build

# Check for dependency conflicts
poetry check
```

## Troubleshooting

```bash
# Clear Poetry's cache
poetry cache clear --all pypi

# Update Poetry itself
poetry self update

# Get Poetry version
poetry --version

# Get detailed environment info (useful for debugging)
poetry env info
```

## Make Integration

The Folio project has integrated Poetry into its Makefile, so you can continue to use familiar Make commands:

```bash
# Set up Poetry and create a virtual environment
make env

# Install dependencies using Poetry
make install

# Run linter using Poetry
make lint

# Run tests using Poetry
make test

# Run the application using Poetry
make folio
```

All these Make commands now use Poetry under the hood, providing a seamless transition to the new dependency management system.
