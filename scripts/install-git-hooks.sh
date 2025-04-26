#!/bin/bash

# Script to install git hooks using pre-commit

echo "Installing git hooks with pre-commit..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Please install Poetry first."
    exit 1
fi

# Install pre-commit hooks
poetry run pre-commit install

echo "Git hooks installed successfully!"
