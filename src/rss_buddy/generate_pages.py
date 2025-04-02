#!/usr/bin/env python3
"""Module for generating HTML pages from processed feed state."""

import html
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Import necessary components from the package
try:
    # Assume running as part of the package
    from .ai_interface import AIInterface
    from .state_manager import StateManager
except ImportError:
    # Allow running as a script
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from rss_buddy.ai_interface import AIInterface
    from rss_buddy.state_manager import StateManager


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


# --- Environment Variable Helpers ---


def get_env_str(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get a string environment variable."""
    value = os.environ.get(var_name, default)
    if not value:
        print(f"Warning: Environment variable {var_name} not found or empty.")
    return value


def get_env_int(var_name: str, default: int) -> int:
    """Get an integer environment variable."""
    value_str = os.environ.get(var_name)
    if value_str:
        try:
            return int(value_str)
        except ValueError:
            print(
                f"Warning: Could not parse {var_name} ('{value_str}') as integer. Using default: {default}."
            )
    return default


# --- HTML Generation Helpers ---


def create_html_header(title: str) -> str:
    """Create the HTML header section with styles."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; line-height: 1.6; background-color: #fff; color: #333; }}
        h1 {{ border-bottom: 1px solid #eee; padding-bottom: 10px; color: #1a1a1a; }}
        h2 {{ margin-top: 30px; color: #0056b3; }} /* Blue for article titles */
        h3 {{ margin-top: 20px; color: #555; }}
        a {{ color: #0056b3; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .article, .digest {{ margin-bottom: 30px; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f9f9f9; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .digest {{ background-color: #eef7ff; border-left: 5px solid #007bff; }} /* Lighter blue for digest */
        .digest h2 {{ color: #004085; }} /* Darker blue for digest title */
        .article-meta {{ font-size: 0.85rem; color: #666; margin-bottom: 10px; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; padding: 8px 15px; background-color: #e9ecef; border-radius: 5px; color: #495057; font-size: 0.9rem; }}
        .back-link:hover {{ background-color: #dee2e6; text-decoration: none; }}
        .feed-description {{ font-size: 0.9rem; color: #6c757d; margin: 5px 0 15px 0; }}
        .updated {{ font-size: 0.8rem; color: #888; margin-top: 10px; }}
        .state-info {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; font-size: 0.9rem; color: #495057; }}
        .explanation {{ margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #28a745; border-radius: 5px; }}
        .index-list {{ list-style: none; padding: 0; }}
        .index-list li {{ margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #fff; }}
        .index-list a {{ font-size: 1.1rem; font-weight: bold; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.8rem; color: #aaa; text-align: center; }}
    </style>
</head>"""


def create_index_html_start() -> str:
    """Create the start of the index HTML file."""
    html_content = create_html_header("RSS Buddy Processed Feeds")
    html_content += """
<body>
    <h1>RSS Buddy Processed Feeds</h1>
    <div class="explanation">
        <p>These feeds are processed with AI to prioritize content:</p>
        <ul>
            <li><strong>Processed articles:</strong> Shown individually below.</li>
            <li><strong>Digest articles:</strong> Consolidated into a single digest section (highlighted in blue) by AI.</li>
        </ul>
    </div>
    <p>Select a feed to view:</p>
    <ul class="index-list">
"""
    return html_content


def create_feed_html_start(feed_title: str) -> str:
    """Create the start of an individual feed's HTML page."""
    html_content = create_html_header(f"Feed: {feed_title}")
    html_content += f"""
<body>
    <a href="index.html" class="back-link">← Back to all feeds</a>
    <h1>{html.escape(feed_title)}</h1>
    <div>
"""
    return html_content


def format_item_html(item: Dict[str, Any], is_digest_item: bool = False) -> str:
    """Formats a single item (processed or digest) into HTML."""
    title = item.get("title", "Untitled Item")
    link = item.get("link", "#")
    summary = item.get("summary", "")
    date_str = item.get("date")
    processed_at_str = item.get("processed_at")

    date_display = "Date not available"
    if date_str:
        try:
            # Attempt to parse the date for display
            parsed_date = StateManager()._parse_date(date_str)  # Use parser from StateManager
            if parsed_date:
                date_display = parsed_date.strftime("%a, %d %b %Y %H:%M GMT")
            else:
                date_display = f"Original: {html.escape(date_str)}"  # Show original if unparseable
        except Exception:
            date_display = f"Original: {html.escape(date_str)}"

    processed_display = ""
    if processed_at_str:
        try:
            processed_dt = datetime.fromisoformat(processed_at_str).astimezone(timezone.utc)
            processed_display = f" | Processed: {processed_dt.strftime('%Y-%m-%d %H:%M GMT')}"
        except Exception:
            pass  # Ignore error if processed_at is invalid

    css_class = "digest" if is_digest_item else "article"
    tag = "h3" if is_digest_item else "h2"  # Use H3 for digest title for hierarchy

    html_output = f'''
        <div class="{css_class}">
            <{tag}><a href="{html.escape(link)}">{html.escape(title)}</a></{tag}>
            <div class="article-meta">Published: {date_display}{processed_display}</div>
            <div>{summary}</div>
        </div>
'''
    return html_output


def create_html_footer() -> str:
    """Creates the HTML footer section."""
    now = datetime.now(timezone.utc)
    return f"""
    <footer>
        Generated by RSS Buddy on {now.strftime("%Y-%m-%d %H:%M:%S UTC")}
    </footer>
</body>
</html>
"""


# --- Core Logic ---


def _generate_feed_html(
    feed_url: str,
    state_manager: StateManager,
    ai_interface: AIInterface,
    days_lookback: int,
    summary_max_tokens: int,
    output_dir: str,
) -> Optional[Dict[str, Any]]:
    """Generates the HTML page for a single feed and returns its metadata."""
    print(f"  Generating HTML for feed: {feed_url}")
    items = state_manager.get_items_in_lookback(feed_url, days_lookback)

    if not items:
        print(f"    No items found within lookback period for {feed_url}. Skipping HTML.")
        return None

    processed_items = [item for item in items if item.get("status") == "processed"]
    digest_items = [item for item in items if item.get("status") == "digest"]

    # Use the title from the most recent item as the feed title (approximation)
    # A better approach might store feed metadata in the state
    feed_title = items[0].get("title", feed_url)  # Fallback to URL
    if len(feed_title) > 70:  # Truncate long titles from items
        feed_title = feed_title[:67] + "..."

    html_content = create_feed_html_start(feed_title)
    feed_last_updated = "Never"
    if items:
        last_item_date = state_manager._parse_date(items[0].get("date"))
        if last_item_date:
            feed_last_updated = last_item_date.strftime("%a, %d %b %Y %H:%M GMT")

    # Add Processed Items
    if processed_items:
        html_content += "<h3>Processed Articles</h3>"
        for item in processed_items:
            html_content += format_item_html(item, is_digest_item=False)
    else:
        html_content += "<p>No individually processed articles in the lookback period.</p>"

    # Add Digest Items (Consolidated)
    if digest_items:
        print(f"    Generating digest for {len(digest_items)} items...")
        try:
            digest_summary_html = ai_interface.generate_consolidated_summary(
                articles=digest_items, max_tokens=summary_max_tokens
            )
            if digest_summary_html:
                # Wrap the AI summary in our digest structure
                digest_wrapper = {
                    "title": f"AI Digest ({len(digest_items)} items)",
                    "link": "#",  # Digest doesn't have a single link
                    "summary": digest_summary_html,
                    "date": datetime.now(timezone.utc).isoformat(),  # Use generation time
                }
                html_content += format_item_html(digest_wrapper, is_digest_item=True)
            else:
                html_content += '<div class="digest"><h3>AI Digest</h3><p>Could not generate digest summary.</p></div>'
                print("    AI digest generation returned None.")
        except Exception as e:
            html_content += (
                f'<div class="digest"><h3>AI Digest</h3><p>Error generating digest: {e}</p></div>'
            )
            print(f"    Error during AI digest generation: {e}")
    else:
        html_content += "<p>No articles marked for digest in the lookback period.</p>"

    html_content += create_html_footer()

    # Generate filename (simple hash of URL for now)
    import hashlib

    feed_hash = hashlib.md5(feed_url.encode()).hexdigest()
    html_filename = f"feed_{feed_hash}.html"
    html_filepath = os.path.join(output_dir, html_filename)

    try:
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"    Successfully wrote feed HTML to {html_filepath}")

        # Return metadata for index page
        return {
            "title": feed_title,
            "url": feed_url,  # Original feed URL
            "html_filename": html_filename,
            "lastUpdated": feed_last_updated,
            "processed_count": len(processed_items),
            "digest_count": len(digest_items),
        }

    except IOError as e:
        print(f"    Error writing HTML file {html_filepath}: {e}")
        return None


def _copy_state_file(data_dir: str, output_dir: str):
    """Copies the state file from data_dir to output_dir."""
    state_filename = "processed_state.json"
    src_path = os.path.join(data_dir, state_filename)
    dst_path = os.path.join(output_dir, state_filename)

    if os.path.exists(src_path):
        try:
            with open(src_path, "rb") as src, open(dst_path, "wb") as dst:
                dst.write(src.read())
            print(f"Copied state file to {dst_path}")
        except IOError as e:
            print(f"Error copying state file from {src_path} to {dst_path}: {e}")
    else:
        print(f"Warning: State file not found in {data_dir}")


def generate_pages(data_dir: str = "processed_feeds", output_dir: str = "docs"):
    """Generate HTML pages from the processed state."""
    print(f"Generating HTML pages from data in '{data_dir}' to '{output_dir}'")

    # --- Configuration ---
    # Get AI config from environment variables
    api_key = get_env_str("OPENAI_API_KEY")
    ai_model = get_env_str("AI_MODEL", "gpt-3.5-turbo")  # Default model
    summary_max_tokens = get_env_int("SUMMARY_MAX_TOKENS", 150)  # Default tokens
    days_lookback = get_env_int("DAYS_LOOKBACK", 7)  # Default lookback

    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set. Cannot generate digests.")
        # Decide if we should proceed without digests or exit
        # For now, let's proceed but digests will fail

    # --- Initialization ---
    os.makedirs(output_dir, exist_ok=True)
    state_manager = StateManager(output_dir=data_dir)  # State lives in data_dir
    ai_interface = AIInterface(api_key=api_key, model=ai_model)

    # --- Process Feeds ---
    index_html_content = create_index_html_start()
    feeds_metadata = []
    feed_urls = list(state_manager.state.get("feeds", {}).keys())

    if not feed_urls:
        print("No feeds found in state file. No feed pages to generate.")
    else:
        print(f"Found {len(feed_urls)} feeds in state. Generating pages...")
        for feed_url in feed_urls:
            metadata = _generate_feed_html(
                feed_url, state_manager, ai_interface, days_lookback, summary_max_tokens, output_dir
            )
            if metadata:
                feeds_metadata.append(metadata)
                # Add to index page
                digest_suffix = "s" if metadata["digest_count"] != 1 else ""
                item_suffix = "s" if metadata["processed_count"] != 1 else ""
                index_html_content += f'''        <li>
                     <a href="{metadata["html_filename"]}">{html.escape(metadata["title"])}</a>
                     <div class="feed-description">({metadata["processed_count"]} processed item{item_suffix}, {metadata["digest_count"]} item{digest_suffix} for digest)</div>
                     <div class="updated">Last Item Update: {html.escape(metadata["lastUpdated"])}</div>
                     <div class="feed-description"><small>Original URL: {html.escape(metadata["url"])}</small></div>
                 </li>
'''

    # --- Finalize Index Page ---
    index_html_content += "    </ul>\n"  # Close the list

    # Add state info
    state_last_updated = state_manager.state.get("last_updated", "Unknown")
    try:
        parsed_update_time = datetime.fromisoformat(state_last_updated).astimezone(timezone.utc)
        state_last_updated = parsed_update_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        pass  # Keep original string if parsing fails

    index_html_content += f"""    <div class="state-info">
        <strong>State Information:</strong>
        <div>Last Processed Run: {html.escape(state_last_updated)}</div>
        <div>Feeds Tracked: {len(feed_urls)}</div>
        <div>Lookback Period: {days_lookback} days</div>
    </div>
"""
    index_html_content += create_html_footer()

    # --- Write Index HTML ---
    index_path = os.path.join(output_dir, "index.html")
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html_content)
        print(f"Successfully wrote index.html to {index_path}")
    except IOError as e:
        print(f"ERROR: Could not write index.html: {e}")

    # --- Write Feeds JSON ---
    json_path = os.path.join(output_dir, "feeds.json")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(feeds_metadata, f, indent=2)
        print(f"Successfully wrote feeds.json to {json_path}")
    except IOError as e:
        print(f"ERROR: Could not write feeds.json: {e}")

    # --- Copy State File ---
    _copy_state_file(data_dir, output_dir)

    # --- Write Metadata File ---
    metadata_path = os.path.join(output_dir, "metadata.json")
    run_metadata = {
        "generation_time_utc": datetime.now(timezone.utc).isoformat(),
        "feeds_generated": len(feeds_metadata),
        "source_data_dir": os.path.abspath(data_dir),
        "output_dir": os.path.abspath(output_dir),
    }
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(run_metadata, f, indent=2)
        print(f"Successfully wrote metadata.json to {metadata_path}")
    except IOError as e:
        print(f"ERROR: Could not write metadata.json: {e}")


if __name__ == "__main__":
    # Get directories from args or use defaults
    data_dir_arg = sys.argv[1] if len(sys.argv) > 1 else "processed_feeds"
    output_dir_arg = sys.argv[2] if len(sys.argv) > 2 else "docs"
    generate_pages(data_dir=data_dir_arg, output_dir=output_dir_arg)
