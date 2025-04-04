"""Unit tests for the feed processor component."""

import datetime
import hashlib
import os
import sys
import unittest
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

# Add path to allow importing package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rss_buddy.feed_processor import FeedProcessor
from src.rss_buddy.interfaces.protocols import AIInterfaceProtocol, StateManagerProtocol
from src.rss_buddy.utils.date_parser import RobustDateParser


class TimeoutError(Exception):
    """Exception raised for timeouts in tests."""

    pass


def timeout_handler(signum, frame):
    """Signal handler for timeouts in tests."""
    raise TimeoutError("Test timed out")


class TestFeedProcessor(unittest.TestCase):
    """Test the FeedProcessor class."""

    def setUp(self):
        """Set up test environment."""
        # Use Protocols for mocks
        self.state_manager = MagicMock(spec=StateManagerProtocol)
        self.ai_interface = MagicMock(spec=AIInterfaceProtocol)
        # Use the real RobustDateParser for testing is_recent
        self.date_parser = RobustDateParser()
        self.test_feed_url = "https://example.com/feed.xml"
        self.days_lookback = 7
        self.processor = FeedProcessor(
            state_manager=self.state_manager,
            ai_interface=self.ai_interface,
            date_parser=self.date_parser,  # Inject date parser
            days_lookback=self.days_lookback,
            user_preference_criteria="Technology articles about Python",
            summary_max_tokens=150,
        )

        # Simplified test entry, dates handled in specific tests
        now = datetime.datetime.now(timezone.utc)
        self.recent_date_str = (now - timedelta(days=1)).isoformat()
        self.old_date_str = (now - timedelta(days=self.days_lookback + 5)).isoformat()

        self.test_entry_base = {
            "title": "Test Article",
            "link": "https://example.com/test-article",
            "summary": "Test summary",
            "guid": "https://example.com/test-guid",
            "guidislink": False,
            # published date added per test
        }

    def test_generate_entry_id(self):
        """Test the generate_entry_id method."""
        # Test with non-link guid
        entry_guid = {"guid": "test-guid", "guidislink": False, "link": "link", "title": "T"}
        self.assertEqual(self.processor.generate_entry_id(entry_guid), "test-guid")

        # Test with link (when guidislink is True or guid is missing)
        entry_link = {"guid": "link", "guidislink": True, "link": "link", "title": "T"}
        self.assertEqual(self.processor.generate_entry_id(entry_link), "link")
        entry_link_no_guid = {"link": "link", "title": "T"}
        self.assertEqual(self.processor.generate_entry_id(entry_link_no_guid), "link")

        # Test with guid only (even if guidislink is True)
        entry_guid_only = {"guid": "guid-link", "guidislink": True, "title": "T"}
        self.assertEqual(self.processor.generate_entry_id(entry_guid_only), "guid-link")

        # Test with title and summary only (fallback)
        entry_fallback = {"title": "Test Title", "summary": "Test Summary"}
        expected_hash = hashlib.md5(b"Test TitleTest Summary").hexdigest()
        self.assertEqual(self.processor.generate_entry_id(entry_fallback), expected_hash)

    def test_fetch_rss_feed(self):
        """Test the fetch_rss_feed method."""
        with patch("feedparser.parse") as mock_parse:
            mock_result = MagicMock()
            mock_result.bozo = 0
            mock_parse.return_value = mock_result

            result = self.processor.fetch_rss_feed("https://example.com/feed.xml")

            self.assertEqual(result, mock_result)
            mock_parse.assert_called_once_with("https://example.com/feed.xml")

    def test_fetch_rss_feed_error(self):
        """Test error handling in fetch_rss_feed method."""
        with patch("feedparser.parse") as mock_parse:
            mock_parse.side_effect = Exception("Feed fetch error")

            result = self.processor.fetch_rss_feed("https://example.com/feed.xml")

            self.assertIsNone(result)

    def test_is_recent_true(self):
        """Test is_recent returns True for a recent date."""
        self.assertTrue(self.processor.is_recent(self.recent_date_str))

    def test_is_recent_false_old(self):
        """Test is_recent returns False for an old date."""
        self.assertFalse(self.processor.is_recent(self.old_date_str))

    def test_is_recent_false_unparseable(self):
        """Test is_recent returns False for an unparseable date string."""
        self.assertFalse(self.processor.is_recent("not a date"))

    def test_is_recent_false_none(self):
        """Test is_recent returns False for None input."""
        self.assertFalse(self.processor.is_recent(None))

    def test_process_feed_new_entry(self):
        """Test processing a feed with a new entry."""
        # Mock feed data
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")
        entry = {**self.test_entry_base, "published": self.recent_date_str}
        mock_feed.entries = [entry]

        # Mock dependencies
        with (
            patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed),
        ):
            # Mock state manager: entry not processed yet
            self.state_manager.get_entry_status.return_value = None
            # Mock AI: classify as 'processed'
            self.ai_interface.evaluate_article_preference.return_value = "FULL"

            # Process the feed
            new_count, skipped_count = self.processor.process_feed(self.test_feed_url)

            # Assertions
            self.assertEqual(new_count, 1)
            self.assertEqual(skipped_count, 0)
            # Assert that get_entry_status was called with the correct GUID
            self.state_manager.get_entry_status.assert_called_once_with(
                self.test_feed_url, entry["guid"]
            )
            self.ai_interface.evaluate_article_preference.assert_called_once()
            # Check that add_processed_entry was called with correct status and GUID
            self.state_manager.add_processed_entry.assert_called_once()
            call_args = self.state_manager.add_processed_entry.call_args[0]
            self.assertEqual(call_args[0], self.test_feed_url)
            self.assertEqual(call_args[1], entry["guid"])
            self.assertEqual(call_args[2], "processed")  # Status should be 'processed'
            self.assertEqual(call_args[3]["title"], entry["title"])

    def test_process_feed_already_processed_entry(self):
        """Test processing a feed where the entry is already processed."""
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")
        entry = {**self.test_entry_base, "published": self.recent_date_str}
        mock_feed.entries = [entry]

        with (
            patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed),
        ):
            # Mock state manager: entry already processed with status 'digest'
            self.state_manager.get_entry_status.return_value = "digest"

            # Process the feed
            new_count, skipped_count = self.processor.process_feed(self.test_feed_url)

            # Assertions
            self.assertEqual(new_count, 0)
            self.assertEqual(skipped_count, 1)
            # Assert that get_entry_status was called with the correct GUID
            self.state_manager.get_entry_status.assert_called_once_with(
                self.test_feed_url, entry["guid"]
            )
            # AI and add_processed_entry should not be called
            self.ai_interface.evaluate_article_preference.assert_not_called()
            self.state_manager.add_processed_entry.assert_not_called()

    def test_process_feed_old_entry(self):
        """Test processing a feed with an old entry."""
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")
        entry = {**self.test_entry_base, "published": self.old_date_str}  # Use old date
        mock_feed.entries = [entry]

        with (
            patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed),
        ):  # Mock as not recent
            # Process the feed
            new_count, skipped_count = self.processor.process_feed(self.test_feed_url)

            # Assertions
            self.assertEqual(new_count, 0)
            self.assertEqual(skipped_count, 0)  # Not skipped because it wasn't recent
            # Should not check status, call AI, or add entry
            self.state_manager.get_entry_status.assert_not_called()
            self.ai_interface.evaluate_article_preference.assert_not_called()
            self.state_manager.add_processed_entry.assert_not_called()

    def test_process_feeds_saves_state(self):
        """Test that process_feeds saves state after processing all feeds."""
        feed_urls = ["url1", "url2"]

        # Mock process_feed to return some dummy counts
        with patch.object(self.processor, "process_feed", return_value=(1, 0)):
            self.processor.process_feeds(feed_urls)

            # Assert process_feed was called for each URL
            self.assertEqual(self.processor.process_feed.call_count, len(feed_urls))
            # Assert save_state was called once with the correct lookback
            self.state_manager.save_state.assert_called_once_with(days_lookback=self.days_lookback)


if __name__ == "__main__":
    unittest.main()
