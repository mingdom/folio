"""Tests for chart configuration consistency.

This module tests that all chart components use the standard chart configuration
to ensure a consistent user experience across the application.
"""

import ast
import inspect
import unittest
from pathlib import Path

from src.folio.components.charts import get_chart_config


class ChartConfigVisitor(ast.NodeVisitor):
    """AST visitor to find chart configuration in the code."""

    def __init__(self):
        self.chart_configs = []
        self.chart_config_calls = []

    # Note: AST visitor methods must match node type names exactly
    # We use a different approach to avoid linting issues
    def visit_Dict(self, node):  # noqa: N802
        """Visit dictionary nodes to find chart configurations."""
        # Check if this dictionary might be a chart config
        keys = []
        for keyword in node.keys:
            if isinstance(keyword, ast.Constant) and isinstance(keyword.value, str):
                keys.append(keyword.value)

        # If it has displayModeBar and scrollZoom, it's likely a chart config
        if "displayModeBar" in keys and "scrollZoom" in keys:
            self.chart_configs.append(node)

        # Continue visiting child nodes
        self.generic_visit(node)

    def visit_Call(self, node):  # noqa: N802
        """Visit function call nodes to find get_chart_config calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "get_chart_config":
            self.chart_config_calls.append(node)

        # Continue visiting child nodes
        self.generic_visit(node)


class TestChartConfig(unittest.TestCase):
    """Test chart configuration consistency."""

    def test_chart_config_consistency(self):
        """Test that all charts use the standard chart configuration."""
        # Get the standard chart configuration
        get_chart_config()

        # Get the path to the charts.py file
        charts_file = Path(inspect.getfile(get_chart_config))

        # Parse the file
        with open(charts_file, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        # Visit the AST to find chart configurations
        visitor = ChartConfigVisitor()
        visitor.visit(tree)

        # Check that there are chart configurations
        self.assertTrue(
            len(visitor.chart_configs) > 0,
            "No chart configurations found in the file",
        )

        # Check that there are get_chart_config calls
        self.assertTrue(
            len(visitor.chart_config_calls) > 0,
            "No get_chart_config calls found in the file",
        )

        # Check that the number of inline chart configs is less than or equal to 1
        # (we allow one for the get_chart_config function itself)
        self.assertLessEqual(
            len(visitor.chart_configs),
            1,
            f"Found {len(visitor.chart_configs)} inline chart configurations, "
            f"but expected at most 1 (in the get_chart_config function). "
            f"All charts should use get_chart_config() instead of inline configurations.",
        )

        # Check that all dcc.Graph components use get_chart_config
        # This is a more complex check that would require parsing the AST more deeply
        # For now, we'll just check that there are at least as many get_chart_config calls
        # as there are chart components (minus the one in the get_chart_config function)
        chart_components = self._count_chart_components(tree)
        self.assertGreaterEqual(
            len(visitor.chart_config_calls),
            chart_components,
            f"Found {len(visitor.chart_config_calls)} get_chart_config calls, "
            f"but expected at least {chart_components} (one for each chart component). "
            f"All charts should use get_chart_config() for configuration.",
        )

    def _count_chart_components(self, tree):
        """Count the number of chart components in the AST."""

        # This is a simplified version that just counts dcc.Graph calls
        class GraphVisitor(ast.NodeVisitor):
            def __init__(self):
                self.graph_count = 0

            def visit_Call(self, node):  # noqa: N802
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "dcc"
                    and node.func.attr == "Graph"
                ):
                    self.graph_count += 1
                self.generic_visit(node)

        visitor = GraphVisitor()
        visitor.visit(tree)
        return visitor.graph_count


if __name__ == "__main__":
    unittest.main()
