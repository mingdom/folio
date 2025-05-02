"""
State management for the interactive shell.

This module provides a State class for managing session state in the interactive shell,
including the loaded portfolio and other session-specific data.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.folib.domain import Portfolio, PortfolioSummary


@dataclass
class State:
    """State for the interactive shell session."""

    # Portfolio state
    loaded_portfolio_path: Path | None = None
    portfolio_df: pd.DataFrame | None = None
    portfolio: Portfolio | None = None
    portfolio_summary: PortfolioSummary | None = None

    # Command history
    command_history: list[str] = field(default_factory=list)

    # User preferences
    preferences: dict[str, Any] = field(default_factory=dict)

    def clear(self):
        """Clear the state."""
        self.loaded_portfolio_path = None
        self.portfolio_df = None
        self.portfolio = None
        self.portfolio_summary = None
        self.command_history = []

    def add_to_history(self, command: str):
        """Add a command to the history."""
        self.command_history.append(command)

    def has_portfolio(self) -> bool:
        """Check if a portfolio is loaded."""
        return self.portfolio is not None
