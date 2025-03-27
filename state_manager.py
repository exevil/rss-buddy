#!/usr/bin/env python3
import os
import json
import hashlib
from datetime import datetime, timedelta, timezone

class StateManager:
    """Manages the state of processed articles to avoid reprocessing."""
    
    def __init__(self, state_file=None, output_dir="processed_feeds"):
        """Initialize the state manager with the given state file.
        
        Args:
            state_file: Path to the state file. If None, uses output_dir/processed_state.json
            output_dir: Directory where processed feeds and state are stored
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Use provided state file or default location in output directory
        if state_file is None:
            self.state_file = os.path.join(self.output_dir, "processed_state.json")
        else:
            self.state_file = state_file
            
        self.state = self._load_state()
    
    def _load_state(self):
        """Load the state from the state file or create a new state."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                    # Check if we need to upgrade the state structure
                    if "feeds" in state:
                        for feed_url, feed_state in state["feeds"].items():
                            # Add digest tracking if not present
                            if "digest" not in feed_state:
                                feed_state["digest"] = {
                                    "id": None,
                                    "content_hash": None,
                                    "article_ids": [],
                                    "last_updated": None
                                }
                    
                    return state
            except Exception as e:
                print(f"Error loading state file: {e}")
                return self._create_new_state()
        else:
            return self._create_new_state()
    
    def _create_new_state(self):
        """Create a new state structure."""
        return {
            "feeds": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def save_state(self):
        """Save the current state to the state file."""
        self.state["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state file: {e}")
    
    def get_processed_entries(self, feed_url):
        """Get the processed entries for a feed."""
        if feed_url not in self.state["feeds"]:
            self.state["feeds"][feed_url] = {
                "processed_ids": [], 
                "last_entry_date": None,
                "digest": {
                    "id": None,
                    "content_hash": None,
                    "article_ids": [],
                    "last_updated": None
                }
            }
        return self.state["feeds"][feed_url]
    
    def is_entry_processed(self, feed_url, entry_id):
        """Check if an entry with the given ID has been processed for the feed."""
        feed_state = self.get_processed_entries(feed_url)
        return entry_id in feed_state["processed_ids"]
    
    def add_processed_entry(self, feed_url, entry_id, entry_date=None):
        """Add an entry ID to the list of processed entries for the feed."""
        if feed_url not in self.state["feeds"]:
            self.state["feeds"][feed_url] = {
                "processed_ids": [], 
                "last_entry_date": None,
                "digest": {
                    "id": None,
                    "content_hash": None,
                    "article_ids": [],
                    "last_updated": None
                }
            }
        
        # Add entry to processed list
        if entry_id not in self.state["feeds"][feed_url]["processed_ids"]:
            self.state["feeds"][feed_url]["processed_ids"].append(entry_id)
        
        # Update last entry date if newer
        if entry_date:
            current_date = self.state["feeds"][feed_url]["last_entry_date"]
            if not current_date or entry_date > current_date:
                self.state["feeds"][feed_url]["last_entry_date"] = entry_date
        
        # Limit the number of stored IDs to prevent unlimited growth
        max_ids = 1000  # Store at most 1000 IDs per feed
        if len(self.state["feeds"][feed_url]["processed_ids"]) > max_ids:
            # Keep only the most recent IDs
            self.state["feeds"][feed_url]["processed_ids"] = self.state["feeds"][feed_url]["processed_ids"][-max_ids:]
    
    def get_last_entry_date(self, feed_url):
        """Get the date of the last processed entry for the feed."""
        feed_state = self.get_processed_entries(feed_url)
        return feed_state["last_entry_date"]
    
    def update_digest_state(self, feed_url, article_ids, content):
        """Update the digest state for a feed.
        
        Args:
            feed_url: The URL of the feed
            article_ids: List of IDs of articles in the digest
            content: A string representation of digest content used for hashing
            
        Returns:
            tuple: (digest_id, is_updated) where is_updated indicates if the digest content changed
        """
        feed_state = self.get_processed_entries(feed_url)
        
        # Generate a hash of the content
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # Check if digest content has changed
        is_updated = False
        if feed_state["digest"]["content_hash"] != content_hash:
            is_updated = True
            # Generate a new digest ID if content changed
            feed_state["digest"]["id"] = f"digest-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            feed_state["digest"]["content_hash"] = content_hash
            feed_state["digest"]["article_ids"] = article_ids
            feed_state["digest"]["last_updated"] = datetime.now().isoformat()
        
        return feed_state["digest"]["id"], is_updated
    
    def get_recent_cutoff_date(self, days_lookback=3):
        """Get the cutoff date for recent entries.
        
        Args:
            days_lookback: Number of days to look back
            
        Returns:
            datetime: The cutoff date (entries after this are considered recent)
        """
        return datetime.now(timezone.utc) - timedelta(days=days_lookback)
    
    def get_articles_in_digest(self, feed_url):
        """Get the list of article IDs that are already in the digest for a feed.
        
        Args:
            feed_url: The URL of the feed
            
        Returns:
            list: List of article IDs in the digest
        """
        feed_state = self.get_processed_entries(feed_url)
        return feed_state["digest"]["article_ids"] 