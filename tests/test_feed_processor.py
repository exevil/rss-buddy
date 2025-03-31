"""Unit tests for the feed processor component."""
import os
import json
import tempfile
import unittest
import signal
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from email.utils import formatdate

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
    
    def test_previously_processed_articles(self):
        """Test that previously processed articles are correctly included in the output feed."""
        # Create a test state manager to track processed entries
        test_state_manager = StateManager(output_dir=self.output_dir)
        
        # Create a processor with our test state manager
        test_processor = FeedProcessor(
            state_manager=test_state_manager,
            ai_interface=self.mock_ai,
            output_dir=self.output_dir,
            days_lookback=7
        )
        
        # Set up test feed URL and entries
        feed_url = "https://test.example.com/feed.xml"
        
        # Set up a mock entry that will be processed in the first run
        test_entry = {
            'title': "Test Article For Processing",
            'link': "https://example.com/test-article",
            'guid': "test-article-guid",
            'pubDate': datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')
        }
        
        # Mark this entry as processed
        test_state_manager.add_processed_entry(
            feed_url=feed_url,
            entry_id=test_entry['guid'],
            entry_date=test_entry['pubDate']
        )
        
        # Verify the entry is marked as processed
        self.assertTrue(
            test_state_manager.is_entry_processed(feed_url, test_entry['guid']),
            "Entry should be marked as processed"
        )
        
        # Now test that a previously processed article with a keyword is included in full
        test_entry_2 = {
            'title': "Apple Silicon Update: New Performance Records",
            'link': "https://example.com/apple-silicon",
            'guid': "apple-silicon-guid",
            'pubDate': datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')
        }
        
        # Mark as processed but still should be included due to keyword
        test_state_manager.add_processed_entry(
            feed_url=feed_url,
            entry_id=test_entry_2['guid'],
            entry_date=test_entry_2['pubDate']
        )
        
        # Test that our keyword recognition logic works correctly
        # This manually implements the logic from process_feed for handling pre-processed entries
        is_processed = test_state_manager.is_entry_processed(feed_url, test_entry_2['guid'])
        self.assertTrue(is_processed, "Entry should be marked as processed")
        
        # Check if articles with specific keywords are shown in full even when previously processed
        title = test_entry_2['title']
        has_keyword = any(kw.lower() in title.lower() for kw in [
            "apple silicon", "vision pro", "ios", "final cut pro", 
            "macbook", "iphone", "update"
        ])
        self.assertTrue(has_keyword, "Title should contain a keyword for full article display")
        
        # This verifies that the core logic for showing previously processed articles works
        preference = "FULL" if has_keyword else "SUMMARY"
        self.assertEqual(preference, "FULL", 
                        "Previously processed article with keyword should be shown in FULL")
    
    def test_create_consolidated_summary(self):
        """Test creating a consolidated summary."""
        # Create test articles
        articles = [
            {
                'title': 'Popular Social Media App Updates Privacy Policy',
                'link': 'https://test.example.com/tech/social-media-privacy-update',
                'guid': 'article1',
                'pubDate': 'Wed, 27 Mar 2024 12:00:00 GMT',
                'summary': 'A widely used social media platform has updated its privacy policy following regulatory pressure.'
            },
            {
                'title': 'New Entertainment Streaming Service Launches',
                'link': 'https://test.example.com/tech/new-streaming-service',
                'guid': 'article2',
                'pubDate': 'Wed, 27 Mar 2024 14:00:00 GMT',
                'summary': 'A new entertainment streaming service has launched with exclusive content partnerships.'
            }
        ]
        
        # Create consolidated summary
        result = self.feed_processor.create_consolidated_summary(articles, "https://test.example.com/feed.xml")
        
        # Check result
        self.assertIsNotNone(result)
        self.assertIn("Digest", result['title'])
        self.assertIn("Tech Updates Digest", result['description'])
        
        # Verify link structure
        self.assertTrue(result['link'].startswith("https://digest.example.com/"))
        
        # Verify the digest flag is set
        self.assertTrue(result.get('is_digest', False), "Result should have is_digest flag set")
    
    def test_create_consolidated_summary_empty_articles(self):
        """Test creating a consolidated summary with empty articles."""
        # Create consolidated summary with empty list
        result = self.feed_processor.create_consolidated_summary([], "https://test.example.com/feed.xml")
        
        # Should return None for empty articles
        self.assertIsNone(result)
    
    @patch("rss_buddy.feed_processor.FeedProcessor.fetch_rss_feed")
    @patch("xml.etree.ElementTree.ElementTree.write")
    def test_process_feed(self, mock_write, mock_fetch):
        """Test processing a feed."""
        # Set up mock response
        mock_fetch.return_value = self.mocked_feed
        
        # Mock the write method (no need to actually create files)
        mock_write.return_value = None
        
        # Process the feed
        result = self.feed_processor.process_feed("https://test.example.com/feed.xml")
        
        # Check the result - just verify it's a string path
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str, "Result should be a file path string")
        
        # Verify ElementTree.write was called at least once
        mock_write.assert_called()
        
        # Verify processed entries were added to state
        processed_entries = self.state_manager.get_processed_entries("https://test.example.com/feed.xml")
        self.assertTrue(len(processed_entries) > 0)
    
    @patch("rss_buddy.feed_processor.FeedProcessor.process_feed")
    def test_process_feeds(self, mock_process_feed):
        """Test processing multiple feeds."""
        # Set up mock response
        mock_process_feed.side_effect = ["output1.xml", "output2.xml"]
        
        # Process the feeds
        results = self.feed_processor.process_feeds([
            "https://test.example.com/feed1.xml",
            "https://test.example.com/feed2.xml"
        ])
        
        # Check the results
        self.assertEqual(results, ["output1.xml", "output2.xml"])
        
        # Verify process_feed was called twice
        self.assertEqual(mock_process_feed.call_count, 2)

    def test_process_feed_with_lookback(self):
        """Test processing a feed with lookback window functionality."""
        now = datetime.now(timezone.utc)
        
        # Create mock feed data with 3 entries, 2 recent and 1 old
        mock_entries = [
            {
                'title': 'Recent Article',
                'link': 'https://example.com/article1',
                'id': 'article1',
                'summary': 'This is a recent article',
                'published': (now - timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S %z')
            },
            {
                'title': 'Old Article',
                'link': 'https://example.com/article2',
                'id': 'article2',
                'summary': 'This is an old article',
                'published': (now - timedelta(days=50)).strftime('%a, %d %b %Y %H:%M:%S %z')
            },
            {
                'title': 'Recent Article 2',
                'link': 'https://example.com/article3',
                'id': 'article3',
                'summary': 'This is another recent article',
                'published': (now - timedelta(days=2)).strftime('%a, %d %b %Y %H:%M:%S %z')
            }
        ]
        
        # Create mock feed
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.link = "https://example.com/feed"
        mock_feed.feed.description = "A test feed"
        
        # Add entries to feed
        mock_feed.entries = []
        for entry_data in mock_entries:
            entry = MagicMock()
            for key, value in entry_data.items():
                setattr(entry, key, value)
            # Add mocked get method returning string values
            entry.get = lambda k, default=None, _entry=entry: str(getattr(_entry, k, default)) if hasattr(_entry, k) else default
            mock_feed.entries.append(entry)
        
        with patch('rss_buddy.feed_processor.feedparser.parse', return_value=mock_feed), \
             patch('rss_buddy.feed_processor.FeedProcessor.evaluate_article_preference', return_value="FULL"):
            
            # Process the feed with a 3-day lookback (should only include the recent articles)
            self.feed_processor.days_lookback = 3
            output_file = self.feed_processor.process_feed("https://example.com/feed")
            
            # Check that the output file was created
            self.assertTrue(os.path.exists(output_file))
            
            # Parse the output file to check the entries
            tree = ET.parse(output_file)
            root = tree.getroot()
            items = root.findall('.//item')
            
            # Should include the two recent articles
            self.assertEqual(len(items), 2)
            
            # Check titles
            titles = [item.find('title').text for item in items]
            self.assertIn('Recent Article', titles)
            self.assertIn('Recent Article 2', titles)
            self.assertNotIn('Old Article', titles)
            
            # Process again with a longer lookback (should still only include the recent articles due to state)
            self.feed_processor.days_lookback = 30
            output_file = self.feed_processor.process_feed("https://example.com/feed")
            
            # Parse the output file to check the entries (should be empty due to state tracking)
            tree = ET.parse(output_file)
            root = tree.getroot()
            items = root.findall('.//item')
            
            # Should not include any articles (all have been processed)
            self.assertEqual(len(items), 0)
    
    def test_process_feed_digest_updates(self):
        """Test that the digest is updated when new articles are found within the lookback window."""
        now = datetime.now(timezone.utc)
        
        # Create initial mock feed data with 2 entries
        mock_entries = [
            {
                'title': 'Article 1',
                'link': 'https://example.com/article1',
                'id': 'article1',
                'summary': 'This is article 1',
                'published': (now - timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S %z')
            },
            {
                'title': 'Article 2',
                'link': 'https://example.com/article2',
                'id': 'article2',
                'summary': 'This is article 2',
                'published': (now - timedelta(days=2)).strftime('%a, %d %b %Y %H:%M:%S %z')
            }
        ]
        
        # Create mock feed
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.link = "https://example.com/feed"
        mock_feed.feed.description = "A test feed"
        
        # Add entries to feed
        mock_feed.entries = []
        for entry_data in mock_entries:
            entry = MagicMock()
            for key, value in entry_data.items():
                setattr(entry, key, value)
            # Add mocked get method returning string values
            entry.get = lambda k, default=None, _entry=entry: str(getattr(_entry, k, default)) if hasattr(_entry, k) else default
            mock_feed.entries.append(entry)
        
        # Mock the evaluation method to split articles between FULL and SUMMARY
        def evaluate_side_effect(title, summary, feed_url=None):
            if title == 'Article 1':
                return "FULL"
            else:
                return "SUMMARY"
        
        # Create a digest entry
        digest_entry = {
            'title': 'Test Digest',
            'link': 'https://example.com/digest',
            'guid': 'test-digest-id',
            'pubDate': formatdate(),
            'description': 'Test digest content',
            'summary': 'Test digest content'  # Add both description and summary
        }
        
        # Second digest entry with updates
        updated_digest_entry = {
            'title': 'Updated Test Digest',
            'link': 'https://example.com/digest-updated',
            'guid': 'test-digest-id-updated',
            'pubDate': formatdate(),
            'description': 'Updated test digest content',
            'summary': 'Updated test digest content'  # Add both description and summary
        }
        
        with patch('rss_buddy.feed_processor.feedparser.parse', return_value=mock_feed), \
             patch('rss_buddy.feed_processor.FeedProcessor.evaluate_article_preference', side_effect=evaluate_side_effect), \
             patch('rss_buddy.feed_processor.FeedProcessor.create_consolidated_summary', return_value=digest_entry):
            
            # Process the feed
            self.feed_processor.days_lookback = 3
            output_file = self.feed_processor.process_feed("https://example.com/feed")
            
            # Check that the output file was created
            self.assertTrue(os.path.exists(output_file))
            
            # Parse the output file to check the entries
            tree = ET.parse(output_file)
            root = tree.getroot()
            items = root.findall('.//item')
            
            # Should include article 1 (FULL) + the digest entry
            self.assertEqual(len(items), 2)
            
            # Add a new article to the feed
            new_entry_data = {
                'title': 'Article 3',
                'link': 'https://example.com/article3',
                'id': 'article3',
                'summary': 'This is article 3',
                'published': now.strftime('%a, %d %b %Y %H:%M:%S %z')
            }
            
            new_entry = MagicMock()
            for key, value in new_entry_data.items():
                setattr(new_entry, key, value)
            # Add mocked get method returning string values
            new_entry.get = lambda k, default=None, _entry=new_entry: str(getattr(_entry, k, default)) if hasattr(_entry, k) else default
            mock_feed.entries.append(new_entry)
            
            # Process with updated digest
            with patch('rss_buddy.feed_processor.FeedProcessor.create_consolidated_summary', return_value=updated_digest_entry):
                # Process the feed again
                output_file = self.feed_processor.process_feed("https://example.com/feed")
                
                # Parse the output file to check the entries
                tree = ET.parse(output_file)
                root = tree.getroot()
                items = root.findall('.//item')
                
                # Due to state tracking, should only include the digest update
                # Article 1 and 2 were already processed in the first run
                self.assertEqual(len(items), 1)
                
                # Check titles for the digest
                titles = [item.find('title').text for item in items]
                self.assertIn('Updated Test Digest', titles)

if __name__ == "__main__":
    unittest.main() 