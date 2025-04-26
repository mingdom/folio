"""
Tests for the security module.
"""

import base64
import io
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath('..'))

from src.folio.security import (
    sanitize_cell,
    sanitize_dangerous_content,
    sanitize_dataframe,
    sanitize_formula,
    validate_csv_upload,
)


class TestSecurity(unittest.TestCase):
    """Test cases for the security module."""

    def test_sanitize_cell(self):
        """Test sanitizing individual cell values."""
        # Test formula sanitization
        self.assertEqual(sanitize_cell("=SUM(A1:B1)"), "'=SUM(A1:B1)")
        self.assertEqual(sanitize_cell("@SUM(A1:B1)"), "'@SUM(A1:B1)")
        self.assertEqual(sanitize_cell("+SUM(A1:B1)"), "+SUM(A1:B1)")

        # Test HTML/script sanitization
        self.assertEqual(sanitize_cell("<script>alert('XSS')</script>"), "[REMOVED]")
        self.assertEqual(sanitize_cell("javascript:alert('XSS')"), "[REMOVED]alert('XSS')")
        self.assertEqual(sanitize_cell("<img src=x onerror=alert('XSS')>"), "<img src=x [REMOVED]=alert('XSS')>")

        # Test command injection sanitization
        self.assertEqual(sanitize_cell("value; rm -rf /"), "value rm -rf /")
        self.assertEqual(sanitize_cell("value | cat /etc/passwd"), "value  cat /etc/passwd")

        # Test non-string values
        self.assertEqual(sanitize_cell(123), "123")
        self.assertEqual(sanitize_cell(None), "None")

        # Test negative numbers (should not be modified)
        self.assertEqual(sanitize_cell("-123"), "-123")
        self.assertEqual(sanitize_cell("-123.45"), "-123.45")

        # Test financial values (should not be modified)
        self.assertEqual(sanitize_cell("$123.45"), "$123.45")
        self.assertEqual(sanitize_cell("-$123.45"), "-$123.45")
        self.assertEqual(sanitize_cell("+$123.45"), "+$123.45")

        # Test percentage values (should not be modified)
        self.assertEqual(sanitize_cell("-12.34%"), "-12.34%")
        self.assertEqual(sanitize_cell("+12.34%"), "+12.34%")
        self.assertEqual(sanitize_cell("12.34%"), "12.34%")

        # Test stock names with ampersands (should not be modified)
        self.assertEqual(sanitize_cell("S&P 500"), "S&P 500")
        self.assertEqual(sanitize_cell("PROSHARES ULTRAPRO S&P500"), "PROSHARES ULTRAPRO S&P500")

    def test_sanitize_formula(self):
        """Test sanitizing formula-like content."""
        self.assertEqual(sanitize_formula("=SUM(A1:B1)"), "'=SUM(A1:B1)")
        self.assertEqual(sanitize_formula("@SUM(A1:B1)"), "'@SUM(A1:B1)")
        self.assertEqual(sanitize_formula("+SUM(A1:B1)"), "'+SUM(A1:B1)")

        # Test that normal text is not modified
        self.assertEqual(sanitize_formula("Normal text"), "Normal text")

        # Test that negative numbers are not modified
        self.assertEqual(sanitize_formula("-123"), "-123")

        # Test financial values (should not be modified)
        self.assertEqual(sanitize_formula("$123.45"), "$123.45")
        self.assertEqual(sanitize_formula("-$123.45"), "-$123.45")
        self.assertEqual(sanitize_formula("+$123.45"), "+$123.45")

        # Test percentage values (should not be modified)
        self.assertEqual(sanitize_formula("-12.34%"), "-12.34%")
        self.assertEqual(sanitize_formula("+12.34%"), "+12.34%")
        self.assertEqual(sanitize_formula("12.34%"), "12.34%")

    def test_sanitize_dangerous_content(self):
        """Test sanitizing dangerous content while preserving financial data."""
        # Test financial values (should not be modified)
        self.assertEqual(sanitize_dangerous_content("$123.45"), "$123.45")
        self.assertEqual(sanitize_dangerous_content("-$123.45"), "-$123.45")
        self.assertEqual(sanitize_dangerous_content("+$123.45"), "+$123.45")

        # Test percentage values (should not be modified)
        self.assertEqual(sanitize_dangerous_content("-12.34%"), "-12.34%")
        self.assertEqual(sanitize_dangerous_content("+12.34%"), "+12.34%")
        self.assertEqual(sanitize_dangerous_content("12.34%"), "12.34%")

        # Test stock names with ampersands (should not be modified)
        self.assertEqual(sanitize_dangerous_content("S&P 500"), "S&P 500")
        self.assertEqual(sanitize_dangerous_content("PROSHARES ULTRAPRO S&P500"), "PROSHARES ULTRAPRO S&P500")

        # Test formula sanitization
        self.assertEqual(sanitize_dangerous_content("=SUM(A1:B1)"), "'=SUM(A1:B1)")
        self.assertEqual(sanitize_dangerous_content("@SUM(A1:B1)"), "'@SUM(A1:B1)")
        self.assertEqual(sanitize_dangerous_content("+SUM(A1:B1)"), "'+SUM(A1:B1)")

        # Test HTML/script sanitization
        self.assertEqual(sanitize_dangerous_content("<script>alert('XSS')</script>"), "[REMOVED]")
        self.assertEqual(sanitize_dangerous_content("javascript:alert('XSS')"), "[REMOVED]alert('XSS')")

        # Test command injection sanitization
        self.assertEqual(sanitize_dangerous_content("value; rm -rf /"), "value rm -rf /")
        self.assertEqual(sanitize_dangerous_content("value | cat /etc/passwd"), "value  cat /etc/passwd")

    def test_sanitize_dataframe(self):
        """Test sanitizing a DataFrame."""
        # Create a test DataFrame with potentially dangerous content
        df = pd.DataFrame({
            'Symbol': ['AAPL', '=SUM(A1:B1)', 'MSFT'],
            'Description': ['Apple Inc', '<script>alert("XSS")</script>', 'Microsoft Corp'],
            'Quantity': [100, 200, 300],
            'Last Price': ['$150.00', '=HYPERLINK("malicious.com")', '$250.00'],
        })

        # Sanitize the DataFrame
        sanitized_df = sanitize_dataframe(df)

        # Check that the dangerous content was sanitized
        self.assertEqual(sanitized_df.loc[1, 'Symbol'], "'=SUM(A1:B1)")
        self.assertEqual(sanitized_df.loc[1, 'Description'], "[REMOVED]")
        self.assertEqual(sanitized_df.loc[1, 'Last Price'], "'=HYPERLINK(\"malicious.com\")")

        # Check that safe content was not modified
        self.assertEqual(sanitized_df.loc[0, 'Symbol'], 'AAPL')
        self.assertEqual(sanitized_df.loc[0, 'Description'], 'Apple Inc')
        self.assertEqual(sanitized_df.loc[0, 'Quantity'], 100)

    def test_validate_csv_upload(self):
        """Test validating a CSV upload."""
        # Create a valid CSV file
        df = pd.DataFrame({
            'Symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'Quantity': [100, 200, 300],
            'Last Price': ['$150.00', '$250.00', '$2,500.00'],
        })

        # Convert to CSV and encode as base64
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_str = csv_buffer.getvalue()
        b64_content = base64.b64encode(csv_str.encode('utf-8')).decode('utf-8')
        contents = f"data:text/csv;base64,{b64_content}"

        # Validate the CSV upload
        result_df, error = validate_csv_upload(contents, "valid.csv")

        # Check that validation passed
        self.assertIsNone(error)
        self.assertEqual(len(result_df), 3)

        # Create a CSV with malicious content
        df = pd.DataFrame({
            'Symbol': ['AAPL', '=SUM(A1:B1)', 'MSFT'],
            'Quantity': [100, 200, 300],
            'Last Price': ['$150.00', '=HYPERLINK("malicious.com")', '$250.00'],
        })

        # Convert to CSV and encode as base64
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_str = csv_buffer.getvalue()
        b64_content = base64.b64encode(csv_str.encode('utf-8')).decode('utf-8')
        contents = f"data:text/csv;base64,{b64_content}"

        # Validate the CSV upload
        result_df, error = validate_csv_upload(contents, "malicious.csv")

        # Check that validation passed but content was sanitized
        self.assertIsNone(error)
        self.assertEqual(result_df.loc[1, 'Symbol'], "'=SUM(A1:B1)")
        self.assertEqual(result_df.loc[1, 'Last Price'], "'=HYPERLINK(\"malicious.com\")")

        # Test with invalid file extension
        with self.assertRaises(ValueError) as context:
            validate_csv_upload(contents, "invalid.txt")
        self.assertIn("Only CSV files are supported", str(context.exception))

        # Test with missing required columns
        df = pd.DataFrame({
            'Symbol': ['AAPL', 'MSFT', 'GOOGL'],
            # Missing 'Quantity' and 'Last Price'
        })

        # Convert to CSV and encode as base64
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_str = csv_buffer.getvalue()
        b64_content = base64.b64encode(csv_str.encode('utf-8')).decode('utf-8')
        contents = f"data:text/csv;base64,{b64_content}"

        # Validate the CSV upload
        with self.assertRaises(ValueError) as context:
            validate_csv_upload(contents, "missing_columns.csv")
        self.assertIn("Missing required columns", str(context.exception))


if __name__ == '__main__':
    unittest.main()
