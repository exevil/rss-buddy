#!/usr/bin/env python3
"""Module for generating HTML pages from processed feed state using Jinja2 templates."""

import hashlib  # Import hashlib
import json
import os
import re  # Import re for sanitization
import sys
from datetime import datetime, timezone
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import necessary components from the package
try:
    # Assume running as part of the package
    from .ai_interface import AIInterface
    from .models import (
        Article,
        FeedDisplayData,
        IndexDisplayData,
        IndexFeedInfo,
    )  # New model imports
    from .state_manager import StateManager
except ImportError:
    # Allow running as a script
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from rss_buddy.ai_interface import AIInterface
    from rss_buddy.models import (
        Article,
        FeedDisplayData,
        IndexDisplayData,
        IndexFeedInfo,
    )  # New model imports
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


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a safe filename."""
    # Replace known problematic characters with underscores
    name = name.replace(" ", "_")
    name = re.sub(r"[\/\\?:*\"<>|]", "_", name)  # Corrected regex
    # Remove any characters that are not alphanumeric, underscore, or hyphen
    name = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
    # Limit length
    return name[:100]


def _hydrate_article(item_dict: dict, state_manager: StateManager) -> Article:
    """Converts a dictionary from state_manager into an Article object, using StateManager for date parsing."""
    published_date = None
    processed_date = None
    try:
        pub_date_str = item_dict.get("date")
        if pub_date_str:
            published_date = state_manager.parse_date(pub_date_str)  # Use StateManager's parser
            if published_date is None:
                print(
                    f"Warning: StateManager could not parse publish date '{pub_date_str}' for item {item_dict.get('id')}"
                )

        proc_date_str = item_dict.get("processed_at")
        if proc_date_str:
            # processed_at is expected to be ISO format, direct parsing is likely okay
            try:
                processed_date = datetime.fromisoformat(
                    proc_date_str.replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            except (ValueError, TypeError) as proc_e:
                print(
                    f"Warning: Could not parse processed_at date '{proc_date_str}' for item {item_dict.get('id')}: {proc_e}"
                )

    except Exception as e:  # Catch potential errors in state_manager.parse_date or isoformat
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
    state_manager: StateManager,
    ai_interface: AIInterface,
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
            # Pass the Article objects directly if AI interface can handle them,
            # otherwise, convert back to dicts if needed. Let's assume it needs dicts for now.
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


def generate_pages(data_dir: str, docs_dir: str = "docs"):
    """Generates the full static HTML site from the state file using Jinja2 templates."""
    print("Starting HTML page generation...")

    state_file = os.path.join(data_dir, "processed_state.json")
    if not os.path.exists(state_file):
        print(f"Error: State file not found at {state_file}")
        return

    # --- Load Config ---
    # API Key might not be strictly needed here if summaries are pre-generated,
    # but keeping it for potential future use or regeneration needs.
    api_key = get_env_str("OPENAI_API_KEY")
    if not api_key:
        # Allow proceeding without API key if only rendering existing state? Maybe.
        # For digest generation, it's required.
        print("Error: OPENAI_API_KEY environment variable not set.")
        # Depending on strictness, you might exit here.
        # return

    # Model needed for AIInterface init and digest generation
    ai_model = get_env_str("AI_MODEL", "gpt-3.5-turbo")
    summary_max_tokens = get_env_int("SUMMARY_MAX_TOKENS", 150)
    days_lookback = get_env_int("DAYS_LOOKBACK", 7)

    # --- Initialize Components ---
    state_manager = StateManager(state_file=state_file)

    # Initialize AI Interface (needed for digests)
    # Consider making AIInterface optional if no digests need generation
    ai_interface = AIInterface(api_key=api_key, model=ai_model)

    # Initialize Jinja2 Environment
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    if not os.path.isdir(template_dir):
        print(f"Error: Templates directory not found at {template_dir}")
        # Try relative path as fallback if running as script vs package
        alt_template_dir = os.path.join(os.getcwd(), "src", "rss_buddy", "templates")
        if os.path.isdir(alt_template_dir):
            template_dir = alt_template_dir
        else:
            print(f"Also checked: {alt_template_dir}")
            return  # Cannot proceed without templates

    print(f"Using template directory: {template_dir}")
    jinja_env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),  # Enable autoescaping
    )

    # --- Prepare Output ---
    os.makedirs(docs_dir, exist_ok=True)
    generation_time = datetime.now(timezone.utc)
    generation_time_display = generation_time.strftime("%Y-%m-%d %H:%M:%S UTC")

    # --- Generate Feed Pages and Collect Index Data ---
    feed_urls = state_manager.get_all_feed_urls()
    index_feeds_info: List[IndexFeedInfo] = []

    for feed_url in feed_urls:
        feed_info = _generate_feed_html(
            feed_url=feed_url,
            state_manager=state_manager,
            ai_interface=ai_interface,
            days_lookback=days_lookback,
            summary_max_tokens=summary_max_tokens,
            output_dir=docs_dir,
            jinja_env=jinja_env,
            generation_time_display=generation_time_display,
        )
        if feed_info:
            index_feeds_info.append(feed_info)

    # Sort index feeds alphabetically by title
    index_feeds_info.sort(key=lambda x: x.title.lower())

    # --- Generate Index Page ---
    index_data = IndexDisplayData(
        feeds=index_feeds_info, generation_time_display=generation_time_display
    )
    index_template = jinja_env.get_template("index.html.j2")
    index_html_content = index_template.render(index_data=index_data)

    index_filepath = os.path.join(docs_dir, "index.html")
    try:
        with open(index_filepath, "w", encoding="utf-8") as f:
            f.write(index_html_content)
        print(f"Successfully generated: {index_filepath}")
    except IOError as e:
        print(f"Error writing index HTML file {index_filepath}: {e}")

    # --- Generate Metadata/State Copy (Optional but good practice) ---
    metadata = {
        "generated_at": generation_time.isoformat(),
        "total_feeds": len(index_feeds_info),
        "total_processed": sum(f.processed_count for f in index_feeds_info),
        "total_digest": sum(f.digest_count for f in index_feeds_info),
        "days_lookback": days_lookback,
    }
    metadata_filepath = os.path.join(docs_dir, "metadata.json")
    try:
        with open(metadata_filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except IOError as e:
        print(f"Error writing metadata file {metadata_filepath}: {e}")

    # Copy state file for reference
    state_copy_filepath = os.path.join(docs_dir, "processed_state.json")
    try:
        import shutil

        shutil.copy2(state_file, state_copy_filepath)
    except Exception as e:
        print(f"Error copying state file to {state_copy_filepath}: {e}")

    print(f"HTML page generation finished. Output in: {docs_dir}")


if __name__ == "__main__":
    print("Running generate_pages as a script...")
    # Simple command-line argument handling for script usage
    if len(sys.argv) < 2:
        print("Usage: python generate_pages.py <data_directory> [output_docs_directory]")
        sys.exit(1)

    data_directory = sys.argv[1]
    docs_output_directory = sys.argv[2] if len(sys.argv) > 2 else "docs"

    # Load .env file if present for environment variables
    from dotenv import load_dotenv

    dotenv_path = os.path.join(
        os.path.dirname(__file__), "..", "..", ".env"
    )  # Adjust path as needed
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Attempted to load .env from: {os.path.abspath(dotenv_path)}")

    generate_pages(data_dir=data_directory, docs_dir=docs_output_directory)
