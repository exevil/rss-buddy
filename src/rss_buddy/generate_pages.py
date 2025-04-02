#!/usr/bin/env python3
"""Module for generating HTML pages from processed RSS feeds for display on GitHub Pages."""

import html
import json
import os
import xml.etree.ElementTree as ElementTree
from datetime import datetime

from dateutil import parser

# Define timezone information
TZINFOS = {
    "PDT": -7 * 3600,
    "PST": -8 * 3600,
    "EDT": -4 * 3600,
    "EST": -5 * 3600,
    "CEST": 2 * 3600,
    "CET": 1 * 3600,
    "AEST": 10 * 3600,
    "AEDT": 11 * 3600,
}


def create_html_header(title):
    """Create the HTML header section with styles.

    Args:
        title: The title to use in the page

    Returns:
        str: HTML header content
    """
    return f"""<!DOCTYPE html>
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
</head>"""


def create_index_html_start():
    """Create the start of the index HTML file.

    Returns:
        str: HTML content for the start of the index page
    """
    html_content = create_html_header("rss-buddy processed feeds")
    html_content += """
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
"""
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
    html_content += f"""
<body>
    <a href="index.html" class="back-link">← Back to all feeds</a>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(description)}</p>
    <p><small>Last updated: {html.escape(last_build_date)}</small></p>

    <div>
"""
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
        article_links_elem = item.find("articleLinks")
        if article_links_elem is not None and article_links_elem.text:
            article_links = json.loads(article_links_elem.text)
    except Exception:
        pass

    # If we have article links but they're not in the description, add them
    if article_links and "<a href" not in item_desc:
        feed_html += """
            <div class="article-links">
                <h3>Included Articles:</h3>
                <ul>
"""
        for title, link in article_links.items():
            feed_html += (
                f'                    <li><a href="{html.escape(link)}">'
                f"{html.escape(title)}</a></li>\n"
            )
        feed_html += """
                </ul>
            </div>
"""

    feed_html += """
        </div>
"""
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
        tree = ElementTree.parse(file_path)
        root = tree.getroot()
        channel = root.find("channel")
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
            "Untitled Feed",
            "#",
            "No description",
            datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        )

    title = channel.find("title").text if channel.find("title") is not None else "Untitled Feed"
    link = channel.find("link").text if channel.find("link") is not None else "#"
    description = (
        channel.find("description").text
        if channel.find("description") is not None
        else "No description"
    )
    last_build_date = (
        channel.find("lastBuildDate").text if channel.find("lastBuildDate") is not None else ""
    )

    # Default to current time if no build date
    if not last_build_date:
        last_build_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")

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
        if not file.endswith(".xml"):
            continue

        file_path = os.path.join(input_dir, file)
        root, channel = parse_feed_file(file_path)

        if channel is None:
            continue

        title, link, description, last_build_date = get_channel_info(channel)

        # Get item counts
        items = channel.findall("item")
        regular_count = 0
        digest_count = 0

        # Create detailed HTML feed page
        feed_html = create_feed_html_start(title, description, last_build_date)

        for item in items:
            # Get the title element and its text, defaulting to 'Untitled Item' if not found
            title_element = item.find("title")
            item_title = title_element.text if title_element is not None else "Untitled Item"
            item_link = item.find("link").text if item.find("link") is not None else "#"
            description_element = item.find("description")
            item_desc = description_element.text if description_element is not None else ""
            pub_date = item.find("pubDate")

            item_date = ""
            if pub_date is not None and pub_date.text:
                try:
                    parsed_date = parser.parse(pub_date.text, tzinfos=TZINFOS)
                    item_date = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                except Exception as e:
                    print(f"Error parsing date: {e}")

            is_consolidated = (
                item.find("consolidated") is not None and item.find("consolidated").text == "true"
            )

            if is_consolidated:
                digest_count += 1
                feed_html += process_digest_item(item, item_link, item_title, item_date, item_desc)
            else:
                regular_count += 1
                feed_html += process_regular_item(item_link, item_title, item_date, item_desc)

        feed_html += """
    </div>
</body>
</html>
"""

        # Write feed HTML file
        feed_html_file = os.path.join(output_dir, os.path.splitext(file)[0] + ".html")
        with open(feed_html_file, "w", encoding="utf-8") as f:
            f.write(feed_html)

        # Create feed entry for the index
        feed_entry = {
            "title": title,
            "url": file,
            "html_url": os.path.splitext(file)[0] + ".html",
            "description": description,
            "lastUpdated": last_build_date,
            "regularItems": regular_count,
            "digestItems": digest_count,
        }
        feeds_list.append(feed_entry)

        # Add to the index page
        digest_suffix = "" if digest_count == 1 else "s"
        html_file = os.path.splitext(file)[0] + ".html"

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
            with open(state_file, "r") as f:
                state_data = json.load(f)
                last_updated = state_data.get("last_updated", "Unknown")
                feed_count = len(state_data.get("feeds", {}))

                html_content += f"""    </ul>
    <div class="state-info">
        <strong>State Information:</strong>
        <div>Last state update: {html.escape(last_updated)}</div>
        <div>Tracking {feed_count} feeds</div>
    </div>
"""
        except Exception as e:
            print(f"Error reading state file: {e}")
            html_content += """    </ul>"""
    else:
        html_content += """    </ul>"""

    return html_content


def _copy_file(src_path, dst_path, description):
    """Helper function to copy a single file with error handling.

    Args:
        src_path: Path to the source file
        dst_path: Path to the destination file
        description: Description of the file being copied

    Returns:
        bool: True if copy was successful, False otherwise
    """
    try:
        with open(src_path, "rb") as src, open(dst_path, "wb") as dst:
            dst.write(src.read())
        print(
            f"Successfully copied {description}: "
            f"{os.path.basename(src_path)}"
            f" to dir: {os.path.dirname(dst_path)}"
        )
        return True
    except IOError as e:
        print(
            f"Error copying {description} file: "
            f"{os.path.basename(src_path)}"
            f" to dir: {os.path.dirname(dst_path)}"
            f" Error: {e}"
        )
        return False


def _copy_state_file(input_dir, output_dir):
    """Copy the state file if it exists.

    Args:
        input_dir: Directory containing the state file
        output_dir: Directory to copy the state file to
    """
    state_file_name = "processed_state.json"
    state_file_src = os.path.join(input_dir, state_file_name)
    state_file_dst = os.path.join(output_dir, state_file_name)
    if os.path.exists(state_file_src):
        _copy_file(state_file_src, state_file_dst, "state")
    else:
        print("Warning: State file not found in input directory")


def _copy_feed_files(input_dir, output_dir):
    """Copy all .xml feed files from input_dir to output_dir.

    Args:
        input_dir: Directory containing the feed files
        output_dir: Directory to copy the feed files to

    Returns:
        int: Number of feed files copied
    """
    feed_count = 0
    if not os.path.exists(input_dir):
        print(f"Warning: Input directory {input_dir} does not exist.")
        return 0

    for file in os.listdir(input_dir):
        if file.endswith(".xml"):
            src_path = os.path.join(input_dir, file)
            dst_path = os.path.join(output_dir, file)
            if _copy_file(src_path, dst_path, "feed"):
                feed_count += 1

    if feed_count == 0:
        print(f"Warning: No .xml feed files found in {input_dir}.")
    print(f"Total feeds copied: {feed_count}")
    return feed_count


def _write_json_file(data, file_path, description):
    """Helper function to write JSON data to a file.

    Args:
        data: JSON data to write
        file_path: Path to the output file
        description: Description of the data being written

    Returns:
        bool: True if writing was successful, False otherwise
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Successfully wrote {description} to {file_path}")
        return True
    except IOError as e:
        print(f"Error writing {description} to {file_path}: {e}")
        return False


def generate_pages(input_dir="processed_feeds", output_dir="docs"):
    """Generate GitHub Pages from processed RSS feeds.

    Args:
        input_dir: Directory containing the processed XML feeds
        output_dir: Directory to output the GitHub Pages files

    Returns:
        int: Number of feeds processed, or -1 on error
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # --- File Copying ---
        _copy_state_file(input_dir, output_dir)
        feed_count = _copy_feed_files(input_dir, output_dir)

        if feed_count == 0:
            print("No feed files copied, skipping HTML generation.")
            # Still create metadata even if no feeds copied

        # --- Metadata ---
        metadata = {"last_processed": datetime.now().isoformat(), "feed_count": feed_count}
        metadata_path = os.path.join(output_dir, "metadata.json")
        _write_json_file(metadata, metadata_path, "metadata file")

        # --- HTML and Feed Data Generation ---
        state_file_path = os.path.join(input_dir, "processed_state.json")
        feeds_list, index_html_content = process_feeds(input_dir, output_dir, state_file_path)

        if not feeds_list and feed_count > 0:
            # This case might indicate an issue in process_feeds if XML files were copied
            # but not processed
            print(
                f"Warning: process_feeds did not return feed data despite {feed_count} "
                f"XML files being copied."
            )
        elif not feeds_list:
            print("No feed data generated by process_feeds (expected as no feeds were copied).")
            # If no feeds were processed, maybe skip index.html or create a placeholder?
            # For now, we will still try to write the basic index.

        # Add state information to the index HTML
        index_html_content = add_state_info(index_html_content, state_file_path)

        # Finish HTML
        index_html_content += "</body>\n</html>"  # Combined onto one line, using single quotes

        # --- Write Index HTML File ---
        index_path = os.path.join(output_dir, "index.html")
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(index_html_content)
            print(f"Successfully wrote index.html to {index_path}")
        except IOError as e:
            print(f"ERROR: Could not write index.html to {index_path}: {e}")
            raise  # Re-raise the exception to signal failure

        # --- Write Feeds JSON File ---
        json_path = os.path.join(output_dir, "feeds.json")
        _write_json_file(feeds_list, json_path, "feeds JSON")

        print(f"Generated GitHub Pages with {len(feeds_list)} feeds listed.")
        return len(feeds_list)

    except Exception as e:
        # Catch any other unexpected errors during page generation
        print(f"ERROR: An unexpected error occurred during generate_pages: {e}")
        # Optionally log the full traceback here
        # import traceback
        # traceback.print_exc()
        return -1  # Indicate error with a negative return value


if __name__ == "__main__":
    import sys

    input_dir = "processed_feeds"
    output_dir = "docs"

    # Allow override from command line
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    generate_pages(input_dir, output_dir)
