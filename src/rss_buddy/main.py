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
    if '\n' in value:
        # Split by newlines and filter out empty items
        result = [item.strip() for item in value.split('\n') if item.strip()]
    else:
        # Split by commas (alternative format)
        result = [item.strip() for item in value.split(',') if item.strip()]
    
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
    RSS_FEEDS = get_env_list('RSS_FEEDS')
    USER_PREFERENCE_CRITERIA = get_env_str('USER_PREFERENCE_CRITERIA')
    DAYS_LOOKBACK = get_env_int('DAYS_LOOKBACK')
    AI_MODEL = get_env_str('AI_MODEL')
    SUMMARY_MAX_TOKENS = get_env_int('SUMMARY_MAX_TOKENS')
    OPENAI_API_KEY = get_env_str('OPENAI_API_KEY')
    
    # Get output directory (optional with default)
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', "processed_feeds")
    
    # Initialize components
    state_manager = StateManager(output_dir=OUTPUT_DIR)
    ai_interface = AIInterface(api_key=OPENAI_API_KEY, model=AI_MODEL)
    
    # Initialize feed processor
    feed_processor = FeedProcessor(
        state_manager=state_manager,
        ai_interface=ai_interface,
        output_dir=OUTPUT_DIR,
        days_lookback=DAYS_LOOKBACK,
        user_preference_criteria=USER_PREFERENCE_CRITERIA,
        summary_max_tokens=SUMMARY_MAX_TOKENS
    )
    
    # Process feeds
    print(f"RSS Buddy is processing {len(RSS_FEEDS)} feeds...")
    processed_files = feed_processor.process_feeds(RSS_FEEDS)
    
    print(f"Processed {len(processed_files)} feed(s)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())