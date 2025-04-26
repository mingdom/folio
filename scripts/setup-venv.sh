#!/bin/bash
# Script to set up and use a virtual environment for the omninmo project

echo "Setting up virtual environment for omninmo..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Get the project root directory
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Define the virtual environment directory
VENV_DIR="$PROJECT_ROOT/venv"

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install python3 first."
    exit 1
fi

# Check if venv module is available
if ! python3 -m venv --help &> /dev/null; then
    echo "Error: python3-venv is not installed. Please install it first."
    echo "On Ubuntu/Debian: sudo apt-get install python3-venv"
    echo "On Fedora: sudo dnf install python3-venv"
    echo "On macOS: python3 -m pip install --user virtualenv"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created successfully."
else
    echo "Virtual environment already exists at $VENV_DIR."
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip3 install --upgrade pip

# Create a script to activate the virtual environment
ACTIVATE_SCRIPT="$PROJECT_ROOT/activate-venv.sh"
echo "Creating activation script at $ACTIVATE_SCRIPT..."
cat > "$ACTIVATE_SCRIPT" << EOF
#!/bin/bash
# Script to activate the virtual environment
source "$VENV_DIR/bin/activate"
echo "Virtual environment activated. Run 'deactivate' to exit."
EOF

chmod +x "$ACTIVATE_SCRIPT"

echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run: source $ACTIVATE_SCRIPT"
echo "To install dependencies in the virtual environment, run: make install" 