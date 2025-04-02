"""Tests for the main execution script."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src directory to path to allow importing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Import the main function we want to test
from rss_buddy.main import main as rss_buddy_main


class TestMainExecution(unittest.TestCase):
    """Test the main function execution and component initialization."""

    @patch("rss_buddy.main.StateManager")
    @patch("rss_buddy.main.AIInterface")
    @patch("rss_buddy.main.FeedProcessor")
    @patch("rss_buddy.main.get_env_list")
    @patch("rss_buddy.main.get_env_str")
    @patch("rss_buddy.main.get_env_int")
    @patch("rss_buddy.main.os.environ.get")  # Mock os.environ.get for OUTPUT_DIR
    def test_main_initializes_feed_processor_correctly(
        self,
        mock_os_environ_get,
        mock_get_env_int,
        mock_get_env_str,
        mock_get_env_list,
        mock_feed_processor,
        mock_ai_interface,
        mock_state_manager,
    ):
        """Verify main() initializes FeedProcessor without output_dir."""
        # --- Setup Mocks ---
        # Mock environment variable functions to return dummy values
        mock_get_env_list.return_value = ["http://test.feed/rss"]
        mock_get_env_str.side_effect = (
            lambda key: f"dummy_{key}"
        )  # Return dummy string based on key
        mock_get_env_int.return_value = 1  # Return dummy int
        # Mock os.environ.get specifically for OUTPUT_DIR
        # The first call is for OUTPUT_DIR, return a dummy value
        # Subsequent calls (if any) can return None or raise errors if unexpected
        mock_os_environ_get.return_value = "dummy_output_dir"

        # Mock the instances returned by the classes
        mock_state_manager_instance = MagicMock()
        mock_state_manager.return_value = mock_state_manager_instance

        mock_ai_interface_instance = MagicMock()
        mock_ai_interface.return_value = mock_ai_interface_instance

        mock_feed_processor_instance = MagicMock()
        mock_feed_processor_instance.process_feeds.return_value = []  # Mock process_feeds
        mock_feed_processor.return_value = mock_feed_processor_instance

        # --- Run Test ---
        # Call the main function
        return_code = rss_buddy_main()

        # --- Assertions ---
        self.assertEqual(return_code, 0)  # Expect success

        # Check StateManager initialization
        mock_state_manager.assert_called_once_with(output_dir="dummy_output_dir")

        # Check AIInterface initialization
        mock_ai_interface.assert_called_once()
        # Get the keyword args passed to AIInterface constructor
        ai_kwargs = mock_ai_interface.call_args.kwargs
        self.assertEqual(ai_kwargs.get("api_key"), "dummy_OPENAI_API_KEY")
        self.assertEqual(ai_kwargs.get("model"), "dummy_AI_MODEL")

        # Check FeedProcessor initialization
        mock_feed_processor.assert_called_once()
        # Get keyword args passed to FeedProcessor constructor
        fp_kwargs = mock_feed_processor.call_args.kwargs

        # Assert that 'output_dir' is NOT in the keyword arguments
        self.assertNotIn("output_dir", fp_kwargs)

        # Assert that the expected arguments *are* present
        self.assertEqual(fp_kwargs.get("state_manager"), mock_state_manager_instance)
        self.assertEqual(fp_kwargs.get("ai_interface"), mock_ai_interface_instance)
        self.assertEqual(fp_kwargs.get("days_lookback"), 1)  # From mock_get_env_int
        self.assertEqual(
            fp_kwargs.get("user_preference_criteria"), "dummy_USER_PREFERENCE_CRITERIA"
        )
        self.assertEqual(fp_kwargs.get("summary_max_tokens"), 1)  # From mock_get_env_int

        # Check that process_feeds was called
        mock_feed_processor_instance.process_feeds.assert_called_once_with(["http://test.feed/rss"])


if __name__ == "__main__":
    unittest.main()
