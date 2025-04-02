#!/usr/bin/env python3
"""Module for generating HTML pages from processed RSS feeds for display on GitHub Pages."""
from datetime import datetime
import html
import json
import os
import shutil
import xml.etree.ElementTree as ET

from dateutil import parser

# Define timezone information
TZINFOS = {
    'PDT': -7 * 3600,
    'PST': -8 * 3600,
    'EDT': -4 * 3600,
    'EST': -5 * 3600,
    'CEST': 2 * 3600,
    'CET': 1 * 3600,
    'AEST': 10 * 3600,
    'AEDT': 11 * 3600,
}


def create_html_header(title):
    """Create the HTML header section with styles.
    
    Args:
        title: The title to use in the page
        
    Returns:
        str: HTML header content
    """
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, 
            sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{ border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        h2 {{ margin-top: 30px; color: #333; }}
        h3 {{ margin-top: 20px; color: #555; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .article {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }}
        .digest {{
            margin: 30px 0;
            padding: 20px;
            background-color: #e6f7ff;
            border-left: 4px solid #1890ff;
            border-radius: 5px;
        }}
        .article-meta {{
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 10px;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            padding: 5px 10px;
            background-color: #f0f0f0;
            border-radius: 3px;
        }}
        .feed-description {{
            font-size: 0.9rem;
            color: #666;
            margin-top: 5px;
        }}
        .updated {{
            font-size: 0.8rem;
            color: #888;
            margin-top: 5px;
        }}
        .state-info {{
            margin-top: 20px;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
            font-size: 0.9rem;
        }}
        .explanation {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
            border-left: 4px solid #4caf50;
        }}
        .article-links {{
            margin-top: 15px;
            padding: 10px;
            background-color: #f0f8ff;
            border-radius: 5px;
        }}
    </style>
</head>'''


def create_index_html_start():
    """Create the start of the index HTML file.
    
    Returns:
        str: HTML content for the start of the index page
    """
    html_content = create_html_header("rss-buddy processed feeds")
    html_content += '''
<body>
    <h1>rss-buddy Processed Feeds</h1>
    
    <div class="explanation">
        <p>These feeds are processed with AI to prioritize content:</p>
        <ul style="list-style-type: disc; padding-left: 20px;">
            <li><strong>Important articles</strong> are shown individually in full</li>
            <li><strong>Other articles</strong> are consolidated into a single digest item 
            (highlighted in blue)</li>
        </ul>
    </div>
    
    <p>Below are the processed RSS feeds with AI-enhanced organization:</p>
    <ul>
'''
    return html_content


def create_feed_html_start(title, description, last_build_date):
    """Create the start of a feed HTML file.
    
    Args:
        title: Feed title
        description: Feed description
        last_build_date: Last build date string
        
    Returns:
        str: HTML content for the start of a feed page
    """
    html_content = create_html_header(title)
    html_content += f'''
<body>
    <a href="index.html" class="back-link">← Back to all feeds</a>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(description)}</p>
    <p><small>Last updated: {html.escape(last_build_date)}</small></p>
    
    <div>
'''
    return html_content


def process_digest_item(item, item_link, item_title, item_date, item_desc):
    """Process a digest item and return its HTML representation.
    
    Args:
        item: The XML item element
        item_link: Link to the item
        item_title: Title of the item
        item_date: Publication date
        item_desc: Item description
        
    Returns:
        str: HTML for the digest item
    """
    feed_html = f'''
        <div class="digest">
            <h2><a href="{html.escape(item_link)}">{html.escape(item_title)}</a></h2>
            <div class="article-meta">{html.escape(item_date)}</div>
            <div>{item_desc}</div>
'''

    # Try to get article links from the item
    article_links = {}
    try:
        article_links_elem = item.find('articleLinks')
        if article_links_elem is not None and article_links_elem.text:
            article_links = json.loads(article_links_elem.text)
    except Exception:
        pass

    # If we have article links but they're not in the description, add them
    if article_links and '<a href' not in item_desc:
        feed_html += '''
            <div class="article-links">
                <h3>Included Articles:</h3>
                <ul>
'''
        for title, link in article_links.items():
            feed_html += (
                f'                    <li><a href="{html.escape(link)}">'
                f'{html.escape(title)}</a></li>\n'
            )
        feed_html += '''
                </ul>
            </div>
'''

    feed_html += '''
        </div>
'''
    return feed_html


def process_regular_item(item_link, item_title, item_date, item_desc):
    """Process a regular item and return its HTML representation.
    
    Args:
        item_link: Link to the item
        item_title: Title of the item
        item_date: Publication date
        item_desc: Item description
        
    Returns:
        str: HTML for the regular item
    """
    return f'''
        <div class="article">
            <h2><a href="{html.escape(item_link)}">{html.escape(item_title)}</a></h2>
            <div class="article-meta">{html.escape(item_date)}</div>
            <div>{item_desc}</div>
        </div>
'''


def parse_feed_file(file_path):
    """Parse an RSS feed file and return the root element.
    
    Args:
        file_path: Path to the XML feed file
        
    Returns:
        tuple: (root_element, channel_element) or (None, None) if parsing fails
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        channel = root.find('channel')
        return root, channel
    except Exception as e:
        print(f"Error parsing feed file {file_path}: {e}")
        return None, None


def get_channel_info(channel):
    """Extract information from a channel element.
    
    Args:
        channel: The XML channel element
        
    Returns:
        tuple: (title, link, description, last_build_date)
    """
    if channel is None:
        return (
            'Untitled Feed',
            '#',
            'No description',
            datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        )
    
    title = channel.find('title').text if channel.find('title') is not None else 'Untitled Feed'
    link = channel.find('link').text if channel.find('link') is not None else '#'
    description = (
        channel.find('description').text
        if channel.find('description') is not None
        else 'No description'
    )
    last_build_date = (
        channel.find('lastBuildDate').text
        if channel.find('lastBuildDate') is not None
        else ''
    )
    
    # Default to current time if no build date
    if not last_build_date:
        last_build_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    return title, link, description, last_build_date


def process_feeds(input_dir, output_dir, state_file):
    """Process feed files and generate HTML pages.
    
    Args:
        input_dir: Directory containing the processed XML feeds
        output_dir: Directory to output the GitHub Pages files
        state_file: Path to the state file
        
    Returns:
        tuple: (feeds_list, html_content) - feeds data and index HTML content
    """
    feeds_list = []
    html_content = create_index_html_start()
    
    if not (os.path.exists(input_dir) and os.path.isdir(input_dir)):
        return feeds_list, html_content
    
    for file in os.listdir(input_dir):
        if not file.endswith('.xml'):
            continue
            
        file_path = os.path.join(input_dir, file)
        root, channel = parse_feed_file(file_path)
        
        if channel is None:
            continue
        
        title, link, description, last_build_date = get_channel_info(channel)
        
        # Get item counts
        items = channel.findall('item')
        regular_count = 0
        digest_count = 0
        
        # Create detailed HTML feed page
        feed_html = create_feed_html_start(title, description, last_build_date)
        
        for item in items:
            # Get the title element and its text, defaulting to 'Untitled Item' if not found
            title_element = item.find('title')
            item_title = title_element.text if title_element is not None else 'Untitled Item'
            item_link = item.find('link').text if item.find('link') is not None else '#'
            description_element = item.find('description')
            item_desc = description_element.text if description_element is not None else ''
            pub_date = item.find('pubDate')
            
            item_date = ''
            if pub_date is not None and pub_date.text:
                try:
                    parsed_date = parser.parse(pub_date.text, tzinfos=TZINFOS)
                    item_date = parsed_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                except Exception as e:
                    print(f"Error parsing date: {e}")
            
            is_consolidated = (
                item.find('consolidated') is not None
                and item.find('consolidated').text == 'true'
            )
            
            if is_consolidated:
                digest_count += 1
                feed_html += process_digest_item(
                    item, item_link, item_title, item_date, item_desc
                )
            else:
                regular_count += 1
                feed_html += process_regular_item(
                    item_link, item_title, item_date, item_desc
                )
        
        feed_html += '''
    </div>
</body>
</html>
'''
        
        # Write feed HTML file
        feed_html_file = os.path.join(output_dir, os.path.splitext(file)[0] + '.html')
        with open(feed_html_file, 'w', encoding='utf-8') as f:
            f.write(feed_html)
        
        # Create feed entry for the index
        feed_entry = {
            'title': title,
            'url': file,
            'html_url': os.path.splitext(file)[0] + '.html',
            'description': description,
            'lastUpdated': last_build_date,
            'regularItems': regular_count,
            'digestItems': digest_count
        }
        feeds_list.append(feed_entry)
        
        # Add to the index page
        digest_suffix = '' if digest_count == 1 else 's'
        html_file = os.path.splitext(file)[0] + '.html'
        
        html_content += f'''        <li>
            <a href="{html_file}">{html.escape(title)}</a>
            <div class="feed-description">{html.escape(description)}</div>
            <div class="feed-description">
                {regular_count} focused articles and {digest_count} digest item{digest_suffix}
            </div>
            <div class="updated">Last updated: {html.escape(last_build_date)}</div>
        </li>
'''
    
    return feeds_list, html_content


def add_state_info(html_content, state_file):
    """Add state information to the HTML content if available.
    
    Args:
        html_content: Current HTML content
        state_file: Path to the state file
        
    Returns:
        str: Updated HTML content
    """
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
                last_updated = state_data.get('last_updated', 'Unknown')
                feed_count = len(state_data.get('feeds', {}))
                
                html_content += f'''    </ul>
    <div class="state-info">
        <strong>State Information:</strong>
        <div>Last state update: {html.escape(last_updated)}</div>
        <div>Tracking {feed_count} feeds</div>
    </div>
'''
        except Exception as e:
            print(f"Error reading state file: {e}")
            html_content += '''    </ul>'''
    else:
        html_content += '''    </ul>'''
    
    return html_content


def generate_pages(input_dir='processed_feeds', output_dir='docs'):
    """Generate GitHub Pages from processed RSS feeds.
    
    Args:
        input_dir: Directory containing the processed XML feeds
        output_dir: Directory to output the GitHub Pages files
        
    Returns:
        int: Number of feeds processed
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy state file if it exists
    state_file = os.path.join(input_dir, 'processed_state.json')
    if os.path.exists(state_file):
        shutil.copy2(state_file, os.path.join(output_dir, 'processed_state.json'))
        print(f"State file copied to {output_dir}/processed_state.json")
    else:
        print("Warning: State file not found")
    
    # Copy feed files if they exist
    feed_count = 0
    if os.path.exists(input_dir):
        for file in os.listdir(input_dir):
            if file.endswith('.xml'):
                # Create a copy in the output directory
                src_path = os.path.join(input_dir, file)
                dst_path = os.path.join(output_dir, file)
                with open(src_path, 'rb') as src:
                    with open(dst_path, 'wb') as dst:
                        dst.write(src.read())
                feed_count += 1
                print(f"Copied feed: {file}")
    
    print(f"Total feeds copied: {feed_count}")
    
    # Create a metadata file with information about when the feeds were last processed
    metadata = {
        "last_processed": datetime.now().isoformat(),
        "feed_count": feed_count
    }
    
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Process feeds and create HTML
    feeds_list, html_content = process_feeds(input_dir, output_dir, state_file)
    
    # Add state information if available
    html_content = add_state_info(html_content, state_file)
    
    # Finish HTML
    html_content += '''</body>
</html>'''
    
    # Write HTML file
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Write JSON file
    with open(os.path.join(output_dir, 'feeds.json'), 'w', encoding='utf-8') as f:
        json.dump(feeds_list, f, indent=2)
    
    print(f"Generated GitHub Pages with {len(feeds_list)} feeds")
    return len(feeds_list)


if __name__ == "__main__":
    import sys
    
    input_dir = 'processed_feeds'
    output_dir = 'docs'
    
    # Allow override from command line
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    generate_pages(input_dir, output_dir) 
