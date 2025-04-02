"""Core RSS feed processing functionality."""

import datetime
import hashlib
import re
from datetime import timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import feedparser
from dateutil import parser

from .ai_interface import AIInterface
from .state_manager import StateManager


class FeedProcessor:
    """Processes RSS feeds, classifies new entries, and updates state."""

    def __init__(
        self,
        state_manager: StateManager,
        ai_interface: AIInterface,
        days_lookback: int = 7,
        user_preference_criteria: str = "",
        summary_max_tokens: int = 150,
    ):
        """Initialize the feed processor.

        Args:
            state_manager: StateManager instance to track processed articles
            ai_interface: AIInterface instance for article evaluation
            days_lookback: Number of days to look back for articles
            user_preference_criteria: Criteria for article preference evaluation
            summary_max_tokens: Maximum tokens for AI summaries (if used by AIInterface)
        """
        self.days_lookback = days_lookback
        self.user_preference_criteria = user_preference_criteria
        self.summary_max_tokens = summary_max_tokens

        # Use provided instances directly
        self.state_manager = state_manager
        self.ai_interface = ai_interface

    def generate_entry_id(self, entry: Dict[str, Any]) -> str:
        """Generate a unique ID for an entry based on its link, guid, or title/summary hash."""
        # Prefer guid if available
        entry_guid = entry.get("guid")
        if entry_guid and entry.get("guidislink") is False:
            return entry_guid

        # Use link if available and not a permalink guid
        entry_link = entry.get("link")
        if entry_link:
            return entry_link

        # Use guid if it's the only identifier, even if it's a permalink
        if entry_guid:
            return entry_guid

        # Fallback to hashing title and summary
        content = entry.get("title", "") + entry.get("summary", "")
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def fetch_rss_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse an RSS feed from the given URL."""
        try:
            print(f"  Fetching feed: {url}")
            feed_data = feedparser.parse(url)
            if feed_data.bozo:
                bozo_type = feed_data.bozo_exception.__class__.__name__
                print(
                    f"    Warning: Feed is not well-formed ({bozo_type}). Processing may be incomplete."
                )
            return feed_data
        except Exception as e:
            print(f"    Error fetching or parsing feed {url}: {e}")
            return None

    def _parse_date(self, entry_date_str: Optional[str]) -> Optional[datetime.datetime]:
        """Parse a date string into a timezone-aware datetime object (UTC)."""
        if not entry_date_str:
            return None

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
            # Add GMT/UTC explicitly, though parser usually handles them
            "GMT": "+0000",
            "UTC": "+0000",
        }

        def tzinfos(tzname, _offset):
            # Let parser handle standard offsets first if possible
            return timezone_replacements.get(tzname)

        parsed_date = None

        # Attempt 1: Standard parsing (might handle GMT, +0000 etc.)
        try:
            parsed_date = parser.parse(entry_date_str)
        except Exception:
            pass  # Ignore failure, try next method

        # Attempt 2: Try parsing ignoring timezone info (common fallback)
        if parsed_date is None:
            try:
                # This might succeed where standard parsing fails due to odd TZ
                parsed_date = parser.parse(entry_date_str, ignoretz=True)
            except Exception:
                pass  # Ignore failure, try next method

        # Attempt 3: Normalize known timezone strings (PDT, EST etc.) and parse
        if parsed_date is None:
            try:
                normalized_date_str = entry_date_str
                for tz, offset in timezone_replacements.items():
                    # Use regex to replace tz only if it's a standalone word
                    # Prevents replacing 'EST' in 'TEST'
                    # Consider case-insensitivity? parser might handle it.
                    pattern = r"\b" + re.escape(tz) + r"\b"
                    if re.search(pattern, normalized_date_str):
                        normalized_date_str = re.sub(pattern, offset, normalized_date_str)
                        # Don't break, might have multiple (though unlikely)

                # If normalization occurred, try parsing with tzinfos
                if normalized_date_str != entry_date_str:
                    parsed_date = parser.parse(normalized_date_str, tzinfos=tzinfos)
                else:  # If no normalization, try standard parse with tzinfos as fallback
                    parsed_date = parser.parse(entry_date_str, tzinfos=tzinfos)

            except Exception:
                pass  # Ignore failure, try next method

        # Attempt 4: Try fuzzy parsing as a last resort
        if parsed_date is None:
            try:
                # Fuzzy parsing tries to find date/time within a larger string
                parsed_date = parser.parse(entry_date_str, fuzzy=True)
            except Exception:
                pass  # All parsing attempts failed

        # Attempt 5: Simplified Regex fallback for YYYY-MM-DD HH:MM:SS or DD/MM/YYYY HH:MM:SS
        if parsed_date is None:
            try:
                # Try YYYY-MM-DD HH:MM:SS format
                match = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", entry_date_str)
                if match:
                    date_part, time_part = match.groups()
                    parsed_date = parser.parse(f"{date_part} {time_part}")
                else:
                    # Try DD/MM/YYYY HH:MM:SS format
                    match = re.search(r"(\d{2}/\d{2}/\d{4})[ T](\d{2}:\d{2}:\d{2})", entry_date_str)
                    if match:
                        date_part, time_part = match.groups()
                        # Need dayfirst=True for DD/MM/YYYY
                        parsed_date = parser.parse(f"{date_part} {time_part}", dayfirst=True)
            except Exception:
                pass  # Regex fallback failed

        # Final check and timezone handling
        if parsed_date is not None:
            try:
                # If parsed date is naive, assume UTC
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                # Convert any aware datetime to UTC
                return parsed_date.astimezone(timezone.utc)
            except Exception as e:
                print(f"    Warning: Error converting parsed date '{parsed_date}' to UTC: {e}")
                return None  # Failed during timezone conversion

        # All attempts failed
        # print(f"    Warning: Could not parse date: '{entry_date_str}'. All attempts failed.")
        return None

    def is_recent(self, entry_date_str: Optional[str]) -> bool:
        """Check if an entry date is within the lookback period."""
        if not entry_date_str:
            return False

        published_date = self._parse_date(entry_date_str)
        if published_date is None:
            # print(f"    Could not parse date '{entry_date_str}', cannot determine recency.") # Reduced verbosity
            return False  # Cannot determine recency if date is unparseable

        cutoff = datetime.datetime.now(timezone.utc) - timedelta(days=self.days_lookback)
        return (
            published_date >= cutoff
        )  # Use >= to include items published exactly on the cutoff day

    def evaluate_article_preference(
        self, title: str, summary: str, feed_url: Optional[str] = None
    ) -> str:
        """Evaluate if an article should be processed or put in digest.

        Args:
            title: The article title.
            summary: The article summary or description.
            feed_url: The URL of the feed (for context).

        Returns:
            str: "processed" or "digest" preference.
        """
        # This now directly returns 'processed' or 'digest' based on AI eval
        # Assuming AIInterface returns "FULL" or "SUMMARY"
        preference = self.ai_interface.evaluate_article_preference(
            title=title, summary=summary, criteria=self.user_preference_criteria, feed_url=feed_url
        )
        # Map AI result to our status terms
        return "processed" if preference == "FULL" else "digest"

    def process_feed(self, feed_url: str) -> Tuple[int, int]:
        """Process a single feed: fetch entries, classify new ones, update state.

        Args:
            feed_url: The URL of the RSS feed to process.

        Returns:
            Tuple[int, int]: Number of newly processed entries, number of skipped (already processed) entries.
        """
        print(f"Processing feed: {feed_url}")
        newly_processed_count = 0
        skipped_count = 0

        feed = self.fetch_rss_feed(feed_url)
        if not feed:
            print(f"  Failed to fetch or parse feed, skipping: {feed_url}")
            return 0, 0

        print(f"  Feed Title: {feed.feed.get('title', 'N/A')}")
        print(f"  Found {len(feed.entries)} total entries in feed.")

        # Use timezone-aware datetime for comparison
        cutoff_date = datetime.datetime.now(timezone.utc) - timedelta(days=self.days_lookback)
        print(f"  Processing entries published on or after: {cutoff_date.date().isoformat()}")

        for entry in feed.entries:
            entry_title = entry.get("title", "Untitled")
            entry_date_str = entry.get("published", entry.get("updated"))
            entry_id = self.generate_entry_id(entry)

            # 1. Check if recent
            if not self.is_recent(entry_date_str):
                # print(f"    Skipping old entry: '{entry_title}' ({entry_date_str})") # Optional logging
                continue

            # 2. Check if already processed
            existing_status = self.state_manager.get_entry_status(feed_url, entry_id)

            if existing_status:
                # print(f"    Skipping already processed entry ('{existing_status}'): '{entry_title}'") # Optional logging
                skipped_count += 1
                continue

            # 3. New entry: Classify and add to state
            print(f"    Processing new entry: '{entry_title}'")
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            link = entry.get("link", "")

            # Call AI for classification
            try:
                status = self.evaluate_article_preference(
                    title=title, summary=summary, feed_url=feed_url
                )
            except Exception as e:
                print(
                    f"      Error evaluating preference for '{entry_title}': {e}. Skipping entry."
                )
                continue  # Skip this entry if AI fails

            # Prepare data for state manager
            entry_data = {
                "id": entry_id,
                "title": title,
                "link": link,
                "summary": summary,
                "date": entry_date_str,  # Store original date string
                # 'status' and 'processed_at' will be added by state_manager
            }

            # Add to state
            try:
                self.state_manager.add_processed_entry(feed_url, entry_id, status, entry_data)
                newly_processed_count += 1
                print(f"      Added entry '{entry_title}' with status: {status}")
            except Exception as e:
                print(f"      Error adding entry '{entry_title}' to state: {e}")

        print(
            f"  Finished processing feed: {feed_url}. New: {newly_processed_count}, Skipped: {skipped_count}"
        )
        return newly_processed_count, skipped_count

    def process_feeds(self, feed_urls: List[str]) -> None:
        """Process multiple feeds and save the state afterwards."""
        total_new = 0
        total_skipped = 0

        print(f"Starting processing for {len(feed_urls)} feed(s)...")

        for feed_url in feed_urls:
            try:
                new_count, skipped_count = self.process_feed(feed_url)
                total_new += new_count
                total_skipped += skipped_count
            except Exception as e:
                print(f"  *** Unhandled error processing feed {feed_url}: {e} ***")

        print(
            f"\nFinished processing all feeds. Total new: {total_new}, Total skipped: {total_skipped}"
        )

        # Save state after processing all feeds
        print("Saving state...")
        try:
            self.state_manager.save_state(days_lookback=self.days_lookback)
            print("State saved successfully.")
        except Exception as e:
            print(f"Error saving state: {e}")
