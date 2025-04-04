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

from rss_buddy.main import main as rss_buddy_main  # Rename to avoid collision


# Helper class to mimic feedparser.FeedParserDict structure
class MockFeedParserDict:
    """A minimal mock object mimicking feedparser.FeedParserDict structure."""

    def __init__(self, data):
        """Initialize the mock with feed and entry data."""
        self.bozo = 0  # Assume success by default for this test
        self.feed = data.get("feed", {})
        self.entries = data.get("entries", [])
        # Add bozo_exception if needed for testing error cases
        self.bozo_exception = None


class TestFeedProcessingToState(unittest.TestCase):
    """Integration tests verifying feed processing saves state correctly."""

    def setUp(self):
        """Set up mocks, temp directory, and mock data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name

        self.mock_feed_url = "http://mock.feed.com/rss"

        # Calculate recent dates relative to now
        now = datetime.now(timezone.utc)
        date_format = "%a, %d %b %Y %H:%M:%S GMT"  # Example: Tue, 02 Apr 2024 10:00:00 GMT
        recent_date_1 = (now - timedelta(days=1)).strftime(date_format)
        recent_date_2 = (now - timedelta(days=2)).strftime(date_format)
        old_date = (now - timedelta(days=30)).strftime(date_format)  # Clearly outside 7 days

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
                },
                {
                    "title": "Entry 3 Old",
                    "link": "http://example.com/entry3-old",
                    "guid": "http://example.com/entry3-old",
                    "published": old_date,
                    "summary": "Summary for old entry 3.",
                },
            ],
            "bozo": 0,  # Not used directly anymore, set in MockFeedParserDict
        }

        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "RSS_FEEDS": self.mock_feed_url,
                "OUTPUT_DIR": self.output_dir,
                "USER_PREFERENCE_CRITERIA": "test criteria",
                "DAYS_LOOKBACK": "7",
                "AI_MODEL": "mock-ai-model",
                "SUMMARY_MAX_TOKENS": "150",
                "OPENAI_API_KEY": "mock-api-key",
            },
            clear=True,  # Clear other env vars that might interfere
        )
        self.env_patcher.start()

        # Mock feedparser.parse, creating the mock object directly as the return value
        self.mock_parse_patcher = patch(
            "feedparser.parse", return_value=MockFeedParserDict(self.mock_feed_parsed_data)
        )
        self.mock_parse = self.mock_parse_patcher.start()

        # Mock AIInterface methods
        self.mock_ai_init_patcher = patch(
            "rss_buddy.ai_interface.AIInterface.__init__", return_value=None
        )
        self.mock_ai_init = self.mock_ai_init_patcher.start()

        def mock_evaluate_preference(*args, **kwargs):
            title = kwargs.get("title", "")
            if title == "Entry 1 Title":
                return "FULL"
            elif title == "Entry 2 Title":
                return "SUMMARY"
            return "SUMMARY"

        self.mock_ai_evaluate_patcher = patch(
            "rss_buddy.ai_interface.AIInterface.evaluate_article_preference",
            side_effect=mock_evaluate_preference,
        )
        self.mock_ai_evaluate = self.mock_ai_evaluate_patcher.start()

    def tearDown(self):
        """Clean up temporary directory and stop mocks."""
        self.temp_dir.cleanup()
        self.env_patcher.stop()
        self.mock_parse_patcher.stop()
        self.mock_ai_init_patcher.stop()
        self.mock_ai_evaluate_patcher.stop()

    def test_feed_processing_saves_state(self):
        """Verify main() processes mock feed and saves expected state."""
        # Run the main script function
        result_code = rss_buddy_main()

        # Assertions
        self.assertEqual(result_code, 0, "main() should return success code 0")

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

        # Verify only recent entries are processed
        self.assertEqual(len(feed_entry_data), 2, "Only 2 recent entries should be saved")

        # Expected entry IDs
        entry1_id = self.mock_feed_parsed_data["entries"][0]["guid"]
        entry2_id = self.mock_feed_parsed_data["entries"][1]["link"]
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
        self.assertEqual(self.mock_ai_evaluate.call_count, 2)
        self.mock_ai_evaluate.assert_any_call(
            title="Entry 1 Title",
            summary="Summary for entry 1.",
            criteria="test criteria",
            feed_url=self.mock_feed_url,
        )
        self.mock_ai_evaluate.assert_any_call(
            title="Entry 2 Title",
            summary="Summary for entry 2.",
            criteria="test criteria",
            feed_url=self.mock_feed_url,
        )


if __name__ == "__main__":
    unittest.main()
