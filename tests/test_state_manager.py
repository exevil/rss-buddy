"""Unit tests for the state manager component."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest

# Add path to allow importing package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rss_buddy.state_manager import StateManager


class TestStateManager(unittest.TestCase):
    """Test the StateManager class."""
    
    def setUp(self):
        """Set up a temporary directory for state files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        self.state_file = os.path.join(self.output_dir, "processed_state.json")
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_init_with_no_state_file(self):
        """Test initializing the state manager with no existing state file."""
        state_manager = StateManager(output_dir=self.output_dir)
        
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
    
    def test_load_existing_state(self):
        """Test loading an existing state file."""
        # Create a state file
        test_state = {
            "feeds": {
                "https://example.com/feed.xml": {
                    "processed_ids": ["1", "2", "3"],
                    "last_entry_date": "2023-01-01T12:00:00",
                    "digest": {
                        "id": "digest-20230101120000",
                        "content_hash": "abcdef123456",
                        "article_ids": ["1", "2"],
                        "last_updated": "2023-01-01T12:00:00"
                    }
                }
            },
            "last_updated": "2023-01-01T12:00:00"
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(test_state, f)
        
        # Load the state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Check that the state was loaded correctly
        self.assertEqual(
            state_manager.state["feeds"]["https://example.com/feed.xml"]["processed_ids"], 
            ["1", "2", "3"]
        )
    
    def test_is_entry_processed(self):
        """Test checking if an entry has been processed."""
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Entry should not be processed yet
        self.assertFalse(state_manager.is_entry_processed(feed_url, entry_id))
        
        # Add the entry to processed list
        state_manager.add_processed_entry(feed_url, entry_id)
        
        # Entry should be processed now
        self.assertTrue(state_manager.is_entry_processed(feed_url, entry_id))
    
    def test_add_processed_entry(self):
        """Test adding an entry to the processed list."""
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        entry_date = "2023-01-01T12:00:00"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Add the entry to processed list
        state_manager.add_processed_entry(feed_url, entry_id, entry_date)
        
        # Check that the entry was added
        feed_state = state_manager.get_processed_entries(feed_url)
        self.assertIn(entry_id, feed_state["processed_ids"])
        self.assertEqual(feed_state["last_entry_date"], entry_date)
    
    def test_update_digest_state_new_content(self):
        """Test updating digest state with new content."""
        feed_url = "https://example.com/feed.xml"
        article_ids = ["1", "2", "3"]
        content = "test content"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Update the digest state (first time)
        digest_id, is_updated = state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids,
            content=content
        )
        
        # Should create a new digest ID and report as updated
        self.assertIsNotNone(digest_id)
        self.assertTrue(is_updated)
        
        # Check that the digest state was updated
        feed_state = state_manager.get_processed_entries(feed_url)
        self.assertEqual(feed_state["digest"]["article_ids"], article_ids)
        hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()
        self.assertEqual(feed_state["digest"]["content_hash"], hash_value)
    
    def test_update_digest_state_unchanged_content(self):
        """Test updating digest state with unchanged content."""
        feed_url = "https://example.com/feed.xml"
        article_ids = ["1", "2", "3"]
        content = "test content"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # First update
        digest_id1, is_updated1 = state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids,
            content=content
        )
        
        # Second update with same content
        digest_id2, is_updated2 = state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids,
            content=content
        )
        
        # IDs should match and second update should report as not updated
        self.assertEqual(digest_id1, digest_id2)
        self.assertTrue(is_updated1)
        self.assertFalse(is_updated2)
    
    def test_update_digest_state_changed_content(self):
        """Test updating digest state with changed content."""
        feed_url = "https://example.com/feed.xml"
        article_ids1 = ["1", "2", "3"]
        article_ids2 = ["1", "2", "3", "4"]
        content1 = "test content 1"
        content2 = "test content 2"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # First update
        digest_id1, is_updated1 = state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids1,
            content=content1
        )
        
        # Sleep a bit to ensure different timestamps
        time.sleep(0.01)
        
        # Second update with different content
        digest_id2, is_updated2 = state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids2,
            content=content2
        )
        
        # IDs should be different and both updates should report as updated
        self.assertNotEqual(digest_id1, digest_id2)
        self.assertTrue(is_updated1)
        self.assertTrue(is_updated2)
    
    def test_get_recent_cutoff_date(self):
        """Test getting the cutoff date for recent entries."""
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Set days lookback
        days_lookback = 7
        
        # Get cutoff date
        cutoff_date = state_manager.get_recent_cutoff_date(days_lookback)
        
        # Check that the cutoff date is approximately correct (within 1 minute)
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=days_lookback)
        diff = abs((cutoff_date - expected_cutoff).total_seconds())
        self.assertLess(diff, 60)  # Within 60 seconds
    
    def test_get_articles_in_digest(self):
        """Test retrieving articles that are part of a digest."""
        feed_url = "https://example.com/feed.xml"
        
        # Create test articles
        test_articles = {
            "article1": {
                "id": "article1",
                "title": "Test Article 1",
                "link": "https://example.com/article1",
                "date": "2023-01-01T12:00:00",
                "display_mode": "SUMMARY"
            },
            "article2": {
                "id": "article2",
                "title": "Test Article 2",
                "link": "https://example.com/article2",
                "date": "2023-01-01T13:00:00",
                "display_mode": "FULL"
            }
        }
        
        # Set up a digest with these articles
        state_manager = StateManager(output_dir=self.output_dir)
        for article_id, article_data in test_articles.items():
            state_manager.add_processed_entry(
                feed_url=feed_url,
                entry_id=article_id,
                entry_date=article_data["date"],
                entry_data=article_data
            )
        
        state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=list(test_articles.keys()),
            content="test digest content"
        )
        
        # Get articles in the digest
        digest_article_ids = state_manager.get_articles_in_digest(feed_url)
        
        # Check that the articles were retrieved correctly
        self.assertIsInstance(digest_article_ids, list)
        self.assertEqual(len(digest_article_ids), 2)
        
        # Verify the correct IDs are present
        self.assertIn("article1", digest_article_ids)
        self.assertIn("article2", digest_article_ids)
    
    def test_save_state(self):
        """Test saving the state to a file."""
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Add some test data
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        entry_date = "2023-01-01T12:00:00"
        state_manager.add_processed_entry(feed_url, entry_id, entry_date)
        
        # Save the state
        state_manager.save_state()
        
        # Check that the file exists
        self.assertTrue(os.path.exists(self.state_file))
        
        # Load the file and check the content
        with open(self.state_file, 'r') as f:
            saved_state = json.load(f)
        
        self.assertIn("feeds", saved_state)
        self.assertIn(feed_url, saved_state["feeds"])
    
    def test_is_entry_processed_with_lookback(self):
        """Test checking if an entry has been processed with lookback period."""
        feed_url = "https://example.com/feed.xml"
        
        # Create entries with different dates
        now = datetime.now(timezone.utc)
        recent_entry_id = "recent_entry"
        recent_entry_date = now.isoformat()
        
        old_entry_id = "old_entry"
        old_entry_date = (now - timedelta(days=14)).isoformat()
        
        # Create a state manager and add the entries
        state_manager = StateManager(output_dir=self.output_dir)
        state_manager.add_processed_entry(feed_url, recent_entry_id, recent_entry_date)
        state_manager.add_processed_entry(feed_url, old_entry_id, old_entry_date)
        
        # Check with a 7-day lookback
        # Recent entry should be considered, old entry should not
        lookback_days = 7
        self.assertTrue(state_manager.is_entry_processed(feed_url, recent_entry_id, lookback_days))
        self.assertFalse(state_manager.is_entry_processed(feed_url, old_entry_id, lookback_days))
        
        # Check with a 30-day lookback (both should be considered)
        lookback_days = 30
        self.assertTrue(state_manager.is_entry_processed(feed_url, recent_entry_id, lookback_days))
        self.assertTrue(state_manager.is_entry_processed(feed_url, old_entry_id, lookback_days))

    def test_get_articles_in_digest_no_digest(self):
        """Test retrieving articles when no digest exists for the feed."""
        feed_url = "https://example.com/feed.xml"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Verify that articles in the digest are correctly identified
        digest_article_ids = state_manager.get_articles_in_digest(feed_url)
        self.assertIsInstance(digest_article_ids, list)
        self.assertEqual(len(digest_article_ids), 0)


if __name__ == "__main__":
    unittest.main() 