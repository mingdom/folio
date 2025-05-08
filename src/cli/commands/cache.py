"""
Cache management commands for the Folio CLI.

This module provides implementations of the cache commands for the Folio CLI,
including clear and status.
"""

import typer
from rich.console import Console

from src.folib.data.market_data import MarketDataProvider

# Create Typer app for cache commands
cache_app = typer.Typer(help="Manage the data cache")

# Create console for rich output
console = Console()


@cache_app.command("clear")
def cache_clear_cmd(
    backup: bool = typer.Option(
        True, "--no-backup/--backup", help="Whether to backup the cache before clearing"
    ),
):
    """Clear the data cache to force fresh data fetching.

    By default, a backup of the cache is created before clearing.
    Use --no-backup to skip creating a backup.
    """
    try:
        # Initialize market data provider
        market_data = MarketDataProvider()

        # Clear the cache
        if backup:
            console.print(
                "[yellow]Creating backup of cache before clearing...[/yellow]"
            )
        else:
            console.print("[yellow]Clearing cache without backup...[/yellow]")

        market_data.clear_all_cache(backup=backup)

        # Print success message
        if backup:
            console.print(
                "[green]Cache cleared successfully with backup created[/green]"
            )
        else:
            console.print("[green]Cache cleared successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {e!s}")
        raise typer.Exit(code=1) from e


@cache_app.command("status")
def cache_status_cmd():
    """Show cache statistics and status."""
    try:
        # Initialize market data provider
        market_data = MarketDataProvider()

        # Log cache statistics
        console.print("[bold]Cache Statistics:[/bold]")
        market_data.log_cache_statistics()

    except Exception as e:
        console.print(f"[red]Error getting cache status:[/red] {e!s}")
        raise typer.Exit(code=1) from e


# Interactive mode command functions
def cache_clear(state, args):  # noqa: ARG001
    """Clear the data cache (interactive mode)."""
    backup = True

    # Parse arguments
    if args and "--no-backup" in args:
        backup = False

    try:
        # Initialize market data provider
        market_data = MarketDataProvider()

        # Clear the cache
        if backup:
            console.print(
                "[yellow]Creating backup of cache before clearing...[/yellow]"
            )
        else:
            console.print("[yellow]Clearing cache without backup...[/yellow]")

        market_data.clear_all_cache(backup=backup)

        # Print success message
        if backup:
            console.print(
                "[green]Cache cleared successfully with backup created[/green]"
            )
        else:
            console.print("[green]Cache cleared successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {e!s}")


def cache_status(state, args):  # noqa: ARG001
    """Show cache statistics and status (interactive mode)."""
    try:
        # Initialize market data provider
        market_data = MarketDataProvider()

        # Log cache statistics
        console.print("[bold]Cache Statistics:[/bold]")
        market_data.log_cache_statistics()

    except Exception as e:
        console.print(f"[red]Error getting cache status:[/red] {e!s}")
