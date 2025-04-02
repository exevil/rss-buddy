#!/usr/bin/env python3
"""Module for managing state of processed feed entries and tracking digest articles."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from dateutil import parser


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
                with open(self.state_file, "r") as f:
                    state = json.load(f)

                    # Check if we need to upgrade the state structure
                    if "feeds" in state:
                        for _feed_url, feed_state in state["feeds"].items():
                            # Add digest tracking if not present
                            if "digest" not in feed_state:
                                feed_state["digest"] = {
                                    "id": None,
                                    "content_hash": None,
                                    "article_ids": [],
                                    "last_updated": None,
                                }

                    return state
            except Exception:
                print(f"Error loading state file: {self.state_file}")
                return self._create_new_state()
        else:
            return self._create_new_state()

    def _create_new_state(self):
        """Create a new state structure."""
        return {"feeds": {}, "last_updated": datetime.now().isoformat()}

    def save_state(self):
        """Save the current state to the state file."""
        self.state["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state file: {e}")

    def get_processed_entries(self, feed_url):
        """Get the processed entries for a feed."""
        if feed_url not in self.state["feeds"]:
            self.state["feeds"][feed_url] = {
                "processed_ids": [],
                "last_entry_date": None,
                "entry_data": {},  # Store additional data for each entry
                "digest": {
                    "id": None,
                    "content_hash": None,
                    "article_ids": [],
                    "last_updated": None,
                },
            }
        return self.state["feeds"][feed_url]

    def is_entry_processed(self, feed_url, entry_id, days_lookback=None):
        """Check if an entry with the given ID has been processed for the feed.

        Args:
            feed_url: The URL of the feed
            entry_id: The ID of the entry
            days_lookback: Number of days to look back. If None, only check if ID exists.

        Returns:
            bool: True if entry is processed and within lookback window (if specified)
        """
        feed_state = self.get_processed_entries(feed_url)

        # If entry is not in processed list, it's not processed
        if entry_id not in feed_state["processed_ids"]:
            return False

        # If no lookback window specified, just check if it exists
        if days_lookback is None:
            return True

        # Get entry data to check date
        entry_data = feed_state.get("entry_data", {}).get(entry_id)
        if not entry_data or "date" not in entry_data:
            # If date is missing, cannot determine recency, so return False
            return False

        try:
            # Common problematic timezone abbreviations and their approximate UTC offsets
            timezone_replacements = {
                "PDT": "-0700",
                "PST": "-0800",
                "EDT": "-0400",
                "EST": "-0500",
                "CEST": "+0200",
                "CET": "+0100",
                "AEST": "+1000",
                "AEDT": "+1100",
            }

            def tzinfos(tzname, offset):
                return timezone_replacements.get(tzname, None)

            entry_date = parser.parse(entry_data["date"], tzinfos=tzinfos)

            # Ensure the date is timezone-aware, defaulting to UTC
            if entry_date.tzinfo is None:
                entry_date = entry_date.replace(tzinfo=timezone.utc)

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
            return entry_date >= cutoff_date
        except Exception:
            print(f"Failed to parse date for entry {entry_id} in feed {feed_url}")
            # If date is unparseable, cannot determine recency, so return False
            return False

    def get_entry_data(self, feed_url, entry_id):
        """Get stored data for a processed entry.

        Args:
            feed_url: The URL of the feed
            entry_id: The ID of the entry

        Returns:
            dict: Stored data for the entry or None if not found
        """
        feed_state = self.get_processed_entries(feed_url)
        return feed_state.get("entry_data", {}).get(entry_id)

    def add_processed_entry(self, feed_url, entry_id, entry_date=None, entry_data=None):
        """Add an entry ID to the list of processed entries for the feed.

        Args:
            feed_url: The URL of the feed
            entry_id: The ID of the entry
            entry_date: The date of the entry
            entry_data: Additional data to store for the entry
        """
        if feed_url not in self.state["feeds"]:
            self.state["feeds"][feed_url] = {
                "processed_ids": [],
                "last_entry_date": None,
                "entry_data": {},
                "digest": {
                    "id": None,
                    "content_hash": None,
                    "article_ids": [],
                    "last_updated": None,
                },
            }

        # Add entry to processed list if not already present
        if entry_id not in self.state["feeds"][feed_url]["processed_ids"]:
            self.state["feeds"][feed_url]["processed_ids"].append(entry_id)

        # Update last entry date if newer
        current_last_date = self.state["feeds"][feed_url]["last_entry_date"]
        if self._is_newer_date(entry_date, current_last_date):
            self.state["feeds"][feed_url]["last_entry_date"] = entry_date

        # Ensure entry_data structure exists
        if "entry_data" not in self.state["feeds"][feed_url]:
            self.state["feeds"][feed_url]["entry_data"] = {}

        # Ensure the entry_id key exists in entry_data before updating
        if entry_id not in self.state["feeds"][feed_url]["entry_data"]:
            self.state["feeds"][feed_url]["entry_data"][entry_id] = {}

        # Store or update entry data
        if entry_data:  # Merge provided data if any
            self.state["feeds"][feed_url]["entry_data"][entry_id].update(entry_data)

        # Always store/update the date if provided
        if entry_date:
            # Now it's safe to add the date
            self.state["feeds"][feed_url]["entry_data"][entry_id]["date"] = entry_date

        # Limit the number of stored IDs to prevent unlimited growth
        max_ids = 1000  # Store at most 1000 IDs per feed
        if len(self.state["feeds"][feed_url]["processed_ids"]) > max_ids:
            # Keep only the most recent IDs and their data
            recent_ids = self.state["feeds"][feed_url]["processed_ids"][-max_ids:]
            self.state["feeds"][feed_url]["processed_ids"] = recent_ids
            if "entry_data" in self.state["feeds"][feed_url]:
                # Keep only data for recent IDs
                self.state["feeds"][feed_url]["entry_data"] = {
                    k: v
                    for k, v in self.state["feeds"][feed_url]["entry_data"].items()
                    if k in recent_ids
                }

    def _is_newer_date(self, new_date_str, current_date_str):
        """Safely compare two date strings, returning True if new_date_str is newer."""
        if not current_date_str:
            return True  # No current date, so new date is newer
        if not new_date_str:
            return False  # No new date, cannot be newer

        try:
            current_dt = parser.parse(current_date_str)
            new_dt = parser.parse(new_date_str)
            # Ensure timezone awareness for comparison
            if current_dt.tzinfo is None:
                current_dt = current_dt.replace(tzinfo=timezone.utc)
            if new_dt.tzinfo is None:
                new_dt = new_dt.replace(tzinfo=timezone.utc)
            return new_dt > current_dt
        except Exception:
            # Fallback to string comparison if parsing fails
            return new_date_str > current_date_str

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
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        # Check if digest content has changed
        is_updated = False
        if feed_state["digest"]["content_hash"] != content_hash:
            is_updated = True
            # Generate a new digest ID - use microseconds for more uniqueness in tests
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            feed_state["digest"]["id"] = f"digest-{timestamp}"
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
