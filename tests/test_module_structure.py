"""Tests for module structure and dependencies."""

import importlib

import pytest


class TestModuleStructure:
    """Tests for module structure and dependencies."""

    def test_utils_module_functions(self):
        """Test that utils module functions are correctly imported and working."""
        # Import the modules
        from src.folio import cash_detection, formatting, portfolio, utils

        # Verify that key functions exist in formatting.py
        assert hasattr(formatting, "format_beta")
        assert hasattr(formatting, "format_currency")
        assert hasattr(formatting, "format_compact_currency")
        assert hasattr(formatting, "format_percentage")
        assert hasattr(formatting, "format_delta")

        # Verify that key functions exist in utils.py
        assert hasattr(utils, "get_beta")
        assert hasattr(utils, "clean_currency_value")

        # Verify that key functions exist in portfolio.py
        assert hasattr(portfolio, "process_portfolio_data")

        # Verify that key functions exist in cash_detection.py
        assert hasattr(cash_detection, "is_cash_or_short_term")

        # Test that the formatting functions work correctly
        assert formatting.format_beta(1.2) == "1.20β"
        assert formatting.format_currency(1500.0) == "$1,500.00"
        assert formatting.format_percentage(0.25) == "25.0%"
        assert formatting.format_compact_currency(1500000.0) == "$1.5M"

        # Test cash detection functions
        assert cash_detection.is_cash_or_short_term("SPAXX")
        assert cash_detection.is_cash_or_short_term("FDRXX")
        assert not cash_detection.is_cash_or_short_term("AAPL")

        # Test beta function with a known ticker would go here
        # This would need to be mocked in a real test

    def test_module_dependencies(self):
        """Test module dependencies and structure."""
        # Import all key modules to ensure they load correctly
        modules_to_test = [
            "src.folio.utils",
            "src.folio.data_model",
            "src.folio.ai_utils",
            "src.folio.gemini_client",
        ]

        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e!s}")

        # Verify that key classes exist in data_model
        from src.folio import data_model

        assert hasattr(data_model, "PortfolioGroup")
        assert hasattr(data_model, "StockPosition")
        assert hasattr(data_model, "OptionPosition")
        assert hasattr(data_model, "PortfolioSummary")
        assert hasattr(data_model, "ExposureBreakdown")

        # Verify that from_dict methods exist
        assert hasattr(data_model.PortfolioGroup, "from_dict")
        assert hasattr(data_model.StockPosition, "from_dict")
        assert hasattr(data_model.OptionPosition, "from_dict")
        assert hasattr(data_model.PortfolioSummary, "from_dict")
        assert hasattr(data_model.ExposureBreakdown, "from_dict")

        # Verify AI utilities
        from src.folio import ai_utils

        assert hasattr(ai_utils, "prepare_portfolio_data_for_analysis")
        assert hasattr(ai_utils, "PORTFOLIO_ADVISOR_SYSTEM_PROMPT")

        # Verify Gemini client
        from src.folio import gemini_client

        assert hasattr(gemini_client, "GeminiClient")
        assert hasattr(gemini_client.GeminiClient, "chat")
        assert hasattr(gemini_client.GeminiClient, "chat_sync")

    def test_app_imports(self):
        """Test that the app imports are working correctly."""
        try:
            # Import the app module
            from src.folio import app

            # Verify that key components exist
            assert hasattr(app, "create_app")

            # Verify key components are imported in app
            assert hasattr(app, "create_dashboard_section")
            assert hasattr(app, "create_portfolio_table")
            assert hasattr(
                app, "create_pnl_modal"
            )  # Updated to use the new PnL modal instead of position details
            assert hasattr(app, "create_summary_cards")

        except ImportError as e:
            pytest.fail(f"Failed to import app module: {e!s}")
        except AttributeError as e:
            pytest.fail(f"Failed to access attribute in app module: {e!s}")
