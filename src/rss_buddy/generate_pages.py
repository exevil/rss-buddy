#!/usr/bin/env python3
"""Module for generating HTML pages from processed feed state."""

import hashlib  # Import hashlib
import html
import json
import os
import re  # Import re for sanitization
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


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a safe filename."""
    # Replace known problematic characters with underscores
    name = name.replace(" ", "_")
    name = re.sub(r"[/\\?:*\"<>|]", "_", name)
    # Remove any characters that are not alphanumeric, underscore, or hyphen
    name = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
    # Limit length
    return name[:100]  # Limit length to avoid issues


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


def create_feed_html_start(feed_title: str, feed_url: str) -> str:
    """Create the start of an individual feed's HTML page."""
    html_content = create_html_header(f"Feed: {feed_title}")
    html_content += f"""
<body>
    <a href="index.html" class="back-link">← Back to all feeds</a>
    <h1>{html.escape(feed_title)}</h1>
    <div class="feed-description"><small>Original Feed URL: <a href="{html.escape(feed_url)}">{html.escape(feed_url)}</a></small></div>
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

    # Retrieve the feed title from the state manager
    feed_title = state_manager.get_feed_title(feed_url) or feed_url

    if not items:
        print(f"    No items found within lookback period for {feed_url}. Skipping HTML.")
        return None

    processed_items = [item for item in items if item.get("status") == "processed"]
    digest_items = [item for item in items if item.get("status") == "digest"]

    html_content = create_feed_html_start(feed_title, feed_url)
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

    # --- Filename Generation ---
    # Sanitize the feed title for the filename
    sanitized_title = sanitize_filename(feed_title)
    if not sanitized_title:
        # Fallback if title sanitization results in an empty string (e.g., only symbols)
        sanitized_title = hashlib.md5(feed_url.encode("utf-8")).hexdigest()
    feed_html_filename = f"feed_{sanitized_title}.html"
    feed_html_path = os.path.join(output_dir, feed_html_filename)

    try:
        with open(feed_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"    Successfully generated HTML file: {feed_html_filename}")

        # Return metadata for the index
        return {
            "url": feed_url,
            "title": feed_title,
            "filename": feed_html_filename,
            "last_updated": feed_last_updated,
            "processed_count": len(processed_items),
            "digest_count": len(digest_items),
        }

    except IOError as e:
        print(f"    Error writing HTML file {feed_html_filename}: {e}")
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
    # Get config directly from environment or use defaults
    days_lookback = get_env_int("DAYS_LOOKBACK", 7)
    summary_max_tokens = get_env_int("SUMMARY_MAX_TOKENS", 150)
    api_key = get_env_str("OPENAI_API_KEY")
    model = get_env_str("AI_MODEL")

    if not api_key or not model:
        print(
            "Error: OPENAI_API_KEY and AI_MODEL environment variables are required for digest generation."
        )
        # Consider if generation should proceed without digests

    # --- Initialization ---
    os.makedirs(output_dir, exist_ok=True)
    state_manager = StateManager(output_dir=data_dir)  # Load state from data_dir
    ai_interface = AIInterface(api_key=api_key, model=model) if api_key and model else None

    if ai_interface is None:
        print("Warning: AI Interface not initialized. Digest generation will be skipped.")

    feed_urls = list(state_manager.state.get("feeds", {}).keys())
    print(f"Found {len(feed_urls)} feeds in state file.")

    index_html = create_index_html_start()
    feeds_metadata = []
    processed_total = 0
    digest_total = 0

    for feed_url in feed_urls:
        if ai_interface:
            feed_metadata = _generate_feed_html(
                feed_url=feed_url,
                state_manager=state_manager,
                ai_interface=ai_interface,  # Pass the initialized AI interface
                days_lookback=days_lookback,
                summary_max_tokens=summary_max_tokens,
                output_dir=output_dir,
            )
        else:
            # Handle case where AI is not available (e.g., generate without digest)
            # This part needs refinement based on desired behavior without AI
            print(f"Skipping feed {feed_url} due to missing AI configuration.")
            feed_metadata = None  # Or generate a basic page

        if feed_metadata:
            feeds_metadata.append(feed_metadata)
            processed_total += feed_metadata.get("processed_count", 0)
            digest_total += feed_metadata.get("digest_count", 0)

            # Add entry to index HTML
            index_html += f'''
                <li>
                    <a href="{html.escape(feed_metadata["filename"])}">{html.escape(feed_metadata["title"])}</a>
                    <div class="feed-description">
                        ({feed_metadata["processed_count"]} processed, {feed_metadata["digest_count"]} digest)<br>
                        <small>Original URL: {html.escape(feed_metadata["url"])}</small><br>
                        <small>Last Article: {feed_metadata["last_updated"]}</small>
                    </div>
                </li>
            '''

    # --- Finalize Index Page ---
    index_html += "    </ul>\n"  # Close the list

    # Add state info
    state_last_updated = state_manager.state.get("last_updated", "Unknown")
    try:
        parsed_update_time = datetime.fromisoformat(state_last_updated).astimezone(timezone.utc)
        state_last_updated = parsed_update_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        pass  # Keep original string if parsing fails

    index_html += f"""    <div class="state-info">
        <strong>State Information:</strong>
        <div>Last Processed Run: {html.escape(state_last_updated)}</div>
        <div>Feeds Tracked: {len(feed_urls)}</div>
        <div>Lookback Period: {days_lookback} days</div>
    </div>
"""
    index_html += create_html_footer()

    # --- Write Index HTML ---
    index_path = os.path.join(output_dir, "index.html")
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)
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
