#!/bin/bash
# Script to install all required dependencies for the omninmo project

echo "Installing dependencies for omninmo..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Get the project root directory
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Not in a virtual environment. Please activate the virtual environment first."
    exit 1
fi

# Function to check if a package is installed
is_package_installed() {
    python3 -m pip show "$1" &> /dev/null
}

# Install packages with proper flags to avoid system conflicts
install_package() {
    echo "Installing $1..."
    python3 -m pip install --no-cache-dir "$1" --no-warn-script-location
}

# Install matplotlib separately first with specific flags
echo "Installing matplotlib..."
if ! is_package_installed "matplotlib"; then
    CFLAGS="-I/opt/homebrew/include -I/opt/homebrew/include/freetype2" \
    LDFLAGS="-L/opt/homebrew/lib" \
    python3 -m pip install --no-cache-dir matplotlib --no-warn-script-location
fi

# Install Folio app dependencies from requirements.txt
echo "Installing Folio app dependencies from requirements.txt..."
while IFS= read -r package || [ -n "$package" ]; do
    # Skip empty lines and comments
    if [[ -z "$package" || "$package" =~ ^# ]]; then
        continue
    fi
    install_package "$package"
done < "$PROJECT_ROOT/requirements.txt"

# Install additional development dependencies from requirements.txt
echo "Installing additional development dependencies from requirements.txt..."
while IFS= read -r package || [ -n "$package" ]; do
    # Skip empty lines and comments
    if [[ -z "$package" || "$package" =~ ^# ]]; then
        continue
    fi
    # Skip matplotlib as we've already installed it
    if [[ "$package" != matplotlib* ]]; then
        install_package "$package"
    fi
done < "$PROJECT_ROOT/requirements.txt"

# Install development tools from requirements-dev.txt
echo "Installing development tools from requirements-dev.txt..."
while IFS= read -r package || [ -n "$package" ]; do
    # Skip empty lines and comments
    if [[ -z "$package" || "$package" =~ ^# ]]; then
        continue
    fi
    install_package "$package"
done < "$PROJECT_ROOT/requirements-dev.txt"

# Make all Python scripts executable
echo "Making Python scripts executable..."
chmod +x "$SCRIPT_DIR"/*.py

echo "Installation complete!"
