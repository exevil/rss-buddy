#!/usr/bin/env python3
"""Main script for RSS Buddy, handles configuration and executes the feed processor."""

import os
import sys
from typing import List

from dotenv import load_dotenv

from .ai_interface import AIInterface
from .feed_processor import FeedProcessor
from .state_manager import StateManager


def get_env_list(var_name: str) -> List[str]:
    """Get a list from environment variable, separated by newlines or commas."""
    value = os.environ.get(var_name)
    if not value:
        print(f"Error: {var_name} environment variable not found.")
        sys.exit(1)

    # Check if value contains newlines
    if "\n" in value:
        # Split by newlines and filter out empty items
        result = [item.strip() for item in value.split("\n") if item.strip()]
    else:
        # Split by commas (alternative format)
        result = [item.strip() for item in value.split(",") if item.strip()]

    if not result:
        print(f"Error: {var_name} environment variable is empty.")
        sys.exit(1)

    return result


def get_env_int(var_name: str) -> int:
    """Get an integer from environment variable."""
    value = os.environ.get(var_name)
    if not value:
        print(f"Error: {var_name} environment variable not found.")
        sys.exit(1)
    try:
        return int(value)
    except ValueError:
        print(f"Error: Could not parse {var_name} as integer. Please provide a valid number.")
        sys.exit(1)


def get_env_str(var_name: str) -> str:
    """Get a string from environment variable."""
    value = os.environ.get(var_name)
    if not value:
        print(f"Error: {var_name} environment variable not found.")
        sys.exit(1)
    return value


def main():
    """Execute the RSS Buddy process based on environment configuration."""
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Get required configuration from environment variables
    rss_feeds = get_env_list("RSS_FEEDS")
    user_preference_criteria = get_env_str("USER_PREFERENCE_CRITERIA")
    days_lookback = get_env_int("DAYS_LOOKBACK")
    ai_model = get_env_str("AI_MODEL")
    summary_max_tokens = get_env_int("SUMMARY_MAX_TOKENS")
    openai_api_key = get_env_str("OPENAI_API_KEY")

    # Get output directory (optional with default)
    output_dir = os.environ.get("OUTPUT_DIR", "processed_feeds")

    # Initialize components
    state_manager = StateManager(output_dir=output_dir)
    ai_interface = AIInterface(api_key=openai_api_key, model=ai_model)

    # Initialize feed processor
    feed_processor = FeedProcessor(
        state_manager=state_manager,
        ai_interface=ai_interface,
        output_dir=output_dir,
        days_lookback=days_lookback,
        user_preference_criteria=user_preference_criteria,
        summary_max_tokens=summary_max_tokens,
    )

    # Process feeds
    print(f"RSS Buddy is processing {len(rss_feeds)} feeds...")
    processed_files = feed_processor.process_feeds(rss_feeds)

    print(f"Processed {len(processed_files)} feed(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
