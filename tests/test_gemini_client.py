"""Tests for the Gemini AI client."""

import os
import unittest
from unittest.mock import MagicMock, patch

import pytest

from src.folio.gemini_client import GeminiClient


class TestGeminiClient(unittest.TestCase):
    """Tests for the Gemini AI client."""

    def setUp(self):
        """Set up test environment."""
        # Save original environment
        self.original_env = os.environ.copy()
        # Set test API key
        os.environ["GEMINI_API_KEY"] = "test_api_key"

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_init_with_api_key(self, mock_model, mock_configure):
        """Test that the client initializes correctly with an API key."""
        # Set up mock
        mock_model.return_value = MagicMock()

        # Initialize client
        client = GeminiClient()

        # Check that configure was called with the API key
        mock_configure.assert_called_once_with(api_key="test_api_key")
        # Check that the model was initialized
        mock_model.assert_called_once()
        # Check that the model is available
        assert hasattr(client, "model")

    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_init_without_api_key(self, mock_model, mock_configure):
        """Test that the client raises an error when no API key is provided."""
        # Remove API key from environment
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        # Check that initializing the client raises an error
        with pytest.raises(
            ValueError, match="GEMINI_API_KEY environment variable not set"
        ):
            GeminiClient()

        # Check that configure was not called
        mock_configure.assert_not_called()
        # Check that the model was not initialized
        mock_model.assert_not_called()

    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_chat_sync_basic(self, mock_model, _mock_configure):
        """Test that the chat_sync method works correctly."""
        # Set up mocks
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance

        # Set up chat session mock
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat

        # Set up response mock
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_chat.send_message.return_value = mock_response

        # Initialize client
        client = GeminiClient()

        # Call chat_sync
        result = client.chat_sync("Test message", [])

        # Check that the chat session was created
        mock_model_instance.start_chat.assert_called_once()

        # Check that send_message was called with the message
        mock_chat.send_message.assert_called_once()

        # Check the result
        assert result["response"] == "Test response"
        assert result["complete"] is True

    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_chat_sync_with_error(self, mock_model, _mock_configure):
        """Test that the chat_sync method handles errors correctly."""
        # Set up mocks
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance

        # Set up chat session mock to raise an exception
        mock_model_instance.start_chat.side_effect = Exception("Test error")

        # Initialize client
        client = GeminiClient()

        # Call chat_sync
        result = client.chat_sync("Test message", [])

        # Check the result
        assert "error" in result
        assert result["error"] is True
        assert "Test error" in result["response"]
        assert result["complete"] is False
