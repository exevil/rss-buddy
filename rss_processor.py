#!/usr/bin/env python3
import os
import json
import feedparser
import datetime
from dateutil import parser
import openai
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
    """Get a list from environment variable, separated by commas."""
    value = os.environ.get(var_name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(',')]

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

# Configuration from environment variables
# Load defaults from config.py if available
try:
    from config import RSS_FEEDS as DEFAULT_RSS_FEEDS
    from config import USER_PREFERENCE_CRITERIA as DEFAULT_USER_PREFERENCE_CRITERIA
    from config import DAYS_LOOKBACK as DEFAULT_DAYS_LOOKBACK
    from config import AI_MODEL as DEFAULT_AI_MODEL
    from config import SUMMARY_MAX_TOKENS as DEFAULT_SUMMARY_MAX_TOKENS
except ImportError:
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

RSS_FEEDS = get_env_list('RSS_FEEDS', DEFAULT_RSS_FEEDS)
USER_PREFERENCE_CRITERIA = os.environ.get('USER_PREFERENCE_CRITERIA', DEFAULT_USER_PREFERENCE_CRITERIA)
DAYS_LOOKBACK = get_env_int('DAYS_LOOKBACK', DEFAULT_DAYS_LOOKBACK)
AI_MODEL = os.environ.get('AI_MODEL', DEFAULT_AI_MODEL)
SUMMARY_MAX_TOKENS = get_env_int('SUMMARY_MAX_TOKENS', DEFAULT_SUMMARY_MAX_TOKENS)

# Set up OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize state manager
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
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        return published_date > cutoff_date
    except Exception as e:
        print(f"Error parsing date: {e}")
        return False

def evaluate_article_preference(title, summary):
    """Use OpenAI to determine if an article should be shown in full or summarized."""
    try:
        system_prompt = f"You are an assistant that helps determine article preferences. Based on the title and summary of an article, determine if it should be shown in full or summarized based on these user preferences:\n\n{USER_PREFERENCE_CRITERIA}\n\nRespond with either 'FULL' or 'SUMMARY' only."
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {title}\n\nSummary: {summary}\n\nShould this article be shown in full or summarized?"}
            ],
            max_tokens=10
        )
        preference = response.choices[0].message.content.strip().upper()
        return "FULL" if preference == "FULL" else "SUMMARY"
    except Exception as e:
        print(f"Error determining preference: {e}")
        return "SUMMARY"  # Default to summary on error

def summarize_article(title, content):
    """Use OpenAI to generate a summary of an article."""
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes articles concisely while preserving key information."},
                {"role": "user", "content": f"Title: {title}\n\nContent: {content}\n\nPlease summarize this article in 1-2 sentences."}
            ],
            max_tokens=SUMMARY_MAX_TOKENS
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing article: {e}")
        return "Unable to generate summary."

def create_consolidated_summary(articles):
    """Create a consolidated summary of multiple articles."""
    if not articles:
        return None
    
    try:
        # Prepare a list of article summaries for OpenAI
        article_list = ""
        for i, article in enumerate(articles, 1):
            article_list += f"Article {i}: {article['title']}\n"
            article_list += f"Link: {article['link']}\n"
            article_list += f"Summary: {article['summary']}\n\n"
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are an assistant that creates a consolidated summary of multiple articles. Your task is to identify key themes and important stories, and organize them into a readable digest. Each article title you mention should be a clickable link to the original article."},
                {"role": "user", "content": f"Here are {len(articles)} articles from the past {DAYS_LOOKBACK} days that I'm less interested in but still want a brief overview of:\n\n{article_list}\n\nPlease create a consolidated summary that organizes these into themes and highlights the most noteworthy stories. Format the response as a readable digest with HTML. Each article title you mention should be wrapped in an HTML link tag pointing to its original URL (e.g., <a href='article_url'>Article Title</a>)."}
            ],
            max_tokens=SUMMARY_MAX_TOKENS * 2
        )
        
        # Collect article data for the digest
        titles_with_links = {}
        for article in articles:
            titles_with_links[article['title']] = article['link']
        
        consolidated_entry = {
            'title': f"Digest: {len(articles)} Other Stories from the Past {DAYS_LOOKBACK} Days",
            'description': response.choices[0].message.content.strip(),
            'link': articles[0]['link'] if articles else "#",  # Use link of first article or placeholder
            'pubDate': formatdate(datetime.datetime.now().timestamp()),
            'guid': f"digest-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            'consolidated': True,
            'included_articles': list(titles_with_links.keys()),
            'article_links': titles_with_links
        }
        return consolidated_entry
    except Exception as e:
        print(f"Error creating consolidated summary: {e}")
        
        # Fallback simple consolidation without OpenAI
        titles_with_links = {}
        for article in articles:
            titles_with_links[article['title']] = article['link']
        
        # Create HTML list with links
        links_html = "<ul>\n"
        for title, link in titles_with_links.items():
            links_html += f"<li><a href='{link}'>{title}</a></li>\n"
        links_html += "</ul>"
        
        description = f"<p>Summary of other stories:</p>\n{links_html}"
        
        return {
            'title': f"Digest: {len(articles)} Other Stories from the Past {DAYS_LOOKBACK} Days",
            'description': description,
            'link': articles[0]['link'] if articles else "#",
            'pubDate': formatdate(datetime.datetime.now().timestamp()),
            'guid': f"digest-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            'consolidated': True,
            'included_articles': list(titles_with_links.keys()),
            'article_links': titles_with_links
        }

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
    """Main function to process all feeds."""
    print(f"Starting RSS processing with {len(RSS_FEEDS)} feeds...")
    
    # Stats for reporting
    total_new_entries = 0
    total_processed_feeds = 0
    
    for feed_url in RSS_FEEDS:
        print(f"Processing feed: {feed_url}")
        feed = fetch_rss_feed(feed_url)
        
        if not feed:
            continue
        
        feed_title = feed.feed.get('title', 'Unknown Feed')
        feed_link = feed.feed.get('link', feed_url)
        feed_description = feed.feed.get('description', 'Processed RSS Feed')
        
        # Separate entries into full and summary categories
        full_entries = []
        summary_entries = []
        new_entry_count = 0
        
        for entry in feed.entries:
            # Generate a unique ID for this entry
            entry_id = generate_entry_id(entry)
            
            # Check if we've already processed this entry
            if state_manager.is_entry_processed(feed_url, entry_id):
                print(f"  Skipping already processed: {entry.get('title', 'No Title')}")
                continue
                
            # Check if entry is recent (as a fallback)
            entry_date = entry.get('published', entry.get('updated'))
            if not is_recent(entry_date) and state_manager.get_last_entry_date(feed_url):
                # Skip old entries if we have already processed entries for this feed
                # This prevents reprocessing all entries when the script runs for the first time
                continue
            
            title = entry.get('title', 'No Title')
            summary = entry.get('summary', entry.get('description', ''))
            content = entry.get('content', [{'value': summary}])[0].get('value', summary) if entry.get('content') else summary
            link = entry.get('link', '')
            
            print(f"  Evaluating: {title}")
            new_entry_count += 1
            
            # Determine preference
            preference = evaluate_article_preference(title, summary)
            
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
        
        # Process entries for output
        processed_entries = []
        
        # Add all full entries
        for entry in full_entries:
            processed_entries.append(entry)
        
        # Create consolidated entry for summary entries
        if summary_entries:
            consolidated_entry = create_consolidated_summary(summary_entries)
            if consolidated_entry:
                processed_entries.append(consolidated_entry)
        
        # Create new RSS feed
        if processed_entries:
            filename = create_new_rss_feed(feed_title, feed_link, feed_description, processed_entries)
            print(f"Created processed feed: {filename} with {len(processed_entries)} entries ({len(full_entries)} individual, 1 digest with {len(summary_entries)} articles)")
            total_new_entries += new_entry_count
            total_processed_feeds += 1
        else:
            print(f"No new entries found for {feed_title}")
    
    # Save the state after processing all feeds
    state_manager.save_state()
    
    print(f"RSS processing complete! Processed {total_processed_feeds} feeds with {total_new_entries} total articles.")

if __name__ == "__main__":
    process_feeds() 