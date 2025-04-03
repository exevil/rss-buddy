#!/usr/bin/env python3
"""Module for managing state of processed feed entries and tracking digest articles."""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dateutil import parser


class StateManager:
    """Manages the state of processed articles to avoid reprocessing and enable lookback."""

    def __init__(self, state_file: Optional[str] = None, output_dir: str = "processed_feeds"):
        """Initialize the state manager.

        Args:
            state_file: Path to the state file. If None, uses output_dir/processed_state.json.
            output_dir: Directory where processed feeds and state are stored.
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.state_file = state_file or os.path.join(self.output_dir, "processed_state.json")
        self.state = self._load_state()

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse a date string into a timezone-aware datetime object (UTC)."""
        if not date_str:
            return None
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

            def tzinfos(tzname, _offset):
                return timezone_replacements.get(tzname)

            # Normalize timezone abbreviations before parsing
            normalized_date_str = date_str
            for tz, offset in timezone_replacements.items():
                if tz in normalized_date_str:
                    normalized_date_str = normalized_date_str.replace(tz, offset)
                    break  # Replace only the first occurrence

            parsed_date = parser.parse(normalized_date_str, tzinfos=tzinfos)

            # Ensure the date is timezone-aware, defaulting to UTC
            if parsed_date.tzinfo is None:
                # Try ignoretz=True as a fallback before assuming UTC
                try:
                    parsed_date_ignoretz = parser.parse(date_str, ignoretz=True)
                    parsed_date = parsed_date_ignoretz.replace(tzinfo=timezone.utc)
                except Exception:
                    # If ignoretz also fails, assume UTC for the original parsed date
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)

            # Convert aware datetimes to UTC
            return parsed_date.astimezone(timezone.utc)
        except Exception as e:
            print(f"Failed to parse date '{date_str}': {e}")
            return None  # Indicate parsing failure

    def _load_state(self) -> Dict[str, Any]:
        """Load the state from the state file or create a new state."""
        if not os.path.exists(self.state_file):
            return self._create_new_state()

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

                # --- Migration Logic ---
                # Check for old structure ('processed_ids', 'digest') and migrate
                needs_migration = False
                for feed_url, feed_state in state.get("feeds", {}).items():
                    if "processed_ids" in feed_state or "digest" in feed_state:
                        needs_migration = True
                        break  # Found one feed needing migration, no need to check others

                if needs_migration:
                    print("Migrating state file to new structure...")
                    new_state = self._create_new_state()
                    for feed_url, old_feed_state in state.get("feeds", {}).items():
                        new_entry_data = {}
                        # Migrate entries from old 'entry_data' if present
                        if "entry_data" in old_feed_state:
                            for entry_id, entry_details in old_feed_state["entry_data"].items():
                                # Try to get original publish date
                                publish_date_str = entry_details.get("date")
                                # Basic structure for migrated entry
                                new_entry_data[entry_id] = {
                                    "id": entry_id,
                                    "date": publish_date_str,  # Keep original date string
                                    # Assume 'processed' if found here, status was not tracked before
                                    "status": "processed",
                                    # Use file's last updated time as a rough processed_at
                                    "processed_at": state.get(
                                        "last_updated", datetime.now(timezone.utc).isoformat()
                                    ),
                                    # Carry over other known fields if they exist
                                    "title": entry_details.get("title"),
                                    "link": entry_details.get("link"),
                                    "summary": entry_details.get("summary"),
                                    # Add other relevant fields if they were stored
                                }
                        # Add potentially missing entries from processed_ids (though they lack details)
                        if "processed_ids" in old_feed_state:
                            for entry_id in old_feed_state["processed_ids"]:
                                if entry_id not in new_entry_data:
                                    new_entry_data[entry_id] = {
                                        "id": entry_id,
                                        "date": None,  # No date info available
                                        "status": "processed",  # Assume processed
                                        "processed_at": state.get(
                                            "last_updated", datetime.now(timezone.utc).isoformat()
                                        ),
                                        "title": None,  # No title info
                                        "link": None,  # No link info
                                        "summary": None,  # No summary info
                                    }

                        if new_entry_data:
                            new_state["feeds"][feed_url] = {"entry_data": new_entry_data}

                    state = new_state  # Replace old state with migrated state
                    print("State migration complete.")
                    # Consider saving the migrated state immediately
                    # self.state = state
                    # self.save_state()
                # --- End Migration Logic ---

                # Ensure basic structure exists after loading/migration
                if "feeds" not in state:
                    state["feeds"] = {}
                state["last_updated"] = state.get(
                    "last_updated", datetime.now(timezone.utc).isoformat()
                )

                return state

        except json.JSONDecodeError:
            print(f"Error decoding JSON from state file: {self.state_file}. Creating new state.")
            return self._create_new_state()
        except Exception as e:
            print(f"Unexpected error loading state file: {self.state_file}. Error: {e}")
            return self._create_new_state()

    def _create_new_state(self) -> Dict[str, Any]:
        """Create a new state structure."""
        return {"feeds": {}, "last_updated": datetime.now(timezone.utc).isoformat()}

    def _cleanup_old_entries(self, days_lookback: int):
        """Remove entries older than the lookback period based on their publish date."""
        if not days_lookback or days_lookback <= 0:
            return  # No cleanup needed if lookback is not positive

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
        feeds_to_update = {}

        for feed_url, feed_state in self.state.get("feeds", {}).items():
            entry_data = feed_state.get("entry_data", {})
            entries_to_keep = {}
            entries_removed = 0

            for entry_id, entry_details in entry_data.items():
                publish_date_str = entry_details.get("date")
                publish_date = self._parse_date(publish_date_str)

                # Keep entry if:
                # 1. Date is missing (can't determine age)
                # 2. Date parsing failed (can't determine age)
                # 3. Date is within the lookback period
                if publish_date is None or publish_date >= cutoff_date:
                    entries_to_keep[entry_id] = entry_details
                else:
                    entries_removed += 1

            if entries_removed > 0:
                feeds_to_update[feed_url] = {"entry_data": entries_to_keep}
                # print(f"Cleaned up {entries_removed} old entries from feed: {feed_url}") # Optional: Logging

        # Update the state with cleaned feeds
        if feeds_to_update:
            self.state["feeds"].update(feeds_to_update)
            # Remove feeds entirely if they become empty after cleanup
            feeds_to_remove = [
                url for url, data in self.state["feeds"].items() if not data.get("entry_data")
            ]
            for url in feeds_to_remove:
                del self.state["feeds"][url]
                # print(f"Removed empty feed state for: {url}") # Optional: Logging

    def save_state(self, days_lookback: Optional[int] = None):
        """Save the current state to the file after cleaning up old entries."""
        if days_lookback is not None:
            self._cleanup_old_entries(days_lookback)

        self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2, default=str)  # Use default=str for datetime obj
        except Exception as e:
            print(f"Error saving state file {self.state_file}: {e}")

    def get_entry_status(self, feed_url: str, entry_id: str) -> Optional[str]:
        """Check if an entry has been processed and return its status ('processed' or 'digest').

        Args:
            feed_url: The URL of the feed.
            entry_id: The ID of the entry.

        Returns:
            The status ("processed" or "digest") if the entry exists, otherwise None.
        """
        feed_state = self.state.get("feeds", {}).get(feed_url, {})
        entry_data = feed_state.get("entry_data", {}).get(entry_id)

        if entry_data:
            return entry_data.get("status")  # Return status if entry exists
        return None  # Entry not found

    def add_processed_entry(
        self,
        feed_url: str,
        entry_id: str,
        status: str,
        entry_data: Dict[str, Any],
        feed_title: Optional[str] = None,
    ):
        """Add or update a processed entry's state.

        Args:
            feed_url: The URL of the feed.
            entry_id: The ID of the entry.
            status: The processing status ('processed' or 'digest').
            entry_data: The full data dictionary for the entry (must include 'date').
            feed_title: The title of the feed (optional, stored once per feed).
        """
        # Ensure the top-level feed structure exists
        if feed_url not in self.state.get("feeds", {}):
            self.state["feeds"][feed_url] = {"entry_data": {}, "feed_title": None}
        elif "entry_data" not in self.state["feeds"][feed_url]:
            self.state["feeds"][feed_url]["entry_data"] = {}

        # Store the feed title if provided and not already set
        if feed_title and not self.state["feeds"][feed_url].get("feed_title"):
            self.state["feeds"][feed_url]["feed_title"] = feed_title

        # Ensure basic structure exists for the specific entry
        current_entry = self.state["feeds"][feed_url]["entry_data"].get(entry_id, {})

        # Update entry data, preserving existing fields if not provided in new data
        updated_entry = {**current_entry, **entry_data}  # Merge new data over old

        # Set/update status and processing time
        updated_entry["status"] = status
        updated_entry["processed_at"] = datetime.now(timezone.utc).isoformat()
        # Ensure 'id' is present, using entry_id as fallback
        updated_entry["id"] = entry_id

        # Store the updated entry data
        self.state["feeds"][feed_url]["entry_data"][entry_id] = updated_entry

    def get_items_in_lookback(self, feed_url: str, days_lookback: int) -> List[Dict[str, Any]]:
        """Get all processed items within the lookback period for a specific feed.

        Args:
            feed_url: The URL of the feed.
            days_lookback: Number of days to look back based on item publish date.

        Returns:
            A list of entry data dictionaries for items within the lookback period.
        """
        items_in_period = []
        feed_state = self.state.get("feeds", {}).get(feed_url, {})
        entry_data = feed_state.get("entry_data", {})

        if not entry_data or days_lookback <= 0:
            return []  # No data or invalid lookback

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)

        for entry_id, entry_details in entry_data.items():
            publish_date_str = entry_details.get("date")
            publish_date = self._parse_date(publish_date_str)

            # Include entry if:
            # 1. Date is missing (assume recent or keep indefinitely?) - Let's keep for now.
            # 2. Date parsing failed (assume recent or keep indefinitely?) - Let's keep for now.
            # 3. Date is within the lookback period
            if publish_date is None or publish_date >= cutoff_date:
                items_in_period.append(entry_details)  # Append the full entry details

        # Optional: Sort by publish date descending (most recent first)
        items_in_period.sort(
            key=lambda x: self._parse_date(x.get("date"))
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        return items_in_period

    def get_feed_title(self, feed_url: str) -> Optional[str]:
        """Retrieve the stored title for a given feed URL."""
        feed_state = self.state.get("feeds", {}).get(feed_url, {})
        return feed_state.get("feed_title")
