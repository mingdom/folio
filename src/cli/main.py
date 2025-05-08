#!/usr/bin/env python3
"""
Main entry point for the Folio CLI.

This module provides the main entry point for the Folio CLI, handling command-line
arguments and dispatching to the appropriate command handlers.

Usage:
    # Direct execution mode
    python -m src.cli [command] [subcommand] [options]

    # Interactive shell mode
    python -m src.cli
"""

import sys

import typer
from rich.console import Console

from src.folib.logger import logger

from . import __version__
from .commands.cache import cache_app
from .commands.portfolio import portfolio_app
from .commands.position import position_app
from .shell import start_interactive_shell

# Create the main Typer app
app = typer.Typer(
    name="folio",
    help="Folio CLI - Command-line interface for portfolio analysis",
    no_args_is_help=False,  # Don't show help when no args (launch interactive mode instead)
)

# Add subcommands
app.add_typer(cache_app, name="cache")
app.add_typer(portfolio_app, name="portfolio")
app.add_typer(position_app, name="position")

# Create console for rich output
console = Console()


def version_callback(value: bool):
    """Print version information and exit."""
    if value:
        console.print(f"Folio CLI version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        help="Show version and exit",
    ),
):
    """
    Folio CLI - Command-line interface for portfolio analysis.

    Run without arguments to start the interactive shell.
    """
    pass


def run():
    """Run the CLI application."""
    # Log the startup with the current log level
    logger.debug("Starting CLI application with DEBUG logging enabled")
    logger.info("CLI application starting")

    # If no arguments are provided, start the interactive shell
    if len(sys.argv) == 1:
        logger.debug("No arguments provided, starting interactive shell")
        start_interactive_shell()
        return

    # Otherwise, run the Typer app
    logger.debug(f"Running with arguments: {sys.argv[1:]}")
    app()


if __name__ == "__main__":
    run()
