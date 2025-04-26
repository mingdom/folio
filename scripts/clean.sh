#!/bin/bash
# Script to clean up generated files

echo "Cleaning up generated files..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Get the project root directory
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Remove Python cache files
echo "Removing Python cache files..."
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} +
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete
find "$PROJECT_ROOT" -type f -name "*.pyo" -delete
find "$PROJECT_ROOT" -type f -name "*.pyd" -delete

# Remove model files
echo "Removing model files..."
rm -rf "$PROJECT_ROOT/models"/*.pkl

# Remove cache files
echo "Removing cache files..."
rm -rf "$PROJECT_ROOT/cache"/*

echo "Cleanup complete!" 