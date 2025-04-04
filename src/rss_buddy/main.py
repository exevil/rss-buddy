#!/usr/bin/env python3
"""Main script for RSS Buddy, handles configuration and executes the feed processor."""

import sys

from .ai_interface import AIInterface
from .config import RssBuddyConfig  # Import the config class
from .feed_processor import FeedProcessor
from .state_manager import StateManager
from .utils.date_parser import RobustDateParser


def run_feed_processing(config: RssBuddyConfig):
    """Execute the RSS Buddy feed processing based on provided configuration."""
    # Initialize components
    date_parser = RobustDateParser()
    # Use output_dir from config
    state_manager = StateManager(date_parser=date_parser, output_dir=config.output_dir)
    # Use API key and model from config
    ai_interface = AIInterface(api_key=config.openai_api_key, model=config.ai_model)

    # Initialize feed processor using config values
    feed_processor = FeedProcessor(
        state_manager=state_manager,
        ai_interface=ai_interface,
        date_parser=date_parser,
        days_lookback=config.days_lookback,
        user_preference_criteria=config.user_preference_criteria,
        summary_max_tokens=config.summary_max_tokens,
    )

    # Process feeds from config
    print(f"RSS Buddy is processing {len(config.rss_feeds)} feeds...")
    feed_processor.process_feeds(config.rss_feeds)
    print("Feed processing complete.")

    # Note: This function no longer returns an exit code directly.
    # The caller (main entry point) should handle exit codes.


def main():
    """Main entry point: Load config and run processing."""
    # Load configuration from environment
    # The dotenv loading is assumed to happen *before* this script is called,
    # typically handled by the execution wrapper (e.g., rss-buddy.sh or the console script).
    try:
        config = RssBuddyConfig.from_environment()
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1  # Return error code

    # Run the feed processing logic
    try:
        run_feed_processing(config)
        return 0  # Return success code
    except Exception as e:
        print(f"An unexpected error occurred during feed processing: {e}", file=sys.stderr)
        return 1  # Return error code


if __name__ == "__main__":
    sys.exit(main())
