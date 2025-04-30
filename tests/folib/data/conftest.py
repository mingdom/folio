"""
Pytest configuration for folib/data tests.

This file contains fixtures specific to testing the data module.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def mock_external_apis():
    """
    Mock all external API calls in the data module.

    This fixture is automatically applied to all tests in the data module.
    It patches common external API calls to prevent network requests.
    """
    # Create mock for yfinance.Ticker
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame(
        {
            "Open": [150.0],
            "High": [155.0],
            "Low": [148.0],
            "Close": [153.0],
            "Volume": [1000000],
        }
    )
    mock_ticker.info = {"beta": 1.2}

    # Create mock for yfinance.download
    mock_download = MagicMock(
        return_value=pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [148.0],
                "Close": [153.0],
                "Volume": [1000000],
            }
        )
    )

    # Mock yfinance
    with (
        patch("yfinance.Ticker", return_value=mock_ticker),
        patch("yfinance.download", mock_download),
    ):
        # Mock fmpsdk
        with (
            patch(
                "fmpsdk.historical_price_full",
                return_value={
                    "historical": [
                        {
                            "date": "2023-01-03",
                            "open": 150.0,
                            "high": 155.0,
                            "low": 148.0,
                            "close": 153.0,
                            "volume": 1000000,
                        }
                    ]
                },
            ),
            patch(
                "fmpsdk.historical_chart",
                return_value=[
                    {
                        "date": "2023-01-03 16:00:00",
                        "open": 150.0,
                        "high": 155.0,
                        "low": 148.0,
                        "close": 153.0,
                        "volume": 1000000,
                    }
                ],
            ),
            patch("fmpsdk.company_profile", return_value={}),
            patch("fmpsdk.quote", return_value=[]),
        ):
            yield
