"""Unit tests for the feed processor component."""

import datetime
import os
import sys
import unittest
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

# Add path to allow importing package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rss_buddy.feed_processor import FeedProcessor
from src.rss_buddy.state_manager import StateManager


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
        self.state_manager = MagicMock(spec=StateManager)
        self.ai_interface = MagicMock()
        self.output_dir = "/tmp/rss_buddy_test"
        self.test_feed_url = "https://example.com/feed.xml"
        self.processor = FeedProcessor(
            state_manager=self.state_manager,
            ai_interface=self.ai_interface,
            output_dir=self.output_dir,
            days_lookback=7,
            user_preference_criteria="Technology articles about Python",
            summary_max_tokens=150,
        )

        # Create test entry
        self.test_entry = {
            "title": "Test Article",
            "link": "https://example.com/test-article",
            "summary": "This is a test article summary",
            "published": "2023-12-01T12:00:00Z",
            "id": "https://example.com/test-article",
        }

    def tearDown(self):
        """Clean up after tests."""
        # Remove output directory if it exists
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))
            os.rmdir(self.output_dir)

    def test_generate_entry_id(self):
        """Test the generate_entry_id method."""
        # Test with entry ID
        entry = {"id": "test-id", "title": "Test", "link": "https://example.com"}
        self.assertEqual(self.processor.generate_entry_id(entry), "test-id")

        # Test with link only
        entry = {"title": "Test", "link": "https://example.com"}
        self.assertEqual(self.processor.generate_entry_id(entry), "https://example.com")

        # Test with title and summary only
        entry = {"title": "Test Title", "summary": "Test Summary"}
        self.assertTrue(len(self.processor.generate_entry_id(entry)) > 0)

    def test_fetch_rss_feed(self):
        """Test the fetch_rss_feed method."""
        with patch("feedparser.parse") as mock_parse:
            mock_result = MagicMock()
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

    def test_is_recent_with_recent_date(self):
        """Test is_recent method with a recent date."""
        # Create a date within the lookback period
        today = datetime.datetime.now(timezone.utc)
        recent_date = (today - timedelta(days=3)).isoformat()

        self.assertTrue(self.processor.is_recent(recent_date, 7))

    def test_is_recent_with_old_date(self):
        """Test is_recent method with an old date."""
        # Create a date outside the lookback period
        today = datetime.datetime.now(timezone.utc)
        old_date = (today - timedelta(days=10)).isoformat()

        self.assertFalse(self.processor.is_recent(old_date, 7))

    def test_is_recent_with_invalid_date(self):
        """Test is_recent method with an invalid date."""
        self.assertFalse(self.processor.is_recent("not a date"))

    def test_alternate_date_fields(self):
        """Test extraction of dates from various feed entry fields."""
        # Test with published date
        entry = {"published": "2023-12-01T12:00:00Z", "title": "Test"}
        expected_date = "2023-12-01T12:00:00+00:00"
        self.assertEqual(self.processor._parse_date(entry["published"]).isoformat(), expected_date)

        # Test with updated date
        entry = {"updated": "2023-12-01T12:00:00Z", "title": "Test"}
        self.assertEqual(self.processor._parse_date(entry["updated"]).isoformat(), expected_date)

        # Test with no date
        self.assertIsNone(self.processor._parse_date("not a date"))

    def test_evaluate_article_preference(self):
        """Test the article preference evaluation."""
        self.ai_interface.evaluate_article_preference.return_value = "FULL"

        result = self.processor.evaluate_article_preference(
            title="Test Title", summary="Test Summary", feed_url="https://example.com/feed.xml"
        )

        self.assertEqual(result, "FULL")
        self.ai_interface.evaluate_article_preference.assert_called_once()

    def test_create_consolidated_summary(self):
        """Test creation of a consolidated summary."""
        # Mock data
        summaries = [
            {
                "title": "Article 1",
                "summary": "Summary 1",
                "guid": "id1",
                "link": "https://example.com/1",
            },
            {
                "title": "Article 2",
                "summary": "Summary 2",
                "guid": "id2",
                "link": "https://example.com/2",
            },
        ]

        # Mock AI interface response
        self.ai_interface.generate_consolidated_summary.return_value = (
            "Combined summary of articles"
        )

        # Mock state manager
        self.state_manager.update_digest_state.return_value = ("digest-id", True)

        result = self.processor.create_consolidated_summary(
            articles=summaries, feed_url="https://example.com/feed.xml"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "RSS Buddy Digest: 2 Less Important Articles")
        self.assertEqual(result["description"], "Combined summary of articles")
        self.assertEqual(result["guid"], "digest-id")
        self.assertTrue(result["is_digest"])

    def test_create_consolidated_summary_empty_articles(self):
        """Test creation of a consolidated summary with empty articles list."""
        # Mock AI interface response
        self.ai_interface.generate_consolidated_summary.return_value = None

        result = self.processor.create_consolidated_summary(
            articles=[], feed_url="https://example.com/feed.xml"
        )

        self.assertIsNone(result)
        self.ai_interface.generate_consolidated_summary.assert_not_called()

    def test_process_feed(self):
        """Test processing a feed."""
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")
        mock_feed.entries = [self.test_entry]

        # Mock fetch_rss_feed to return our mock feed
        with patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed):
            # Mock is_recent to return True
            with patch.object(self.processor, "is_recent", return_value=True):
                # Mock is_entry_processed to return False
                self.state_manager.is_entry_processed.return_value = False

                # Mock evaluate_article_preference to return "FULL"
                with patch.object(
                    self.processor, "evaluate_article_preference", return_value="FULL"
                ):
                    # Mock ET.ElementTree to avoid actual file operations
                    with patch("xml.etree.ElementTree.ElementTree"):
                        result = self.processor.process_feed(self.test_feed_url)

                        # Verify that the result is the expected file path
                        expected_path = os.path.join(self.output_dir, "Test Feed.xml")
                        self.assertEqual(result, expected_path)

    def test_process_feed_with_lookback(self):
        """Test processing a feed with different lookback periods."""
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")

        # Create two entries, one recent and one old
        recent_entry = self.test_entry.copy()
        old_entry = self.test_entry.copy()
        old_entry["published"] = "2023-01-01T12:00:00Z"  # Old date

        mock_feed.entries = [recent_entry, old_entry]

        with patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed):
            # Define mock for is_recent to return proper values based on entry date
            def mock_is_recent(entry_date, days=None):
                return "recent" in entry_date or "2023-12" in entry_date

            with patch.object(self.processor, "is_recent", side_effect=mock_is_recent):
                # Mock is_entry_processed to return False for all entries
                self.state_manager.is_entry_processed.return_value = False

                # Mock evaluate_article_preference to return "FULL" for all entries
                with patch.object(
                    self.processor, "evaluate_article_preference", return_value="FULL"
                ):
                    # Mock ET.ElementTree to avoid actual file operations
                    with patch("xml.etree.ElementTree.ElementTree"):
                        # Process with default lookback (7 days)
                        self.processor.process_feed(self.test_feed_url)

                        # Should have processed only the recent entry
                        self.state_manager.add_processed_entry.assert_called_once()

    def test_process_feed_with_state_updates(self):
        """Test updating of state when processing a feed."""
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")
        mock_feed.entries = [self.test_entry]

        with patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed):
            # Mock is_recent to return True
            with patch.object(self.processor, "is_recent", return_value=True):
                # Mock is_entry_processed to return False
                self.state_manager.is_entry_processed.return_value = False

                # Mock evaluate_article_preference to return "FULL"
                with patch.object(
                    self.processor, "evaluate_article_preference", return_value="FULL"
                ):
                    # Mock ET.ElementTree to avoid actual file operations
                    with patch("xml.etree.ElementTree.ElementTree"):
                        self.processor.process_feed(self.test_feed_url)

                        # Verify that the state was updated
                        self.state_manager.add_processed_entry.assert_called_once()

                        # Reset mocks for second test
                        self.state_manager.reset_mock()

                        # Now test with a previously processed entry
                        self.state_manager.is_entry_processed.return_value = True

                        # Store entry data for retrieval
                        stored_data = {"preference": "FULL", "date": self.test_entry["published"]}
                        self.state_manager.get_entry_data.return_value = stored_data

                        self.processor.process_feed(self.test_feed_url)

                        # Verify that add_processed_entry was not called again
                        self.state_manager.add_processed_entry.assert_not_called()

    def test_process_feed_digest_updates(self):
        """Test updating of the digest when processing a feed."""
        # Create a mock feed
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.get = MagicMock(return_value="Test Feed")

        # Create two entries
        entry1 = self.test_entry.copy()
        entry2 = self.test_entry.copy()
        entry2["title"] = "Test Article 2"
        entry2["link"] = "https://example.com/test-article-2"

        mock_feed.entries = [entry1, entry2]

        # Define helper function to return a different preference based on the title
        def get_preference(title, summary, feed_url):
            if "2" in title:
                return "SUMMARY"
            return "FULL"

        # Mock the consolidated summary
        mock_summary = {
            "title": "RSS Buddy Digest",
            "link": "https://digest.example.com/123",
            "guid": "digest-123",
            "pubDate": "2023-12-01T12:00:00Z",
            "description": "Consolidated summary",
            "is_digest": True,
        }

        with patch.object(self.processor, "fetch_rss_feed", return_value=mock_feed):
            # Mock is_recent to return True for all entries
            with patch.object(self.processor, "is_recent", return_value=True):
                # Mock is_entry_processed to return False for all entries
                self.state_manager.is_entry_processed.return_value = False

                # Mock evaluate_article_preference to use our helper function
                with patch.object(
                    self.processor, "evaluate_article_preference", side_effect=get_preference
                ):
                    # Mock create_consolidated_summary to return our mock summary
                    with patch.object(
                        self.processor, "create_consolidated_summary", return_value=mock_summary
                    ):
                        # Mock ET.ElementTree to avoid actual file operations
                        with patch("xml.etree.ElementTree.ElementTree"):
                            self.processor.process_feed(self.test_feed_url)

                            # Verify that create_consolidated_summary was called
                            args, _ = self.processor.create_consolidated_summary.call_args
                            summary_articles = args[0]
                            self.assertEqual(len(summary_articles), 1)
                            self.assertEqual(summary_articles[0]["title"], "Test Article 2")


if __name__ == "__main__":
    unittest.main()
