"""Core RSS feed processing functionality."""
import os
import json
import hashlib
import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
import xml.etree.ElementTree as ET
from email.utils import formatdate
from datetime import timezone, timedelta

from dateutil import parser
import feedparser

from .state_manager import StateManager
from .ai_interface import AIInterface

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
            published_date = None
            # First attempt: Try standard parsing
            try:
                published_date = parser.parse(entry_date)
            except Exception as e:
                # First exception caught, continue with fallbacks
                pass
                
            # Second attempt: If first attempt failed, try with ignoretz
            if published_date is None:
                try:
                    published_date = parser.parse(entry_date, ignoretz=True)
                except Exception as e:
                    # Second exception caught, continue with more fallbacks
                    pass
            
            # Third attempt: Handle known problematic timezone abbreviations
            if published_date is None:
                # Common problematic timezone abbreviations and their approximate UTC offsets
                timezone_replacements = {
                    'PDT': '-0700', 'PST': '-0800', 
                    'EDT': '-0400', 'EST': '-0500',
                    'CEST': '+0200', 'CET': '+0100',
                    'AEST': '+1000', 'AEDT': '+1100'
                }
                
                def tzinfos(tzname):
                    return timezone_replacements.get(tzname, None)
                
                normalized_date = entry_date
                for tz, offset in timezone_replacements.items():
                    if tz in entry_date:
                        # Replace the problematic timezone with its UTC offset
                        normalized_date = entry_date.replace(tz, offset)
                        break
                
                try:
                    published_date = parser.parse(normalized_date, tzinfos=tzinfos)
                except Exception as e:
                    # Third exception caught, one final attempt with a stricter format
                    pass
            
            # Fourth attempt: Strip all timezone info and assume UTC
            if published_date is None:
                try:
                    # Extract just the date and time part without timezone
                    import re
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2} \w{3} \d{4}', entry_date)
                    time_match = re.search(r'\d{2}:\d{2}:\d{2}', entry_date)
                    
                    if date_match and time_match:
                        date_str = date_match.group(0)
                        time_str = time_match.group(0)
                        simple_date = f"{date_str} {time_str}"
                        published_date = parser.parse(simple_date)
                except Exception as e:
                    # All attempts failed
                    print(f"All parsing attempts failed for date: {entry_date} - {e}")
                    return False
            
            # All attempts failed
            if published_date is None:
                print(f"Could not parse date: {entry_date}")
                return False
            
            # Get the cutoff date, which is timezone-aware (UTC)
            cutoff_date = datetime.datetime.now(timezone.utc) - timedelta(days=days)
            
            # Ensure the published date has timezone info
            if published_date is not None and published_date.tzinfo is None:
                # If no timezone info, assume UTC
                published_date = published_date.replace(tzinfo=timezone.utc)
            
            # Now we can safely compare the dates
            return published_date is not None and published_date > cutoff_date
        except Exception as e:
            print(f"Error parsing date: {e}")
            return False
    
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
            ids = [article['guid'] for article in articles]
            # Sort IDs to ensure consistent hashing regardless of order
            ids.sort()
            
            # Create a stable content representation for hashing
            # Use only article IDs and titles, not timestamps or other changing data
            content = ""
            for article_id in ids:
                article_match = next((a for a in articles if a['guid'] == article_id), None)
                if article_match:
                    content += f"{article_id}:{article_match['title']}|"
            return ids, content
        
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
        
        # Calculate the cutoff date for recent entries
        cutoff_date = datetime.datetime.now(timezone.utc) - timedelta(days=self.days_lookback)
        
        # Process entries
        full_articles = []
        summary_articles = []
        processed_ids = set()
        
        print(f"  Found {len(feed.entries)} total entries in feed")
        
        for entry in feed.entries:
            # Get entry date
            entry_date = entry.get('published', entry.get('updated'))
            entry_id = self.generate_entry_id(entry)
            
            # Check if entry is recent
            is_recent_entry = self.is_recent(entry_date)
            status = "recent" if is_recent_entry else "old"
            print(f"  Entry: '{entry.get('title', 'Untitled')}' - Date: {entry_date} - Status: {status}")
            
            # Skip if not recent
            if not is_recent_entry:
                continue
                
            # Check if entry has been processed within lookback window
            if self.state_manager.is_entry_processed(feed_url, entry_id, self.days_lookback):
                print(f"  Already processed entry: {entry.get('title', 'Untitled')}")
                continue
                
            # Store entry data for state tracking
            entry_data = {
                "date": entry_date,
                "title": entry.get('title', 'Untitled'),
                "link": entry.get('link', ''),
                "summary": entry.get('summary', '')
            }
            
            # Evaluate article preference
            preference = self.evaluate_article_preference(
                title=entry.get('title', ''),
                summary=entry.get('summary', ''),
                feed_url=feed_url
            )
            
            if preference == "FULL":
                full_articles.append(entry)
                self.state_manager.add_processed_entry(feed_url, entry_id, entry_date, entry_data)
            else:
                summary_articles.append(entry)
                self.state_manager.add_processed_entry(feed_url, entry_id, entry_date, entry_data)
        
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
            ET.SubElement(item, 'description').text = digest_entry.get('summary', '')
            ET.SubElement(item, 'pubDate').text = digest_entry.get('published', '')
            ET.SubElement(item, 'guid').text = digest_entry.get('id', '')
        
        # Save the feed
        tree = ET.ElementTree(feed_tree)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        print(f"  Saved processed feed to {output_file} with {len(full_articles)} full articles and {1 if digest_entry else 0} digests")
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