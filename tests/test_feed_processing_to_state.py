"""Tests the integration between feed processing and state saving."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Add path to allow importing package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rss_buddy.ai_interface import MockAIInterface
from rss_buddy.config import RssBuddyConfig  # Import config class
from rss_buddy.main import run_feed_processing  # Import the refactored function


# Helper class to mimic feedparser.FeedParserDict structure
class MockFeedParserDict:
    """A minimal mock object mimicking feedparser.FeedParserDict structure."""

    def __init__(self, data):
        """Initialize the mock with feed and entry data."""
        self.bozo = 0
        self.feed = data.get("feed", {})
        self.entries = data.get("entries", [])
        self.bozo_exception = None


class TestFeedProcessingToState(unittest.TestCase):
    """Integration tests verifying feed processing saves state correctly."""

    def setUp(self):
        """Set up mocks, temp directory, and test config."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name

        self.mock_feed_url = "http://mock.feed.com/rss"
        self.days_lookback = 7

        # Calculate recent dates relative to now
        now = datetime.now(timezone.utc)
        date_format = "%a, %d %b %Y %H:%M:%S GMT"
        recent_date_1 = (now - timedelta(days=1)).strftime(date_format)
        recent_date_2 = (now - timedelta(days=2)).strftime(date_format)
        # Make old date clearly outside lookback
        old_date = (now - timedelta(days=self.days_lookback + 5)).strftime(date_format)

        # Mock feed data mimicking feedparser.parse output
        self.mock_feed_parsed_data = {
            "feed": {"title": "Mock Feed Title"},
            "entries": [
                {
                    "title": "Entry 1 Title",
                    "link": "http://example.com/entry1",
                    "guid": "http://example.com/entry1-guid",
                    "guidislink": False,
                    "published": recent_date_1,
                    "summary": "Summary for entry 1.",
                },
                {
                    "title": "Entry 2 Title",
                    "link": "http://example.com/entry2",
                    "published": recent_date_2,
                    "summary": "Summary for entry 2.",
                    # Missing guid, link will be used as ID
                },
                {
                    "title": "Entry 3 Old",
                    "link": "http://example.com/entry3-old",
                    "guid": "http://example.com/entry3-old",
                    "published": old_date,
                    "summary": "Summary for old entry 3.",
                },
            ],
        }

        # Define mock AI responses
        self.mock_ai_eval_responses = {
            ("Entry 1 Title", "Summary for entry 1."): "FULL",
            ("Entry 2 Title", "Summary for entry 2."): "SUMMARY",
        }

        # Create Test Config Object
        self.test_config = RssBuddyConfig(
            openai_api_key="mock-api-key",
            rss_feeds=[self.mock_feed_url],
            user_preference_criteria="test criteria",
            days_lookback=self.days_lookback,
            ai_model="mock-ai-model",
            summary_max_tokens=150,
            output_dir=self.output_dir,
        )

        # Mock feedparser.parse
        self.mock_parse_patcher = patch(
            "feedparser.parse", return_value=MockFeedParserDict(self.mock_feed_parsed_data)
        )
        self.mock_parse = self.mock_parse_patcher.start()

        # Instantiate MockAIInterface
        self.mock_ai_instance = MockAIInterface(evaluation_responses=self.mock_ai_eval_responses)

        # Patch AIInterface class within the main module's scope
        # Note: Patch target depends on where AIInterface is imported/used in run_feed_processing
        self.mock_ai_class_patcher = patch(
            "rss_buddy.main.AIInterface",  # Patch where it's used
            return_value=self.mock_ai_instance,
        )
        self.mock_ai_class = self.mock_ai_class_patcher.start()

        # We will use the real StateManager and RobustDateParser here

    def tearDown(self):
        """Clean up temporary directory and stop mocks."""
        self.temp_dir.cleanup()
        self.mock_parse_patcher.stop()
        self.mock_ai_class_patcher.stop()

    def test_feed_processing_saves_state(self):
        """Verify run_feed_processing processes mock feed and saves expected state."""
        # Run the processing function with the test config
        run_feed_processing(self.test_config)

        # Verify state file was created
        state_file_path = os.path.join(self.output_dir, "processed_state.json")
        self.assertTrue(os.path.exists(state_file_path), "processed_state.json should be created")

        # Load and validate state file content
        with open(state_file_path, "r") as f:
            state_data = json.load(f)

        # Check basic structure
        self.assertIn("feeds", state_data)
        self.assertIn(self.mock_feed_url, state_data["feeds"])
        self.assertIn("entry_data", state_data["feeds"][self.mock_feed_url])

        feed_entry_data = state_data["feeds"][self.mock_feed_url]["entry_data"]

        # Verify only recent entries are processed and saved
        self.assertEqual(len(feed_entry_data), 2, "Only 2 recent entries should be saved")

        # Expected entry IDs (generated based on feedprocessor logic)
        entry1_id = self.mock_feed_parsed_data["entries"][0]["guid"]
        entry2_id = self.mock_feed_parsed_data["entries"][1]["link"]  # Fallback to link
        entry3_id = self.mock_feed_parsed_data["entries"][2]["guid"]
        self.assertNotIn(entry3_id, feed_entry_data, "Old Entry 3 should not be in state")

        # Check Entry 1 details (processed)
        self.assertIn(entry1_id, feed_entry_data)
        entry1_state = feed_entry_data[entry1_id]
        self.assertEqual(entry1_state.get("title"), "Entry 1 Title")
        self.assertEqual(entry1_state.get("status"), "processed")
        self.assertIn("processed_at", entry1_state)
        self.assertEqual(
            entry1_state.get("date"), self.mock_feed_parsed_data["entries"][0]["published"]
        )

        # Check Entry 2 details (digest)
        self.assertIn(entry2_id, feed_entry_data)
        entry2_state = feed_entry_data[entry2_id]
        self.assertEqual(entry2_state.get("title"), "Entry 2 Title")
        self.assertEqual(entry2_state.get("status"), "digest")
        self.assertIn("processed_at", entry2_state)
        self.assertEqual(
            entry2_state.get("date"), self.mock_feed_parsed_data["entries"][1]["published"]
        )

        # Verify mocks were called
        self.mock_parse.assert_called_once_with(self.mock_feed_url)

        # Verify AI evaluation happened (implicitly tested by correct status in state)
        # If explicit checks are needed, MockAIInterface needs call tracking.


if __name__ == "__main__":
    unittest.main()
