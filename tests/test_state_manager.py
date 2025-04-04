"""Unit tests for the state manager component."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# Add path to allow importing package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rss_buddy.state_manager import StateManager

# Import DateParser
from rss_buddy.utils.date_parser import RobustDateParser


class TestStateManager(unittest.TestCase):
    """Test the StateManager class."""

    def setUp(self):
        """Set up a temporary directory for state files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        self.state_file = os.path.join(self.output_dir, "processed_state.json")
        # Instantiate the real parser for use in tests
        self.date_parser = RobustDateParser()

    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    def test_init_with_no_state_file(self):
        """Test initializing the state manager with no existing state file."""
        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)

        # Save state to create the file
        state_manager.save_state()

        # Check that the state file exists now
        self.assertTrue(os.path.exists(self.state_file))

        # Check initial state structure
        expected_keys = ["feeds", "last_updated"]
        for key in expected_keys:
            self.assertIn(key, state_manager.state)

        # Feeds should be an empty dict initially
        self.assertEqual(state_manager.state["feeds"], {})

    def test_get_entry_status(self):
        """Test checking an entry's status."""
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        entry_data = {"id": entry_id, "date": "2024-01-01T12:00:00Z", "title": "Test"}

        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)

        # Status should be None initially
        self.assertIsNone(state_manager.get_entry_status(feed_url, entry_id))

        # Add the entry with 'processed' status
        state_manager.add_processed_entry(feed_url, entry_id, "processed", entry_data)
        self.assertEqual(state_manager.get_entry_status(feed_url, entry_id), "processed")

        # Add/update the entry with 'digest' status
        state_manager.add_processed_entry(feed_url, entry_id, "digest", entry_data)
        self.assertEqual(state_manager.get_entry_status(feed_url, entry_id), "digest")

    def test_add_processed_entry(self):
        """Test adding an entry with status and data."""
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        entry_data = {
            "id": entry_id,
            "date": "2024-01-01T12:00:00Z",
            "title": "Test Title",
            "link": "http://link",
            "summary": "Test Summary",
        }
        status = "processed"

        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)
        state_manager.add_processed_entry(feed_url, entry_id, status, entry_data)

        # Check that the entry was added correctly
        feed_state = state_manager.state["feeds"][feed_url]
        self.assertIn(entry_id, feed_state["entry_data"])
        stored_data = feed_state["entry_data"][entry_id]
        self.assertEqual(stored_data["status"], status)
        self.assertEqual(stored_data["title"], entry_data["title"])
        self.assertEqual(stored_data["date"], entry_data["date"])
        self.assertIn("processed_at", stored_data)

    def test_save_state_with_cleanup(self):
        """Test saving the state to a file includes cleanup."""
        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)
        feed_url = "https://example.com/feed.xml"
        days_lookback = 7

        now = datetime.now(timezone.utc)
        recent_entry_id = "recent_entry"
        recent_entry_data = {"id": recent_entry_id, "date": now.isoformat(), "title": "Recent"}
        old_entry_id = "old_entry"
        old_entry_data = {
            "id": old_entry_id,
            "date": (now - timedelta(days=days_lookback + 1)).isoformat(),  # Ensure it's older
            "title": "Old",
        }

        # Add entries
        state_manager.add_processed_entry(feed_url, recent_entry_id, "processed", recent_entry_data)
        state_manager.add_processed_entry(feed_url, old_entry_id, "digest", old_entry_data)

        # Save the state with cleanup enabled
        state_manager.save_state(days_lookback=days_lookback)

        # Reload the state from file
        # Inject parser for the reloaded instance too
        reloaded_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)
        saved_state = reloaded_manager.state

        # Check that only the recent entry remains
        feed_entry_data = saved_state["feeds"][feed_url]["entry_data"]
        self.assertIn(recent_entry_id, feed_entry_data)
        self.assertNotIn(old_entry_id, feed_entry_data)

    def test_get_items_in_lookback(self):
        """Test retrieving items within the lookback period."""
        feed_url = "https://example.com/feed.xml"
        days_lookback = 7

        now = datetime.now(timezone.utc)
        entry1_data = {
            "id": "e1",
            "date": now.isoformat(),
            "title": "Recent 1",
            "status": "processed",
        }
        entry2_data = {
            "id": "e2",
            "date": (now - timedelta(days=days_lookback // 2)).isoformat(),
            "title": "Recent 2",
            "status": "digest",
        }
        entry3_data = {
            "id": "e3",
            "date": (now - timedelta(days=days_lookback + 1)).isoformat(),  # Ensure older
            "title": "Old",
            "status": "processed",
        }
        entry4_data = {
            "id": "e4",
            "date": None,
            "title": "No Date",
            "status": "processed",
        }  # No date

        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)
        state_manager.add_processed_entry(feed_url, "e1", "processed", entry1_data)
        state_manager.add_processed_entry(feed_url, "e2", "digest", entry2_data)
        state_manager.add_processed_entry(feed_url, "e3", "processed", entry3_data)
        state_manager.add_processed_entry(feed_url, "e4", "processed", entry4_data)

        # Get items within lookback
        items = state_manager.get_items_in_lookback(feed_url, days_lookback)

        # Check results (e1, e2, e4 should be included)
        self.assertEqual(len(items), 3)
        item_ids = {item["id"] for item in items}
        self.assertIn("e1", item_ids)
        self.assertIn("e2", item_ids)
        self.assertNotIn("e3", item_ids)
        self.assertIn("e4", item_ids)  # Items with no date are kept

    # --- Test State File Loading Error Handling ---

    def test_load_state_invalid_json(self):
        """Test loading a state file with invalid JSON content."""
        # Write invalid JSON to the state file
        with open(self.state_file, "w") as f:
            f.write("this is not json{")

        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)

        # Check that the state is the default empty state
        self.assertTrue(hasattr(state_manager, "state"))
        self.assertIsInstance(state_manager.state, dict)
        self.assertEqual(state_manager.state.get("feeds"), {})
        self.assertIn("last_updated", state_manager.state)

    def test_load_state_missing_feeds_key(self):
        """Test loading a state file that is valid JSON but missing the 'feeds' key."""
        # Write state file without the 'feeds' key
        invalid_state = {"last_updated": datetime.now(timezone.utc).isoformat()}
        with open(self.state_file, "w") as f:
            json.dump(invalid_state, f)

        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)

        # Check state defaults correctly
        self.assertTrue(hasattr(state_manager, "state"))
        self.assertIsInstance(state_manager.state, dict)
        self.assertEqual(state_manager.state.get("feeds"), {})
        self.assertIn("last_updated", state_manager.state)

    def test_load_state_wrong_feeds_type(self):
        """Test loading state file where 'feeds' key is not a dictionary."""
        # Write state file with 'feeds' as a list
        invalid_state = {"feeds": ["url1", "url2"], "last_updated": "time"}
        with open(self.state_file, "w") as f:
            json.dump(invalid_state, f)

        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)

        # Check state defaults correctly
        self.assertTrue(hasattr(state_manager, "state"))
        self.assertIsInstance(state_manager.state, dict)
        self.assertEqual(state_manager.state.get("feeds"), {})
        self.assertIn("last_updated", state_manager.state)

    def test_get_feed_title(self):
        """Test getting the feed title."""
        feed_url = "https://example.com/feed.xml"
        feed_title = "My Test Feed"
        # Inject parser
        state_manager = StateManager(date_parser=self.date_parser, output_dir=self.output_dir)

        # Title should be None initially
        self.assertIsNone(state_manager.get_feed_title(feed_url))

        # Add an entry with the title
        state_manager.add_processed_entry(
            feed_url,
            "id1",
            "processed",
            {"id": "id1", "date": "date"},
            feed_title=feed_title,
        )
        self.assertEqual(state_manager.get_feed_title(feed_url), feed_title)

        # Add another entry without title - title should persist
        state_manager.add_processed_entry(feed_url, "id2", "digest", {"id": "id2", "date": "date"})
        self.assertEqual(state_manager.get_feed_title(feed_url), feed_title)


if __name__ == "__main__":
    unittest.main()
