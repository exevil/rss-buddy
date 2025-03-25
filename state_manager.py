#!/usr/bin/env python3
import os
import json
from datetime import datetime

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
                    return json.load(f)
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
        return self.state["feeds"].get(feed_url, {"processed_ids": [], "last_entry_date": None})
    
    def is_entry_processed(self, feed_url, entry_id):
        """Check if an entry with the given ID has been processed for the feed."""
        feed_state = self.get_processed_entries(feed_url)
        return entry_id in feed_state["processed_ids"]
    
    def add_processed_entry(self, feed_url, entry_id, entry_date=None):
        """Add an entry ID to the list of processed entries for the feed."""
        if feed_url not in self.state["feeds"]:
            self.state["feeds"][feed_url] = {"processed_ids": [], "last_entry_date": None}
        
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
    
    def clean_old_entries(self, max_days=30):
        """Clean entries older than max_days to prevent the state file from growing too large."""
        # This would require storing dates with each entry
        # For simplicity, we just limit the number of IDs per feed
        pass 