"""Tests for the main execution logic (run_feed_processing)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src directory to path to allow importing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Import the function we want to test
# Import the config class to create test instances
from rss_buddy.config import RssBuddyConfig
from rss_buddy.main import run_feed_processing


class TestRunFeedProcessing(unittest.TestCase):
    """Test the run_feed_processing function and component initialization."""

    @patch("rss_buddy.main.StateManager")
    @patch("rss_buddy.main.AIInterface")
    @patch("rss_buddy.main.FeedProcessor")
    @patch("rss_buddy.main.RobustDateParser")  # Mock date parser if needed, though often not
    def test_run_feed_processing_initializes_components_correctly(
        self,
        mock_date_parser,
        mock_feed_processor,
        mock_ai_interface,
        mock_state_manager,
    ):
        """Verify run_feed_processing initializes components correctly based on config."""
        # --- Setup Test Config --- #
        test_config = RssBuddyConfig(
            openai_api_key="test_key_123",
            rss_feeds=["http://test.feed/rss", "http://another.feed/rss"],
            user_preference_criteria="Test Criteria Here",
            days_lookback=5,
            ai_model="test-ai-model",
            summary_max_tokens=120,
            output_dir="test_output_dir",
        )

        # --- Setup Mocks --- #
        # Mock the instances returned by the classes
        mock_state_manager_instance = MagicMock()
        mock_state_manager.return_value = mock_state_manager_instance

        mock_ai_interface_instance = MagicMock()
        mock_ai_interface.return_value = mock_ai_interface_instance

        mock_feed_processor_instance = MagicMock()
        # Mock the process_feeds method on the instance
        mock_feed_processor_instance.process_feeds.return_value = []
        mock_feed_processor.return_value = mock_feed_processor_instance

        mock_date_parser_instance = MagicMock()
        mock_date_parser.return_value = mock_date_parser_instance

        # --- Run Test --- #
        # Call the function with the test config
        run_feed_processing(config=test_config)

        # --- Assertions --- #

        # Check DateParser initialization (usually not mocked, but if needed)
        mock_date_parser.assert_called_once()

        # Check StateManager initialization with values from config
        mock_state_manager.assert_called_once_with(
            date_parser=mock_date_parser_instance, output_dir=test_config.output_dir
        )

        # Check AIInterface initialization with values from config
        mock_ai_interface.assert_called_once_with(
            api_key=test_config.openai_api_key, model=test_config.ai_model
        )

        # Check FeedProcessor initialization with values from config
        mock_feed_processor.assert_called_once_with(
            state_manager=mock_state_manager_instance,
            ai_interface=mock_ai_interface_instance,
            date_parser=mock_date_parser_instance,
            days_lookback=test_config.days_lookback,
            user_preference_criteria=test_config.user_preference_criteria,
            summary_max_tokens=test_config.summary_max_tokens,
        )

        # Check that process_feeds was called with feeds from config
        mock_feed_processor_instance.process_feeds.assert_called_once_with(test_config.rss_feeds)


if __name__ == "__main__":
    unittest.main()
