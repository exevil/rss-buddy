#!/usr/bin/env python3
"""Module for generating HTML pages from processed feed state using Jinja2 templates."""

import dataclasses  # Import dataclasses
import hashlib  # Import hashlib
import json
import os
import re  # Import re for sanitization
import shutil  # Import shutil for copying the state file
import sys
from datetime import datetime, timezone
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import necessary components from the package
try:
    # Assume running as part of the package
    from .ai_interface import AIInterface, MockAIInterface  # Import MockAIInterface for fallback
    from .config import RssBuddyConfig  # Import config
    from .interfaces.protocols import (
        AIInterfaceProtocol,
        StateManagerProtocol,
    )
    from .models import (
        Article,
        FeedDisplayData,
        IndexDisplayData,
        IndexFeedInfo,
    )
    from .state_manager import StateManager
    from .utils.date_parser import RobustDateParser
except ImportError:
    # Allow running as a script (less ideal, dependencies might not resolve)
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from rss_buddy.ai_interface import (
        AIInterface,
        MockAIInterface,
    )  # Import MockAIInterface for fallback
    from rss_buddy.config import RssBuddyConfig  # Import config
    from rss_buddy.interfaces.protocols import (
        AIInterfaceProtocol,
        StateManagerProtocol,
    )
    from rss_buddy.models import (
        Article,
        FeedDisplayData,
        IndexDisplayData,
        IndexFeedInfo,
    )
    from rss_buddy.state_manager import StateManager
    from rss_buddy.utils.date_parser import RobustDateParser


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


# --- HTML Generation Helpers ---


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a safe filename."""
    # Replace known problematic characters with underscores
    name = name.replace(" ", "_")
    name = re.sub(r"[\/\\?:*\"<>|]", "_", name)  # Corrected regex
    # Remove any characters that are not alphanumeric, underscore, or hyphen
    name = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
    # Limit length
    return name[:100]


def _hydrate_article(item_dict: dict, state_manager: StateManagerProtocol) -> Article:
    """Converts a dictionary from state_manager into an Article object, using StateManager for date parsing."""
    published_date = None
    processed_date = None
    try:
        pub_date_str = item_dict.get("date")
        if pub_date_str:
            # Use the injected state_manager's date parser
            published_date = state_manager.parse_date(pub_date_str)
            if published_date is None:
                print(
                    f"Warning: Could not parse publish date '{pub_date_str}' for item {item_dict.get('id')}"
                )

        proc_date_str = item_dict.get("processed_at")
        if proc_date_str:
            # processed_at is expected to be ISO format
            try:
                processed_date = datetime.fromisoformat(
                    proc_date_str.replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            except (ValueError, TypeError) as proc_e:
                print(
                    f"Warning: Could not parse processed_at date '{proc_date_str}' for item {item_dict.get('id')}: {proc_e}"
                )

    except Exception as e:
        print(f"Warning: Error processing dates for article {item_dict.get('id')}: {e}")

    return Article(
        id=item_dict.get(
            "id", hashlib.sha1(item_dict.get("link", "").encode()).hexdigest()
        ),  # Ensure ID exists
        title=item_dict.get("title", "Untitled Article"),
        link=item_dict.get("link", "#"),
        summary=item_dict.get("summary", ""),
        published_date=published_date,
        processed_date=processed_date,
        status=item_dict.get("status"),
    )


# --- Core Logic ---


def _generate_feed_html(
    feed_url: str,
    state_manager: StateManagerProtocol,
    ai_interface: AIInterfaceProtocol,
    days_lookback: int,
    summary_max_tokens: int,
    output_dir: str,
    jinja_env: Environment,
    generation_time_display: str,
) -> Optional[IndexFeedInfo]:
    """Generates the HTML page for a single feed using Jinja2 and returns its metadata."""
    print(f"  Generating HTML for feed: {feed_url}")
    # Get items as dictionaries from state manager
    items_dict = state_manager.get_items_in_lookback(feed_url, days_lookback)

    feed_title = state_manager.get_feed_title(feed_url) or feed_url

    if not items_dict:
        print(f"    No items found within lookback period for {feed_url}. Skipping HTML.")
        return None

    # Convert dictionaries to Article objects
    all_articles = [_hydrate_article(item, state_manager) for item in items_dict]

    # Sort articles by published date (newest first), handling None dates
    all_articles.sort(
        key=lambda x: x.published_date
        if x.published_date
        else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    processed_articles = [article for article in all_articles if article.status == "processed"]
    digest_articles = [article for article in all_articles if article.status == "digest"]

    feed_last_updated_display = "Never"
    if all_articles and all_articles[0].published_date:
        feed_last_updated_display = all_articles[0].published_date.strftime(
            "%a, %d %b %Y %H:%M GMT"
        )

    ai_digest_summary = None
    if digest_articles:
        print(f"    Generating digest for {len(digest_articles)} items...")
        try:
            digest_dicts = [
                {
                    "title": a.title,
                    "link": a.link,
                    "summary": a.summary,
                    "date": a.published_date.isoformat() if a.published_date else None,
                }
                for a in digest_articles
            ]
            ai_digest_summary = ai_interface.generate_consolidated_summary(
                articles=digest_dicts, max_tokens=summary_max_tokens
            )
        except Exception as e:
            print(f"Error generating digest summary for {feed_url}: {e}")
            ai_digest_summary = "<p><i>Error generating summary.</i></p>"

    # Prepare data for the template
    feed_data = FeedDisplayData(
        url=feed_url,
        title=feed_title,
        processed_items=processed_articles,
        digest_items=digest_articles,  # Keep original items for count etc.
        ai_digest_summary=ai_digest_summary,
        last_updated_display=feed_last_updated_display,
        # generation_time_display is added in the template context below
    )

    # Render the template
    template = jinja_env.get_template("feed.html.j2")
    html_content = template.render(
        feed_data=feed_data, generation_time_display=generation_time_display
    )

    # Save the HTML file
    filename_base = sanitize_filename(feed_title)
    html_filename = f"feed_{filename_base}.html"
    html_filepath = os.path.join(output_dir, html_filename)
    try:
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"    Successfully generated: {html_filepath}")
    except IOError as e:
        print(f"Error writing HTML file {html_filepath}: {e}")
        return None

    # Return metadata for the index page
    return IndexFeedInfo(
        title=feed_title,
        filename=html_filename,
        processed_count=len(processed_articles),
        digest_count=len(digest_articles),
        original_url=feed_url,
    )


def generate_pages(
    config: RssBuddyConfig,
    state_manager: Optional[StateManagerProtocol] = None,
    ai_interface: Optional[AIInterfaceProtocol] = None,
    docs_dir: str = "docs",
):
    """Generates the full static HTML site using provided configuration and components."""
    print("Starting HTML page generation...")

    # --- Setup Components if not provided ---
    if state_manager is None:
        # Requires a state file in config.output_dir
        state_file = os.path.join(config.output_dir, "processed_state.json")
        if not os.path.exists(state_file):
            print(f"Error: State file not found at {state_file} and no StateManager provided.")
            return  # Or raise an error
        date_parser = RobustDateParser()
        state_manager = StateManager(date_parser=date_parser, state_file=state_file)

    if ai_interface is None:
        # Check if API key is available in config
        if config.openai_api_key:
            ai_interface = AIInterface(api_key=config.openai_api_key, model=config.ai_model)
        else:
            # Fallback to Mock AI if no key is provided (useful for rendering without API)
            print(
                "Warning: OPENAI_API_KEY not found. Using MockAIInterface for summary generation."
            )
            ai_interface = MockAIInterface()  # Basic mock for safe execution

    # --- Setup Jinja --- #
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    jinja_env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # --- Prepare Output Directory --- #
    os.makedirs(docs_dir, exist_ok=True)

    # --- Load State & Generate Feed Pages --- #
    all_feed_urls = state_manager.get_all_feed_urls()
    if not all_feed_urls:
        print("No feed URLs found in the state. Generating empty index.")
        all_feed_urls = []

    index_feeds_info: List[IndexFeedInfo] = []
    total_processed = 0
    total_digest = 0
    generation_time = datetime.now(timezone.utc)
    generation_time_display = generation_time.strftime("%Y-%m-%d %H:%M:%S UTC")

    for feed_url in all_feed_urls:
        feed_info = _generate_feed_html(
            feed_url=feed_url,
            state_manager=state_manager,
            ai_interface=ai_interface,
            days_lookback=config.days_lookback,
            summary_max_tokens=config.summary_max_tokens,
            output_dir=docs_dir,  # Generate HTML directly into docs_dir
            jinja_env=jinja_env,
            generation_time_display=generation_time_display,
        )
        if feed_info:
            index_feeds_info.append(feed_info)
            total_processed += feed_info.processed_count
            total_digest += feed_info.digest_count

    # Sort index feeds alphabetically by title
    index_feeds_info.sort(key=lambda x: x.title.lower())

    # --- Generate Index Page --- #
    index_data = IndexDisplayData(
        feeds=index_feeds_info,
        total_feeds=len(index_feeds_info),
        total_processed=total_processed,
        total_digest=total_digest,
        generation_time_display=generation_time_display,
    )
    index_template = jinja_env.get_template("index.html.j2")
    index_html_content = index_template.render(index_data=index_data)
    index_filepath = os.path.join(docs_dir, "index.html")
    try:
        with open(index_filepath, "w", encoding="utf-8") as f:
            f.write(index_html_content)
        print(f"Successfully generated: {index_filepath}")
    except IOError as e:
        print(f"Error writing index file {index_filepath}: {e}")

    # --- Generate Metadata File --- #
    metadata = {
        "generation_timestamp_utc": generation_time.isoformat(),
        "total_feeds": len(index_feeds_info),
        "total_processed": total_processed,
        "total_digest": total_digest,
        "feeds": [dataclasses.asdict(feed) for feed in index_feeds_info],  # Use dataclasses.asdict
    }
    metadata_filepath = os.path.join(docs_dir, "metadata.json")
    try:
        with open(metadata_filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"Successfully generated: {metadata_filepath}")
    except IOError as e:
        print(f"Error writing metadata file {metadata_filepath}: {e}")

    # --- Copy State File --- #
    state_file_path = state_manager.get_state_file_path()  # Get path from state manager
    if state_file_path and os.path.exists(state_file_path):
        state_copy_path = os.path.join(docs_dir, "processed_state.json")
        try:
            shutil.copy2(state_file_path, state_copy_path)
            print(f"Copied state file to: {state_copy_path}")
        except Exception as e:
            print(f"Error copying state file from {state_file_path} to {state_copy_path}: {e}")
    elif not state_file_path:
        print("Warning: Could not determine state file path from StateManager, skipping copy.")
    else:
        print(f"Warning: State file {state_file_path} not found, skipping copy.")

    print("HTML page generation complete.")


# Example usage if run as a script (for basic testing)
if __name__ == "__main__":
    # This requires environment variables to be set correctly
    # Load dotenv explicitly if running as script
    from dotenv import load_dotenv

    load_dotenv()

    try:
        config = RssBuddyConfig.from_environment()
        generate_pages(config=config)
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
