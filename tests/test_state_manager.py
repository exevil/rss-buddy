"""Unit tests for the state manager component."""
import os
import json
import tempfile
import unittest
import time
from datetime import datetime, timedelta, timezone
import hashlib

import sys
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
        self.assertEqual(feed_state["digest"]["content_hash"], 
                         hashlib.md5(content.encode('utf-8')).hexdigest())
    
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
        
        days_lookback = 3
        cutoff_date = state_manager.get_recent_cutoff_date(days_lookback)
        
        # Cutoff date should be about 3 days ago
        expected_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
        date_diff = abs((cutoff_date - expected_date).total_seconds())
        
        # Allow for a 5-second difference due to test execution time
        self.assertLess(date_diff, 5)
    
    def test_get_articles_in_digest(self):
        """Test getting articles in a digest."""
        feed_url = "https://example.com/feed.xml"
        article_ids = ["1", "2", "3"]
        content = "test content"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Update the digest state
        state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids,
            content=content
        )
        
        # Get articles in digest
        articles = state_manager.get_articles_in_digest(feed_url)
        
        # Should match the article IDs we added
        self.assertEqual(articles, article_ids)
    
    def test_save_state(self):
        """Test saving the state."""
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        
        # Create a state manager and add an entry
        state_manager = StateManager(output_dir=self.output_dir)
        state_manager.add_processed_entry(feed_url, entry_id)
        
        # Save the state
        state_manager.save_state()
        
        # Create a new state manager and check that the entry is still there
        new_state_manager = StateManager(output_dir=self.output_dir)
        self.assertTrue(new_state_manager.is_entry_processed(feed_url, entry_id))
    
    def test_is_entry_processed_with_lookback(self):
        """Test checking if an entry has been processed within the lookback window."""
        feed_url = "https://example.com/feed.xml"
        entry_id = "test_entry_1"
        
        # Create a state manager with empty state
        state_manager = StateManager(output_dir=self.output_dir)
        
        # Add an entry with a date from 5 days ago
        old_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        state_manager.add_processed_entry(
            feed_url=feed_url,
            entry_id=entry_id,
            entry_date=old_date,
            entry_data={"date": old_date}
        )
        
        # With 3-day lookback, entry should not be considered processed
        self.assertFalse(state_manager.is_entry_processed(feed_url, entry_id, days_lookback=3))
        
        # With 7-day lookback, entry should be considered processed
        self.assertTrue(state_manager.is_entry_processed(feed_url, entry_id, days_lookback=7))
        
        # Add a newer entry
        new_entry_id = "test_entry_2"
        new_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        state_manager.add_processed_entry(
            feed_url=feed_url,
            entry_id=new_entry_id,
            entry_date=new_date,
            entry_data={"date": new_date}
        )
        
        # New entry should be considered processed with 3-day lookback
        self.assertTrue(state_manager.is_entry_processed(feed_url, new_entry_id, days_lookback=3))
        
        # Test with missing date data
        no_date_entry_id = "test_entry_3"
        state_manager.add_processed_entry(feed_url, no_date_entry_id)
        self.assertTrue(state_manager.is_entry_processed(feed_url, no_date_entry_id, days_lookback=3))
        
        # Test with invalid date data
        invalid_date_entry_id = "test_entry_4"
        state_manager.add_processed_entry(
            feed_url=feed_url,
            entry_id=invalid_date_entry_id,
            entry_data={"date": "invalid date"}
        )
        self.assertTrue(state_manager.is_entry_processed(feed_url, invalid_date_entry_id, days_lookback=3))

if __name__ == "__main__":
    unittest.main() 