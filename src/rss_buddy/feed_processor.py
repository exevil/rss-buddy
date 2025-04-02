"""Core RSS feed processing functionality."""
import datetime
from datetime import timedelta, timezone
from email.utils import formatdate
import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Union
import xml.etree.ElementTree as ET

from dateutil import parser
import feedparser

from .ai_interface import AIInterface
from .state_manager import StateManager


class FeedProcessor:
    """Processes RSS feeds and creates filtered outputs based on AI evaluation."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        ai_interface: Optional[AIInterface] = None,
        output_dir: str = "processed_feeds",
        days_lookback: int = 7,
        user_preference_criteria: str = "",
        summary_max_tokens: int = 150
    ):
        """Initialize the feed processor.

        Args:
            state_manager: StateManager instance to track processed articles
            ai_interface: AIInterface instance for article evaluation and summaries
            output_dir: Directory to store processed feeds
            days_lookback: Number of days to look back for articles
            user_preference_criteria: Criteria for article preference evaluation
            summary_max_tokens: Maximum tokens for summaries
        """
        self.output_dir = output_dir
        self.days_lookback = days_lookback
        self.user_preference_criteria = user_preference_criteria
        self.summary_max_tokens = summary_max_tokens

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize state manager if not provided
        self.state_manager = state_manager or StateManager(output_dir=output_dir)

        # Initialize AI interface if not provided
        self.ai_interface = ai_interface or AIInterface()

    def generate_entry_id(self, entry: Dict[str, Any]) -> str:
        """Generate a unique ID for an entry based on its link and title."""
        # Use link as primary ID if available
        entry_id = entry.get('id')
        if entry_id:
            return entry_id

        entry_link = entry.get('link')
        if entry_link:
            return entry_link
        else:
            # Create a hash from title and content if no ID or link
            content = entry.get('summary', '') + entry.get('title', '')
            return hashlib.md5(content.encode('utf-8')).hexdigest()

    def fetch_rss_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse an RSS feed from the given URL."""
        try:
            return feedparser.parse(url)
        except Exception as e:
            print(f"Error fetching feed {url}: {e}")
            return None

    def is_recent(self, entry_date: Optional[str], days: int = None) -> bool:
        """Check if an entry is from within the specified number of days."""
        if not entry_date:
            return False

        days = days or self.days_lookback

        try:
            published_date = self._parse_date(entry_date)

            # All attempts failed
            if published_date is None:
                print(f"Could not parse date: {entry_date}")
                return False

            # Get the cutoff date, which is timezone-aware (UTC)
            cutoff = datetime.datetime.now(timezone.utc) - timedelta(days=days)

            # Ensure the published date has timezone info
            if published_date is not None and published_date.tzinfo is None:
                # If no timezone info, assume UTC
                published_date = published_date.replace(tzinfo=timezone.utc)

            # Now we can safely compare the dates
            return published_date is not None and published_date > cutoff
        except Exception as e:
            print(f"Error parsing date: {e}")
            return False

    def _parse_date(self, entry_date: str) -> Optional[datetime.datetime]:
        """Parse a date string using multiple fallback methods.
       
        Tries several approaches to parse problematic date formats:
        1. Standard parsing with timezone info
        2. Parsing without timezone info
        3. Special handling for timezone abbreviations
        4. Extracting date and time parts separately
       
        Returns:
            datetime.datetime or None: Parsed date or None if parsing failed
        """
        # Common problematic timezone abbreviations and their approximate UTC offsets
        timezone_replacements = {
            'PDT': '-0700', 'PST': '-0800',
            'EDT': '-0400', 'EST': '-0500',
            'CEST': '+0200', 'CET': '+0100',
            'AEST': '+1000', 'AEDT': '+1100'
        }

        def tzinfos(tzname, offset):
            return timezone_replacements.get(tzname, None)

        # Try each parsing method in sequence
        return (
            self._try_standard_parsing(entry_date, tzinfos)
            or self._try_ignoretz_parsing(entry_date)
            or self._try_timezone_replacement_parsing(
                entry_date, timezone_replacements, tzinfos
            )
            or self._try_regex_parsing(entry_date, tzinfos)
        )

    def _try_standard_parsing(self, entry_date: str, tzinfos_func) -> Optional[datetime.datetime]:
        """Attempt to parse date with standard parsing."""
        try:
            parsed_date = parser.parse(entry_date, tzinfos=tzinfos_func)
            # Ensure timezone-aware, default to UTC
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date
        except Exception:
            # First exception caught, continue with fallbacks
            return None

    def _try_ignoretz_parsing(self, entry_date: str) -> Optional[datetime.datetime]:
        """Attempt to parse date ignoring timezone info."""
        try:
            # Parse ignoring timezone, then assume UTC
            parsed_date = parser.parse(entry_date, ignoretz=True)
            return parsed_date.replace(tzinfo=timezone.utc)
        except Exception:
            # Second exception caught, continue with more fallbacks
            return None

    def _try_timezone_replacement_parsing(
        self, entry_date: str, replacements: Dict[str, str], tzinfos_func
    ) -> Optional[datetime.datetime]:
        """Attempt to parse date by replacing timezone abbreviations."""
        try:
            normalized_date = entry_date
            for tz, offset in replacements.items():
                if tz in entry_date:
                    # Replace the problematic timezone with its UTC offset
                    normalized_date = entry_date.replace(tz, offset)
                    break

            parsed_date = parser.parse(normalized_date, tzinfos=tzinfos_func)
            # Ensure timezone-aware, default to UTC
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date
        except Exception:
            # Third exception caught, one final attempt with a stricter format
            return None

    def _try_regex_parsing(self, entry_date: str, tzinfos_func) -> Optional[datetime.datetime]:
        """Attempt to parse date using regex to extract date and time separately."""
        try:
            # More flexible regex to find date and time patterns within text
            # Date patterns: YYYY-MM-DD (G1), DD/MM/YYYY (G2), DD Mon YYYY (G3)
            date_pattern = r'(\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4})|(\d{2} \w{3} \d{4})'
            # Time pattern: HH:MM:SS (G1)
            time_pattern = r'(\d{2}:\d{2}:\d{2})'
            
            date_match = re.search(date_pattern, entry_date)
            time_match = re.search(time_pattern, entry_date)

            if date_match and time_match:
                # Determine which date pattern matched
                date_str = None
                day_first = False
                if date_match.group(1):  # YYYY-MM-DD
                    date_str = date_match.group(1)
                elif date_match.group(2):  # DD/MM/YYYY
                    date_str = date_match.group(2)
                    day_first = True  # Ambiguous, assume day first
                elif date_match.group(3):  # DD Mon YYYY
                    date_str = date_match.group(3)
                    day_first = True  # Explicitly day first
                
                time_str = time_match.group(1)  # time_pattern only has one group

                if date_str and time_str:
                    # Combine extracted date and time
                    simple_date = f"{date_str} {time_str}"
                    # Parse simplified date, assume UTC, respect dayfirst if needed
                    parsed_date = parser.parse(
                        simple_date, 
                        tzinfos=tzinfos_func, 
                        dayfirst=day_first
                    )
                    return parsed_date.replace(tzinfo=timezone.utc)
            return None
        except Exception as e:
            # All attempts failed
            print(f"All parsing attempts failed for date: {entry_date} - {e}")
            return None

    def evaluate_article_preference(
        self,
        title: str,
        summary: str,
        feed_url: Optional[str] = None
    ) -> str:
        """Evaluate if an article should be shown in full or summarized.

        Args:
            title: The article title
            summary: The article summary or description
            feed_url: The URL of the feed (for context)

        Returns:
            str: "FULL" or "SUMMARY" preference
        """
        return self.ai_interface.evaluate_article_preference(
            title=title,
            summary=summary,
            criteria=self.user_preference_criteria,
            feed_url=feed_url
        )

    def create_consolidated_summary(
        self,
        articles: List[Dict[str, Any]],
        feed_url: str
    ) -> Optional[Dict[str, Any]]:
        """Create a consolidated summary of multiple articles.

        Args:
            articles: List of article dictionaries to consolidate
            feed_url: The URL of the feed (used for state tracking)

        Returns:
            dict: Consolidated entry dictionary or None if no articles
        """
        if not articles:
            print("  No articles for digest, skipping digest creation")
            return None

        # Helper function to create stable content hash
        def create_stable_content():
            # Get article IDs for state tracking
            article_list_ids = [article['guid'] for article in articles]
            # Sort IDs to ensure consistent hashing regardless of order
            article_list_ids.sort()

            # Create a stable content representation for hashing
            # Use only article IDs and titles, not timestamps or other changing data
            content = ""
            for article_id in article_list_ids:
                article_match = next(
                    (a for a in articles if a['guid'] == article_id), None
                )
                if article_match:
                    content += f"{article_id}:{article_match['title']}|"
            return article_list_ids, content

        # Generate content hash for state tracking
        article_ids, content_hash_data = create_stable_content()

        # Generate the digest content
        digest_content = self.ai_interface.generate_consolidated_summary(
            articles=articles,
            max_tokens=self.summary_max_tokens
        )

        if not digest_content:
            print("  Failed to generate digest content")
            return None

        # Update digest state and get ID
        digest_id, is_updated = self.state_manager.update_digest_state(
            feed_url=feed_url,
            article_ids=article_ids,
            content=content_hash_data
        )

        # Update processed state of included articles
        now_iso = datetime.datetime.now().isoformat()
        for article in articles:
            self.state_manager.add_processed_entry(
                feed_url=feed_url,
                entry_id=article['guid'],
                entry_date=now_iso
            )

        # Create digest entry
        digest_date = formatdate()
        digest_title = f"RSS Buddy Digest: {len(articles)} Less Important Articles"

        # Only create a new digest entry if the content has changed or no digest existed
        if is_updated:
            print(f"  Content changed, creating new digest ({digest_id})")
            return {
                'title': digest_title,
                'link': f"https://digest.example.com/{digest_id}",
                'guid': digest_id,
                'pubDate': digest_date,
                'description': digest_content,
                'is_digest': True
            }
        else:
            print(f"  Content unchanged, using existing digest ID ({digest_id})")
            return None  # No need to update the digest

    def process_feed(self, feed_url: str) -> Union[str, None]:
        """Process a feed, evaluating articles and creating filtered RSS files.

        Args:
            feed_url: The URL of the RSS feed to process

        Returns:
            str: Path to the processed feed file or None if processing failed
        """
        print(f"Processing feed: {feed_url}")

        # Fetch the feed
        feed = self.fetch_rss_feed(feed_url)
        if not feed:
            print(f"  Failed to fetch feed: {feed_url}")
            return None

        print(f"  Feed: {feed.feed.get('title')}")

        # Calculate the cutoff date for recent entries (used for logging/debugging)
        cutoff_date = datetime.datetime.now(timezone.utc) - timedelta(days=self.days_lookback)
        print(f"  Using cutoff date: {cutoff_date.isoformat()}")

        # Process entries
        full_articles = []
        summary_articles = []

        print(f"  Found {len(feed.entries)} total entries in feed")

        for entry in feed.entries:
            # Get entry date
            entry_date = entry.get('published', entry.get('updated'))
            entry_id = self.generate_entry_id(entry)

            # Check if entry is recent
            is_recent_entry = self.is_recent(entry_date)
            status = "recent" if is_recent_entry else "old"
            print(
                f"  Entry: '{entry.get('title', 'Untitled')}' - "
                f"Date: {entry_date} - Status: {status}"
            )

            # Skip if not recent
            if not is_recent_entry:
                continue

            # Store entry data for state tracking
            entry_data = {
                "date": entry_date,
                "title": entry.get('title', 'Untitled'),
                "link": entry.get('link', ''),
                "summary": entry.get('summary', '')
            }

            # Check if entry has been processed within lookback window
            if self.state_manager.is_entry_processed(
                feed_url, entry_id, self.days_lookback
            ):
                print(f"  Already processed entry: {entry.get('title', 'Untitled')}")

                # Get the stored entry data if available
                stored_data = self.state_manager.get_entry_data(feed_url, entry_id)
                if stored_data and "preference" in stored_data:
                    # Use the stored preference to determine category
                    if stored_data["preference"] == "FULL":
                        full_articles.append(entry)
                    else:
                        summary_articles.append(entry)
                continue

            # Evaluate article preference
            preference = self.evaluate_article_preference(
                title=entry.get('title', ''),
                summary=entry.get('summary', ''),
                feed_url=feed_url
            )

            # Add preference to the entry data
            entry_data["preference"] = preference

            if preference == "FULL":
                full_articles.append(entry)
                self.state_manager.add_processed_entry(
                    feed_url, entry_id, entry_date, entry_data
                )
            else:
                summary_articles.append(entry)
                self.state_manager.add_processed_entry(
                    feed_url, entry_id, entry_date, entry_data
                )

        # Create consolidated summary if needed
        digest_entry = None
        if summary_articles:
            print(f"  Summarized article: {summary_articles[0].get('title', 'Untitled')}")
            digest_entry = self.create_consolidated_summary(summary_articles, feed_url)

        # Create output feed
        output_file = os.path.join(self.output_dir, f"{feed.feed.get('title')}.xml")

        # Create feed tree
        feed_tree = ET.Element('rss')
        feed_tree.set('version', '2.0')

        channel = ET.SubElement(feed_tree, 'channel')

        # Add feed metadata
        ET.SubElement(channel, 'title').text = f"{feed.feed.get('title')} (Filtered)"
        ET.SubElement(channel, 'link').text = feed_url
        ET.SubElement(channel, 'description').text = f"Filtered version of {feed.feed.get('title')}"
        ET.SubElement(channel, 'lastBuildDate').text = formatdate()

        # Add full articles
        for entry in full_articles:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = entry.get('title', '')
            ET.SubElement(item, 'link').text = entry.get('link', '')
            ET.SubElement(item, 'description').text = entry.get('summary', '')
            ET.SubElement(item, 'pubDate').text = entry.get('published', entry.get('updated', ''))
            ET.SubElement(item, 'guid').text = self.generate_entry_id(entry)

        # Add digest if available
        if digest_entry:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = digest_entry.get('title', '')
            ET.SubElement(item, 'link').text = digest_entry.get('link', '')
            ET.SubElement(item, 'description').text = digest_entry.get('description', '')
            ET.SubElement(item, 'pubDate').text = digest_entry.get('pubDate', '')
            ET.SubElement(item, 'guid').text = digest_entry.get('guid', '')

        # Save the feed
        tree = ET.ElementTree(feed_tree)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(
            f"  Saved processed feed to {output_file} with "
            f"{len(full_articles)} full articles and {1 if digest_entry else 0} digests"
        )
        return output_file

    def process_feeds(self, feed_urls: List[str]) -> List[str]:
        """Process multiple feeds.

        Args:
            feed_urls: List of feed URLs to process

        Returns:
            List[str]: Paths to the processed feed files
        """
        processed_files = []

        for feed_url in feed_urls:
            output_path = self.process_feed(feed_url)
            if output_path:
                processed_files.append(output_path)

        return processed_files
