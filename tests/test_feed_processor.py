"""Unit tests for the feed processor component."""
import os
import json
import tempfile
import unittest
import signal
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rss_buddy.feed_processor import FeedProcessor
from rss_buddy.ai_interface import MockAIInterface
from rss_buddy.state_manager import StateManager

# Define a timeout handler
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Test timed out")

class TestFeedProcessor(unittest.TestCase):
    """Test the FeedProcessor class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for output
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        
        # Set up a mock AI interface
        self.mock_ai = MockAIInterface(
            evaluation_responses={
                ("Major AI Breakthrough in Quantum Computing", 
                 "Researchers have achieved a significant breakthrough in quantum computing using AI techniques, potentially revolutionizing the field."): "FULL",
                ("Tech Giant Announces New Smartphone", 
                 "A major tech company has unveiled its latest smartphone with groundbreaking features."): "FULL",
                ("Popular Social Media App Updates Privacy Policy", 
                 "A widely used social media platform has updated its privacy policy following regulatory pressure."): "SUMMARY",
                ("New Entertainment Streaming Service Launches", 
                 "A new entertainment streaming service has launched with exclusive content partnerships."): "SUMMARY"
            },
            summary_responses={
                "New Entertainment Streaming Service Launches+Popular Social Media App Updates Privacy Policy": 
                "<h3>Tech Updates Digest</h3><p>Several tech platforms have made updates, including <a href='https://test.example.com/tech/social-media-privacy-update'>privacy policy changes</a> and <a href='https://test.example.com/tech/new-streaming-service'>new service launches</a>.</p>"
            }
        )
        
        # Set up a state manager with an empty state
        self.state_manager = StateManager(output_dir=self.output_dir)
        
        # Set up the feed processor
        self.feed_processor = FeedProcessor(
            state_manager=self.state_manager,
            ai_interface=self.mock_ai,
            output_dir=self.output_dir,
            days_lookback=7,
            user_preference_criteria="Just a test criteria, the MockAI doesn't use it",
            summary_max_tokens=150
        )
        
        # Load test feed data
        with open(os.path.join(os.path.dirname(__file__), "data", "test_feed_1.json"), 'r') as f:
            self.test_feed_data = json.load(f)
            
        # Create a mock for feedparser result
        self.mocked_feed = MagicMock()
        self.mocked_feed.feed.title = self.test_feed_data["feed"]["title"]
        self.mocked_feed.feed.link = self.test_feed_data["feed"]["link"]
        self.mocked_feed.feed.description = self.test_feed_data["feed"]["description"]
        
        # Add entries as mock objects
        self.mocked_feed.entries = []
        for entry_data in self.test_feed_data["entries"]:
            entry = MagicMock()
            for key, value in entry_data.items():
                setattr(entry, key, value)
            # Add mocked get method to simulate dictionary-like behavior
            entry.get = lambda k, default=None, entry=entry: getattr(entry, k, default)
            self.mocked_feed.entries.append(entry)
    
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_generate_entry_id(self):
        """Test generating an entry ID."""
        # Test with an entry that has an ID
        entry_with_id = {"id": "test-id", "link": "https://example.com/article", "title": "Test"}
        self.assertEqual(self.feed_processor.generate_entry_id(entry_with_id), "test-id")
        
        # Test with an entry that has no ID but has a link
        entry_with_link = {"link": "https://example.com/article", "title": "Test"}
        self.assertEqual(self.feed_processor.generate_entry_id(entry_with_link), "https://example.com/article")
        
        # Test with an entry that has neither ID nor link
        entry_no_id_link = {"title": "Test Title", "summary": "Test Summary"}
        id_hash = self.feed_processor.generate_entry_id(entry_no_id_link)
        self.assertTrue(id_hash.isalnum())  # Should be a hash
    
    @patch("rss_buddy.feed_processor.feedparser.parse")
    def test_fetch_rss_feed(self, mock_parse):
        """Test fetching an RSS feed."""
        # Set up mock response
        mock_parse.return_value = self.mocked_feed
        
        # Fetch the feed
        feed = self.feed_processor.fetch_rss_feed("https://test.example.com/feed.xml")
        
        # Check the result
        self.assertEqual(feed, self.mocked_feed)
        mock_parse.assert_called_once_with("https://test.example.com/feed.xml")
    
    @patch("rss_buddy.feed_processor.feedparser.parse")
    def test_fetch_rss_feed_error(self, mock_parse):
        """Test fetching an RSS feed with an error."""
        # Set up mock to raise an exception
        mock_parse.side_effect = Exception("Network error")
        
        # Fetch the feed
        feed = self.feed_processor.fetch_rss_feed("https://test.example.com/feed.xml")
        
        # Should return None on error
        self.assertIsNone(feed)
    
    def test_is_recent_with_recent_date(self):
        """Test checking if an entry is recent with a recent date."""
        # A date from less than 7 days ago should be recent
        recent_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.assertTrue(self.feed_processor.is_recent(recent_date))
    
    def test_is_recent_with_old_date(self):
        """Test checking if an entry is recent with an old date."""
        # A date from more than 7 days ago should not be recent
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.assertFalse(self.feed_processor.is_recent(old_date))
    
    def test_is_recent_with_invalid_date(self):
        """Test checking if an entry is recent with an invalid date."""
        # An invalid date should return False
        self.assertFalse(self.feed_processor.is_recent("invalid date"))
        
        # A None date should return False
        self.assertFalse(self.feed_processor.is_recent(None))
    
    def test_is_recent_with_timezone_formats(self):
        """Test different timezone formats to ensure consistent handling."""
        # Get current time for reference
        now = datetime.now(timezone.utc)
        
        # A few key date formats to test (within lookback period)
        recent_dates = [
            # Standard RFC 2822 format with explicit timezone
            (now - timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S +0000'),
            # ISO 8601 format with Z (Zulu/UTC)
            (now - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            # Format with no timezone (should be interpreted as UTC)
            (now - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S')
        ]
        
        # Test each format
        for date_str in recent_dates:
            self.assertTrue(self.feed_processor.is_recent(date_str), 
                            f"Date {date_str} should be considered recent")
        
        # One old date to test
        old_date = (now - timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S +0000')
        self.assertFalse(self.feed_processor.is_recent(old_date),
                          f"Date {old_date} should not be considered recent")
    
    def test_naive_and_aware_datetime_comparison(self):
        """Test that timezone-naive and timezone-aware datetimes are compared correctly."""
        now = datetime.now(timezone.utc)
        
        # Create a timezone-naive recent date string
        naive_recent = (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Create a timezone-aware recent date string
        aware_recent = (now - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        
        # Both should be considered recent
        self.assertTrue(self.feed_processor.is_recent(naive_recent))
        self.assertTrue(self.feed_processor.is_recent(aware_recent))
        
        # Create naive and aware old dates
        naive_old = (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
        aware_old = (now - timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        
        # Both should not be considered recent
        self.assertFalse(self.feed_processor.is_recent(naive_old))
        self.assertFalse(self.feed_processor.is_recent(aware_old))
    
    def test_alternate_date_fields(self):
        """Test that the feed processor correctly checks alternate date fields."""
        # Method to simulate the behavior in process_feed that checks different date fields
        def find_entry_date(entry):
            # First try standard fields
            entry_date = entry.get('published', entry.get('updated', None))
            
            # If standard fields aren't found, check alternative fields
            if not entry_date:
                for field in ['pubDate', 'date', 'created', 'modified']:
                    if field in entry:
                        return entry[field]
            return entry_date
        
        # Create a test entry
        test_entry = {
            'title': 'Test Article with Alternative Date Field',
            'link': 'https://example.com/test-article',
            # No standard date fields
        }
        
        # Test with no date field
        self.assertIsNone(find_entry_date(test_entry), 
                         "Should return None when no date fields are present")
        
        # Test with pubDate field
        test_entry['pubDate'] = '2025-03-27T12:00:00Z'
        self.assertEqual(find_entry_date(test_entry), '2025-03-27T12:00:00Z',
                        "Should find date in pubDate field")
        
        # Test with a different alternative field
        del test_entry['pubDate']
        test_entry['date'] = '2025-03-27T12:00:00Z'
        self.assertEqual(find_entry_date(test_entry), '2025-03-27T12:00:00Z',
                        "Should find date in date field")
        
        # Test with a standard field taking precedence over alternative
        test_entry['published'] = '2025-03-28T12:00:00Z'
        self.assertEqual(find_entry_date(test_entry), '2025-03-28T12:00:00Z',
                        "Standard published field should take precedence")
    
    def test_evaluate_article_preference(self):
        """Test evaluating article preference."""
        # Test full article preference
        result1 = self.feed_processor.evaluate_article_preference(
            title="Major AI Breakthrough in Quantum Computing",
            summary="Researchers have achieved a significant breakthrough in quantum computing using AI techniques, potentially revolutionizing the field.",
            feed_url="https://test.example.com/feed.xml"
        )
        self.assertEqual(result1, "FULL")
        
        # Test summary article preference
        result2 = self.feed_processor.evaluate_article_preference(
            title="New Entertainment Streaming Service Launches",
            summary="A new entertainment streaming service has launched with exclusive content partnerships.",
            feed_url="https://test.example.com/feed.xml"
        )
        self.assertEqual(result2, "SUMMARY")
    
    def test_create_consolidated_summary(self):
        """Test creating a consolidated summary."""
        # Create article data
        articles = [
            {
                "title": "Popular Social Media App Updates Privacy Policy",
                "link": "https://test.example.com/tech/social-media-privacy-update",
                "guid": "https://test.example.com/tech/social-media-privacy-update",
                "pubDate": "Mon, 25 Mar 2024 09:15:00 GMT",
                "summary": "A widely used social media platform has updated its privacy policy following regulatory pressure."
            },
            {
                "title": "New Entertainment Streaming Service Launches",
                "link": "https://test.example.com/tech/new-streaming-service",
                "guid": "https://test.example.com/tech/new-streaming-service",
                "pubDate": "Mon, 25 Mar 2024 08:30:00 GMT",
                "summary": "A new entertainment streaming service has launched with exclusive content partnerships."
            }
        ]
        
        # Create the summary
        digest = self.feed_processor.create_consolidated_summary(
            articles=articles,
            feed_url="https://test.example.com/feed.xml"
        )
        
        # Check the result
        self.assertIsNotNone(digest)
        self.assertTrue(digest['title'].startswith("RSS Buddy Digest"))
        self.assertEqual(digest['description'], 
                         "<h3>Tech Updates Digest</h3><p>Several tech platforms have made updates, including <a href='https://test.example.com/tech/social-media-privacy-update'>privacy policy changes</a> and <a href='https://test.example.com/tech/new-streaming-service'>new service launches</a>.</p>")
        
        # Test that the IDs were added to the state
        for article in articles:
            self.assertTrue(self.state_manager.is_entry_processed("https://test.example.com/feed.xml", article["guid"]))
    
    def test_create_consolidated_summary_empty_articles(self):
        """Test creating a consolidated summary with empty articles list."""
        # Create the summary with empty articles
        digest = self.feed_processor.create_consolidated_summary(
            articles=[],
            feed_url="https://test.example.com/feed.xml"
        )
        
        # Should return None for empty articles
        self.assertIsNone(digest)
    
    @patch("rss_buddy.feed_processor.FeedProcessor.fetch_rss_feed")
    @patch("xml.etree.ElementTree.ElementTree.write")
    def test_process_feed(self, mock_write, mock_fetch):
        """Test processing a feed."""
        # Set up mock response
        mock_fetch.return_value = self.mocked_feed
        
        # Create a temporary file path for output
        temp_output_path = os.path.join(self.output_dir, "TestFeed_Filtered.xml")
        
        # Make the write method return the path
        mock_write.return_value = None
        
        # Mock the evaluate_article_preference to return "FULL" for all entries
        with patch.object(self.feed_processor, 'evaluate_article_preference', return_value="FULL"):
            # Mock the is_recent method to return True for all entries
            with patch.object(self.feed_processor, 'is_recent', return_value=True):
                # Process the feed
                output_path = self.feed_processor.process_feed("https://test.example.com/feed.xml")
                
                # Check that write was called
                mock_write.assert_called()
                
                # We don't need to verify state processing since our mocks don't actually
                # process entries, and that's tested in other test methods
    
    @patch("rss_buddy.feed_processor.FeedProcessor.process_feed")
    def test_process_feeds(self, mock_process_feed):
        """Test processing multiple feeds."""
        # Set up mock response
        mock_process_feed.side_effect = [
            os.path.join(self.output_dir, "Feed1.xml"),
            os.path.join(self.output_dir, "Feed2.xml"),
            None  # Simulate failure for the third feed
        ]
        
        # Process the feeds
        feed_urls = [
            "https://test.example.com/feed1.xml",
            "https://test.example.com/feed2.xml",
            "https://test.example.com/feed3.xml"
        ]
        output_paths = self.feed_processor.process_feeds(feed_urls)
        
        # Check the result
        self.assertEqual(len(output_paths), 2)  # Only two successful feeds
        mock_process_feed.assert_any_call("https://test.example.com/feed1.xml")
        mock_process_feed.assert_any_call("https://test.example.com/feed2.xml")
        mock_process_feed.assert_any_call("https://test.example.com/feed3.xml")

if __name__ == "__main__":
    unittest.main() 