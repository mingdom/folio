# Makefile for folio project

# Variables
SHELL := /bin/bash
PYTHON := python3
SCRIPTS_DIR := scripts
LOGS_DIR := logs
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)
PORT := 5000
POETRY := poetry

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help        - Show this help message"
	@echo "  env         - Set up Poetry and create a virtual environment"
	@echo "  install     - Install dependencies and set script permissions"
	@echo "  hooks       - Install git hooks for pre-commit checks"
	@echo "  folio       - Start the portfolio dashboard with debug mode enabled"
	@echo "               Options: portfolio=path/to/file.csv (use custom portfolio file)"
	@echo "                        log=LEVEL (set logging level: DEBUG, INFO, WARNING, ERROR)"
	@echo "  focli       - Start the interactive Folio CLI shell for portfolio analysis"
	@echo "  simulate    - Run portfolio simulation using the improved simulator_v2"
	@echo "  sim         - Alias for simulate (shorter to type)"
	@echo "               Options: ticker=SYMBOL (focus on a specific ticker)"
	@echo "                        detailed=1 (show detailed position-level results)"
	@echo "                        portfolio=path/to/file.csv (use custom portfolio file)"
	@echo "               Default: -20% to +20% SPY change with 2% increments"
	@echo "  analyze     - Analyze position contributions to portfolio performance"
	@echo "               Options: focus_spy=0.06 (focus on a specific SPY change level)"
	@echo "                        top_n=10 (show top N contributors)"
	@echo "                        portfolio=path/to/file.csv (use custom portfolio file)"
	@echo "  clean       - Clean up generated files and caches"
	@echo "               Options: --cache (also clear data cache)"
	@echo "  lint        - Run type checker and linter"
	@echo "               Options: --fix (auto-fix linting issues)"
	@echo "  test        - Run all unit tests in the tests directory"
	@echo "  test-e2e    - Run end-to-end tests against real portfolio data"
	@echo ""
	@echo "Note: All targets now use Poetry under the hood for dependency management"
	@echo ""
	@echo "Docker targets:"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-run   - Run the Docker container"
	@echo "  docker-up    - Start the application with docker-compose"
	@echo "  docker-down  - Stop the docker-compose services"
	@echo "  docker-logs  - Tail the Docker logs"
	@echo "  docker-test  - Run tests in a Docker container"

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

# Install git hooks
.PHONY: hooks
hooks:
	@echo "Installing git hooks..."
	@if ! command -v $(POETRY) &> /dev/null; then \
		echo "Poetry not found. Please run 'make env' first."; \
		exit 1; \
	fi
	@$(POETRY) run pre-commit install -c .pre-commit-config.yaml --hook-type pre-commit
	@$(POETRY) run pre-commit install -c .pre-push-config.yaml --hook-type pre-push
	@echo "Git hooks installed successfully!"

# Clean up generated files
.PHONY: clean
clean:
	@echo "Cleaning up generated files..."
	@bash $(SCRIPTS_DIR)/clean.sh
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@if [ "$(findstring --cache,$(MAKECMDGOALS))" != "" ]; then \
		echo "Clearing data cache..."; \
		rm -rf cache/*; \
		mkdir -p cache; \
		echo "Cache cleared."; \
	fi

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
	$(POETRY) run ruff check --fix --unsafe-fixes src/ tests/ \
	2>&1) | tee $(LOGS_DIR)/code_check_latest.log
	@echo "Check log saved to: $(LOGS_DIR)/code_check_latest.log"

# Allow --fix as target without actions
.PHONY: --fix
--fix:

# Portfolio and CLI Projects
.PHONY: folio stop-folio port focli simulate

# Poetry is used under the hood for all targets

# Docker targets
.PHONY: docker-build docker-run docker-up docker-down docker-logs docker-compose-up docker-compose-down docker-test deploy-hf

folio:
	@echo "Starting portfolio dashboard with debug mode..."
	@if ! command -v $(POETRY) &> /dev/null; then \
		echo "Poetry not found. Please run 'make env' first."; \
		exit 1; \
	fi
	@LOG_LEVEL=$(if $(log),$(log),INFO) \
	$(POETRY) run python -m src.folio.app --port 8051 --debug $(if $(portfolio),--portfolio $(portfolio),)

stop-folio:
	@echo "Stopping portfolio dashboard..."
	@PIDS=$$(ps aux | grep "[p]ython.*folio" | awk '{print $$2}'); \
	if [ -n "$$PIDS" ]; then \
		echo "Found folio processes with PIDs: $$PIDS"; \
		for PID in $$PIDS; do \
			echo "Killing process $$PID..."; \
			kill -9 $$PID 2>/dev/null || echo "Failed to kill process $$PID (might require sudo)"; \
		done; \
		echo "All folio processes have been terminated."; \
	else \
		echo "No running folio processes found."; \
	fi



focli:
	@echo "Starting Folio CLI interactive shell..."
	@if ! command -v $(POETRY) &> /dev/null; then \
		echo "Poetry not found. Please run 'make env' first."; \
		exit 1; \
	fi
	@$(POETRY) run python src/focli/focli.py

simulate:
	@echo "Running portfolio simulation with simulator_v2..."
	@if ! command -v $(POETRY) &> /dev/null; then \
		echo "Poetry not found. Please run 'make env' first."; \
		exit 1; \
	fi
	@if [ -n "$(portfolio)" ]; then \
		$(POETRY) run python -m src.focli.commands.sim $(portfolio) --min-spy-change -0.1 --max-spy-change 0.1 --steps 5 $(if $(ticker),--ticker $(ticker),) $(if $(detailed),--detailed,) $(if $(type),--position-type $(type),); \
	elif [ -f "@private-data/private-portfolio.csv" ]; then \
		$(POETRY) run python -m src.focli.commands.sim @private-data/private-portfolio.csv --min-spy-change -0.1 --max-spy-change 0.1 --steps 5 $(if $(ticker),--ticker $(ticker),) $(if $(detailed),--detailed,) $(if $(type),--position-type $(type),); \
	elif [ -f "private-data/portfolio-private.csv" ]; then \
		$(POETRY) run python -m src.focli.commands.sim private-data/portfolio-private.csv --min-spy-change -0.1 --max-spy-change 0.1 --steps 5 $(if $(ticker),--ticker $(ticker),) $(if $(detailed),--detailed,) $(if $(type),--position-type $(type),); \
	else \
		echo "Error: Portfolio file not found. Please specify a file path:"; \
		echo "  make simulate portfolio=path/to/your/portfolio.csv"; \
		exit 1; \
	fi

analyze:
	@echo "Analyzing position contributions to portfolio performance..."
	@if ! command -v $(POETRY) &> /dev/null; then \
		echo "Poetry not found. Please run 'make env' first."; \
		exit 1; \
	fi
	@if [ -n "$(portfolio)" ]; then \
		$(POETRY) run python -m src.focli.commands.analyze $(portfolio) --min-spy-change -0.2 --max-spy-change 0.2 --steps 21 $(if $(focus_spy),--focus-spy $(focus_spy),) $(if $(top_n),--top-n $(top_n),); \
	elif [ -f "@private-data/private-portfolio.csv" ]; then \
		$(POETRY) run python -m src.focli.commands.analyze @private-data/private-portfolio.csv --min-spy-change -0.2 --max-spy-change 0.2 --steps 21 $(if $(focus_spy),--focus-spy $(focus_spy),) $(if $(top_n),--top-n $(top_n),); \
	elif [ -f "private-data/portfolio-private.csv" ]; then \
		$(POETRY) run python -m src.focli.commands.analyze private-data/portfolio-private.csv --min-spy-change -0.2 --max-spy-change 0.2 --steps 21 $(if $(focus_spy),--focus-spy $(focus_spy),) $(if $(top_n),--top-n $(top_n),); \
	else \
		echo "Error: Portfolio file not found. Please specify a file path:"; \
		echo "  make analyze portfolio=path/to/your/portfolio.csv"; \
		exit 1; \
	fi

# Alias for simulate
sim: simulate

# Test targets
.PHONY: test test-e2e simulate analyze sim
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

# Docker commands
docker-build:
	@echo "Building Docker image..."
	docker build --debug -t folio:latest .

# Run the Docker container
docker-run:
	@echo "Running Docker container..."
	docker run -p 8050:8050 --env-file .env folio:latest

# Start with docker-compose
docker-up:
	@echo "Starting with docker-compose..."
	docker-compose up -d
	@echo "Folio app launched successfully!"
	@echo "Access the app at: http://localhost:8060"

# Stop docker-compose services
docker-down:
	@echo "Stopping docker-compose services..."
	docker-compose down

# Alias for backward compatibility
docker-compose-up: docker-up
docker-compose-down: docker-down

# Tail Docker logs
docker-logs:
	@echo "Tailing Docker logs..."
	docker-compose logs -f

# Run tests in Docker container
docker-test:
	@echo "Running tests in Docker container..."
	@if [ -z "$$GEMINI_API_KEY" ]; then \
		echo "Warning: GEMINI_API_KEY environment variable not set. Some tests may fail."; \
	fi
	@docker-compose -f docker-compose.test.yml build --build-arg INSTALL_DEV=true
	@docker-compose -f docker-compose.test.yml run --rm folio

# Deploy to Hugging Face Spaces
deploy-hf:
	@echo "Deploying to Hugging Face Spaces..."
	@echo "Checking if Hugging Face Space remote exists..."
	@if ! git remote | grep -q "space"; then \
		echo "Adding Hugging Face Space remote..."; \
		git remote add space git@hf.co:spaces/mingdom/folio; \
	fi
	@echo "Pushing to Hugging Face Space..."
	@git push space main:main
	@echo "\n✅ Deployment to Hugging Face Space completed!"
	@echo "Your application is now available at: https://huggingface.co/spaces/mingdom/folio"

%:
	@:
