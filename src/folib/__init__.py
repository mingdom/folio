"""
Folib - Portfolio Analysis Library

A functional-first library for portfolio analysis, simulation, and management.

This library follows a clean, modular architecture with a focus on:
- Functional programming principles
- Clear separation of concerns
- Explicit data flow
- Minimal dependencies between components

Architecture Overview:
---------------------
- domain.py: Core data models for portfolio analysis
- calculations/: Pure calculation functions with no side effects
- data/: Data access layer for external sources and file loading
- services/: Orchestration layer that combines the other components

Key Features:
------------
- Portfolio loading and parsing from CSV files
- Market data retrieval with caching (via yfinance and FMP API)
- Position and portfolio analysis
- Exposure calculations and risk metrics
- Option pricing and Greeks calculations
- Portfolio simulation

Usage:
-----
The library is designed to be used primarily through the service layer,
which provides high-level functions that orchestrate the lower-level
components to fulfill specific use cases.
"""

__version__ = "0.1.0"
