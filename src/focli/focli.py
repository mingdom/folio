#!/usr/bin/env python3
"""
Folio CLI - Interactive command-line interface for Folio portfolio management.

This script provides an interactive shell for running portfolio simulations,
analyzing positions, and exploring investment scenarios.

Usage:
    python src/focli/focli.py                    # Start interactive shell
    python src/focli/focli.py --simulate         # Run simulation directly
    python src/focli/focli.py --simulate --preset quick  # Run quick simulation

Command-line Options:
    --simulate          Run portfolio simulation directly without entering interactive shell
    --preset NAME       Use a specific simulation preset (default, quick, detailed)

Interactive Commands:
    help                Show help information
    simulate spy        Simulate portfolio performance with SPY changes
    position <ticker>   Analyze a specific position group
    portfolio list      List all positions in the portfolio
    portfolio summary   Show a summary of the portfolio
    portfolio load      Load a portfolio from a CSV file
    exit                Exit the application
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.focli.shell import main

if __name__ == "__main__":
    main()
