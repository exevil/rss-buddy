#!/usr/bin/env python3
import os
import json
import feedparser
import datetime
from dateutil import parser
from openai import OpenAI
import xml.etree.ElementTree as ET
from email.utils import formatdate
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Import the state manager
from state_manager import StateManager

# Read configuration from environment variables
def get_env_list(var_name, default=None):
    """Get a list from environment variable, separated by newlines."""
    value = os.environ.get(var_name)
    if not value:
        return default or []
    
    # Split by newlines and filter out empty items
    return [item.strip() for item in value.split('\n') if item.strip()]

def get_env_int(var_name, default):
    """Get an integer from environment variable."""
    value = os.environ.get(var_name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        print(f"Warning: Could not parse {var_name} as integer, using default {default}")
        return default

# Default configuration values
DEFAULT_RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://www.wired.com/feed/rss"
]

DEFAULT_USER_PREFERENCE_CRITERIA = """
When determining if an article should be shown in full or summarized, consider these factors:
- Technical deep dives in machine learning, AI, and quantum computing should be shown in FULL
- Breaking news about major tech companies should be shown in FULL
- General technology news can be SUMMARIZED
"""

DEFAULT_DAYS_LOOKBACK = 7
DEFAULT_AI_MODEL = "gpt-4"
DEFAULT_SUMMARY_MAX_TOKENS = 150

# Get configuration from environment variables, falling back to defaults
RSS_FEEDS = get_env_list('RSS_FEEDS', DEFAULT_RSS_FEEDS)
USER_PREFERENCE_CRITERIA = os.environ.get('USER_PREFERENCE_CRITERIA', DEFAULT_USER_PREFERENCE_CRITERIA)
DAYS_LOOKBACK = get_env_int('DAYS_LOOKBACK', DEFAULT_DAYS_LOOKBACK)
AI_MODEL = os.environ.get('AI_MODEL', DEFAULT_AI_MODEL)
SUMMARY_MAX_TOKENS = get_env_int('SUMMARY_MAX_TOKENS', DEFAULT_SUMMARY_MAX_TOKENS)

# Set up OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize state manager
# Note: When running in GitHub Actions, state file is downloaded from GitHub Pages
# before execution, and will be uploaded back to GitHub Pages after processing
state_manager = StateManager()

def generate_entry_id(entry):
    """Generate a unique ID for an entry based on its link and title."""
    # Use link as primary ID if available
    if entry.get('id'):
        return entry['id']
    elif entry.get('link'):
        return entry['link']
    else:
        # Create a hash from title and content if no ID or link
        content = entry.get('summary', '') + entry.get('title', '')
        return hashlib.md5(content.encode('utf-8')).hexdigest()

def fetch_rss_feed(url):
    """Fetch and parse an RSS feed from the given URL."""
    try:
        return feedparser.parse(url)
    except Exception as e:
        print(f"Error fetching feed {url}: {e}")
        return None

def is_recent(entry_date, days=DAYS_LOOKBACK):
    """Check if an entry is from within the specified number of days."""
    if not entry_date:
        return False
    
    try:
        published_date = parser.parse(entry_date)
        cutoff_date = state_manager.get_recent_cutoff_date(days)
        return published_date > cutoff_date
    except Exception as e:
        print(f"Error parsing date: {e}")
        return False

def evaluate_article_preference(title, summary, feed_url=None):
    """Use OpenAI to determine if an article should be shown in full or summarized.
    
    Args:
        title: The article title
        summary: The article summary or description
        feed_url: The URL of the feed (for context in preference decisions)
        
    Returns:
        str: "FULL" or "SUMMARY" preference
    """
    try:
        # Create a feed source for better context
        feed_source = ""
        if feed_url:
            # Extract domain from feed URL for context
            from urllib.parse import urlparse
            parsed_url = urlparse(feed_url)
            domain = parsed_url.netloc
            feed_source = f"\nSource: {domain}"
            
        system_prompt = f"You are an assistant that helps determine article preferences. Based on the title, summary, and source of an article, determine if it should be shown in full or summarized based on these user preferences:\n\n{USER_PREFERENCE_CRITERIA}\n\nRespond with either 'FULL' or 'SUMMARY' only."
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {title}\n\nSummary: {summary}{feed_source}\n\nShould this article be shown in full or summarized?"}
            ],
            max_tokens=10
        )
        preference = response.choices[0].message.content.strip().upper()
        return "FULL" if preference == "FULL" else "SUMMARY"
    except Exception as e:
        print(f"Error determining preference: {e}")
        return "SUMMARY"  # Default to summary on error

def create_consolidated_summary(articles, feed_url):
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
    
    # Helper function to create title-link mapping
    def create_title_links_map():
        titles_map = {}
        for article in articles:
            titles_map[article['title']] = article['link']
        return titles_map
    
    # Helper function to create article list for OpenAI
    def create_article_list():
        result = ""
        for i, article in enumerate(articles, 1):
            result += f"Article {i}: {article['title']}\n"
            result += f"Link: {article['link']}\n"
            result += f"Summary: {article['summary']}\n\n"
        return result
    
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
    
    # Helper function to generate digest with OpenAI
    def generate_digest_content(article_list_str):
        try:
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an assistant that creates a consolidated summary of multiple articles. Your task is to identify key themes and important stories, and organize them into a readable digest. Each article title you mention should be a clickable link to the original article."},
                    {"role": "user", "content": f"Here are {len(articles)} articles from the past {DAYS_LOOKBACK} days that I'm less interested in but still want a brief overview of:\n\n{article_list_str}\n\nPlease create a consolidated summary that organizes these into themes and highlights the most noteworthy stories. Format the response as a readable digest with HTML. Each article title you mention should be wrapped in an HTML link tag pointing to its original URL (e.g., <a href='article_url'>Article Title</a>)."}
                ],
                max_tokens=SUMMARY_MAX_TOKENS * len(articles)
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating digest with OpenAI: {e}")
            # Create simple HTML list as fallback
            links_html = "<ul>\n"
            for title, link in create_title_links_map().items():
                links_html += f"<li><a href='{link}'>{title}</a></li>\n"
            links_html += "</ul>"
            return f"<p>Summary of other stories:</p>\n{links_html}"
    
    # Helper function to create final digest entry
    def create_digest_entry(digest_id, content):
        return {
            'title': f"[RSS Buddy]: {len(articles)} Stories from the Past {DAYS_LOOKBACK} Days",
            'description': content,
            'link': articles[0]['link'] if articles else "#",
            'pubDate': formatdate(datetime.datetime.now().timestamp()),
            'guid': digest_id,
            'consolidated': True,
            'included_articles': list(create_title_links_map().keys()),
            'article_links': create_title_links_map()
        }
    
    try:
        # Create stable content for hashing
        article_ids, stable_content = create_stable_content()
        
        # Create article list for OpenAI
        article_list = create_article_list()
        
        # Check if digest would be unchanged from previous state
        existing_digest_articles = state_manager.get_articles_in_digest(feed_url)
        existing_digest_articles.sort()
        
        # If the article IDs are exactly the same, we can reuse the existing digest ID
        if set(article_ids) == set(existing_digest_articles):
            digest_id = state_manager.get_processed_entries(feed_url)["digest"]["id"]
            # If we have an existing digest ID, we can reuse it
            if digest_id:
                print(f"  Digest content unchanged (same articles), keeping existing ID: {digest_id}")
                
                # Generate digest content
                digest_content = generate_digest_content(article_list)
                
                # Return the entry with the existing digest ID
                return create_digest_entry(digest_id, digest_content)
        
        # For new or changed digests, create a new summary
        digest_content = generate_digest_content(article_list)
        
        # Update digest state using our stable content string
        digest_id, is_updated = state_manager.update_digest_state(feed_url, article_ids, stable_content)
        
        if is_updated:
            print(f"  Digest content changed, generating new digest with ID: {digest_id}")
        else:
            print(f"  Digest content unchanged, keeping existing ID: {digest_id}")
        
        # Create and return the digest entry
        return create_digest_entry(digest_id, digest_content)
        
    except Exception as e:
        print(f"Error creating consolidated summary: {e}")
        
        # Fall back to simple digest if something fails
        article_ids, stable_content = create_stable_content()
        digest_id, _ = state_manager.update_digest_state(feed_url, article_ids, ",".join(article_ids))
        
        # Create simple HTML content as fallback
        simple_content = generate_digest_content("")
        
        return create_digest_entry(digest_id, simple_content)

def create_new_rss_feed(feed_title, feed_link, feed_description, entries):
    """Create a new RSS feed with processed entries."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    # Add channel metadata
    title_elem = ET.SubElement(channel, "title")
    title_elem.text = f"{feed_title} (Processed)"
    
    link_elem = ET.SubElement(channel, "link")
    link_elem.text = feed_link
    
    desc_elem = ET.SubElement(channel, "description")
    desc_elem.text = f"Processed feed: {feed_description}"
    
    # Add processing timestamp
    last_build_date = ET.SubElement(channel, "lastBuildDate")
    last_build_date.text = formatdate(datetime.datetime.now().timestamp())
    
    # Add each entry
    for entry in entries:
        item = ET.SubElement(channel, "item")
        
        item_title = ET.SubElement(item, "title")
        item_title.text = entry['title']
        
        item_link = ET.SubElement(item, "link")
        item_link.text = entry['link']
        
        item_desc = ET.SubElement(item, "description")
        item_desc.text = entry['description']
        
        if 'pubDate' in entry:
            pub_date = ET.SubElement(item, "pubDate")
            pub_date.text = entry['pubDate']
        
        if 'preference' in entry:
            pref = ET.SubElement(item, "preference")
            pref.text = entry['preference']
            
        if 'guid' in entry:
            guid = ET.SubElement(item, "guid")
            guid.text = entry['guid']
            guid.set("isPermaLink", "false")
            
        if 'consolidated' in entry and entry['consolidated']:
            consolidated = ET.SubElement(item, "consolidated")
            consolidated.text = "true"
            
            if 'included_articles' in entry:
                included = ET.SubElement(item, "includedArticles")
                included.text = ", ".join(entry['included_articles'])
                
            if 'article_links' in entry and entry['article_links']:
                links_elem = ET.SubElement(item, "articleLinks")
                # Store as JSON to preserve structure
                links_elem.text = json.dumps(entry['article_links'])
    
    # Create XML tree and convert to string
    tree = ET.ElementTree(rss)
    
    # Create output directory if it doesn't exist
    output_dir = "processed_feeds"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate safe filename from feed title
    safe_filename = ''.join(c if c.isalnum() else '_' for c in feed_title)
    filename = f"{output_dir}/{safe_filename}_processed.xml"
    
    tree.write(filename, encoding="UTF-8", xml_declaration=True)
    return filename

def process_feeds():
    """Main function to process all RSS feeds."""
    print(f"Starting RSS processing with {DAYS_LOOKBACK} days lookback...")
    
    total_processed_feeds = 0
    total_new_entries = 0
    
    # Process each RSS feed
    for feed_url in RSS_FEEDS:
        print(f"\nProcessing feed: {feed_url}")
        
        # Fetch the feed
        feed = fetch_rss_feed(feed_url)
        if not feed:
            print(f"  Error: Could not fetch feed {feed_url}, skipping")
            continue
        
        # Get feed info
        feed_title = feed.feed.get('title', 'Untitled Feed')
        feed_link = feed.feed.get('link', feed_url)
        feed_description = feed.feed.get('description', 'No Description')
        
        print(f"  Title: {feed_title}")
        
        # Lists to store entries
        full_entries = []
        summary_entries = []
        new_entry_count = 0
        already_processed_count = 0
        
        # Cutoff date for recent entries
        cutoff_date = state_manager.get_recent_cutoff_date(DAYS_LOOKBACK)
        print(f"  Looking for entries newer than: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get existing digest articles
        existing_digest_articles = state_manager.get_articles_in_digest(feed_url)
        
        # Process each entry
        for entry in feed.entries:
            # Generate a unique ID for the entry
            entry_id = generate_entry_id(entry)
            
            # Get the entry date
            entry_date = entry.get('published', entry.get('updated'))
            
            # Skip if entry is already processed
            if state_manager.is_entry_processed(feed_url, entry_id):
                already_processed_count += 1
                
                # Check if the entry should be reconsidered for the digest
                # We need to check if it's within our lookback window, regardless of whether
                # it was processed before
                if entry_date and is_recent(entry_date, DAYS_LOOKBACK):
                    title = entry.get('title', 'No Title')
                    summary = entry.get('summary', entry.get('description', ''))
                    content = entry.get('content', [{'value': summary}])[0].get('value', summary) if entry.get('content') else summary
                    link = entry.get('link', '')
                    
                    # Format the date for the RSS feed
                    formatted_date = formatdate(parser.parse(entry_date).timestamp()) if entry_date else formatdate(datetime.datetime.now().timestamp())
                    
                    # Determine if this was previously added to digest
                    preference = "FULL"
                    if entry_id in existing_digest_articles:
                        preference = "SUMMARY"
                    
                    # Create entry dict with common fields
                    entry_dict = {
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'content': content,
                        'pubDate': formatted_date,
                        'preference': preference,
                        'guid': entry_id
                    }
                    
                    # Add to appropriate list but don't double-count
                    if preference == "FULL":
                        entry_dict['description'] = content
                        full_entries.append(entry_dict)
                    else:
                        summary_entries.append(entry_dict)
                
                continue
                
            # For entries not already processed:
            
            # Check if entry is recent (within lookback days)
            if not is_recent(entry_date, DAYS_LOOKBACK):
                continue
            
            title = entry.get('title', 'No Title')
            summary = entry.get('summary', entry.get('description', ''))
            content = entry.get('content', [{'value': summary}])[0].get('value', summary) if entry.get('content') else summary
            link = entry.get('link', '')
            
            print(f"  Evaluating: {title}")
            new_entry_count += 1
            
            # Determine preference
            preference = evaluate_article_preference(title, summary, feed_url)
            
            # Format the date for the RSS feed
            formatted_date = formatdate(parser.parse(entry_date).timestamp()) if entry_date else formatdate(datetime.datetime.now().timestamp())
            
            # Create entry dict with common fields
            entry_dict = {
                'title': title,
                'link': link,
                'summary': summary,  # Keep original summary for potential consolidation
                'content': content,  # Keep original content for potential full display
                'pubDate': formatted_date,
                'preference': preference,
                'guid': entry_id
            }
            
            # Add to appropriate list
            if preference == "FULL":
                print(f"    Keeping in full...")
                entry_dict['description'] = content
                full_entries.append(entry_dict)
            else:
                print(f"    Adding to summary digest...")
                # Just add to summary entries list - we'll consolidate later
                summary_entries.append(entry_dict)
            
            # Mark this entry as processed in our state manager
            state_manager.add_processed_entry(feed_url, entry_id, entry_date)
        
        print(f"  Found {new_entry_count} new entries, {already_processed_count} already processed entries")
        print(f"  Entries for full display: {len(full_entries)}")
        print(f"  Entries for digest: {len(summary_entries)}")
        
        # Process entries for output
        processed_entries = []
        
        # Add all full entries
        for entry in full_entries:
            processed_entries.append(entry)
        
        # Create consolidated entry for summary entries
        if summary_entries:
            consolidated_entry = create_consolidated_summary(summary_entries, feed_url)
            if consolidated_entry:
                processed_entries.append(consolidated_entry)
        
        # Create new RSS feed
        if processed_entries:
            filename = create_new_rss_feed(feed_title, feed_link, feed_description, processed_entries)
            if summary_entries:
                print(f"Created processed feed: {filename} with {len(processed_entries)} entries ({len(full_entries)} individual, 1 digest with {len(summary_entries)} articles)")
            else:
                print(f"Created processed feed: {filename} with {len(processed_entries)} entries ({len(full_entries)} individual, no digest)")
            total_new_entries += new_entry_count
            total_processed_feeds += 1
        else:
            print(f"No entries found for {feed_title}")
    
    # Save the state after processing all feeds
    state_manager.save_state()
    
    print(f"RSS processing complete! Processed {total_processed_feeds} feeds with {total_new_entries} total new articles.")

if __name__ == "__main__":
    process_feeds() 