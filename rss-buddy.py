#!/usr/bin/env python3
import os
import feedparser
import datetime
from dateutil import parser
import openai
from openai import OpenAI
import xml.etree.ElementTree as ET
from email.utils import formatdate

# Import configuration
from config import RSS_FEEDS, DAYS_LOOKBACK, USER_PREFERENCE_CRITERIA, AI_MODEL, SUMMARY_MAX_TOKENS

# Set up OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
                {"role": "user", "content": f"Title: {title}\n\nContent: {content}\n\nPlease summarize this article in 2-3 sentences."}
            ],
            max_tokens=SUMMARY_MAX_TOKENS
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing article: {e}")
        return "Unable to generate summary."

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
    
    for feed_url in RSS_FEEDS:
        print(f"Processing feed: {feed_url}")
        feed = fetch_rss_feed(feed_url)
        
        if not feed:
            continue
        
        feed_title = feed.feed.get('title', 'Unknown Feed')
        feed_link = feed.feed.get('link', feed_url)
        feed_description = feed.feed.get('description', 'Processed RSS Feed')
        
        processed_entries = []
        
        for entry in feed.entries:
            # Check if entry is recent
            entry_date = entry.get('published', entry.get('updated'))
            if not is_recent(entry_date):
                continue
            
            title = entry.get('title', 'No Title')
            summary = entry.get('summary', entry.get('description', ''))
            content = entry.get('content', [{'value': summary}])[0].get('value', summary) if entry.get('content') else summary
            link = entry.get('link', '')
            
            print(f"  Evaluating: {title}")
            
            # Determine preference
            preference = evaluate_article_preference(title, summary)
            
            # Process content based on preference
            if preference == "SUMMARY":
                print(f"    Summarizing...")
                description = summarize_article(title, content)
            else:
                print(f"    Keeping in full...")
                description = content
            
            processed_entries.append({
                'title': title,
                'link': link,
                'description': description,
                'pubDate': formatdate(parser.parse(entry_date).timestamp()) if entry_date else formatdate(datetime.datetime.now().timestamp()),
                'preference': preference
            })
        
        # Create new RSS feed
        if processed_entries:
            filename = create_new_rss_feed(feed_title, feed_link, feed_description, processed_entries)
            print(f"Created processed feed: {filename} with {len(processed_entries)} entries")
        else:
            print(f"No recent entries found for {feed_title}")
    
    print("RSS processing complete!")

if __name__ == "__main__":
    process_feeds() 