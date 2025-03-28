#!/usr/bin/env python3
"""Main script for RSS Buddy, handles configuration and executes the feed processor."""
import os
import sys
from typing import List
from dotenv import load_dotenv

from .state_manager import StateManager
from .ai_interface import AIInterface
from .feed_processor import FeedProcessor

def get_env_list(var_name: str, default=None) -> List[str]:
    """Get a list from environment variable, separated by newlines or commas."""
    value = os.environ.get(var_name)
    if not value:
        return default or []
    
    # Check if value contains newlines
    if '\n' in value:
        # Split by newlines and filter out empty items
        return [item.strip() for item in value.split('\n') if item.strip()]
    else:
        # Split by commas (alternative format)
        return [item.strip() for item in value.split(',') if item.strip()]

def get_env_int(var_name: str, default: int) -> int:
    """Get an integer from environment variable."""
    value = os.environ.get(var_name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        print(f"Warning: Could not parse {var_name} as integer, using default {default}")
        return default

def main():
    """Execute the RSS Buddy process based on environment configuration."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Default configuration values
    DEFAULT_RSS_FEEDS = [
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://www.wired.com/feed/rss"
    ]

    DEFAULT_USER_PREFERENCE_CRITERIA = """
    When determining if an article should be shown in full or summarized, consider these factors:
    - Technical deep dives in machine learning, AI, and quantum computing should be shown in FULL
    - Breaking news about major tech companies should be shown in FULL
    - General technology news can be SUMMARIZED
    """

    DEFAULT_DAYS_LOOKBACK = 7
    DEFAULT_AI_MODEL = "gpt-4"
    DEFAULT_SUMMARY_MAX_TOKENS = 150
    DEFAULT_OUTPUT_DIR = "processed_feeds"

    # Get configuration from environment variables, falling back to defaults
    RSS_FEEDS = get_env_list('RSS_FEEDS', DEFAULT_RSS_FEEDS)
    USER_PREFERENCE_CRITERIA = os.environ.get('USER_PREFERENCE_CRITERIA', DEFAULT_USER_PREFERENCE_CRITERIA)
    DAYS_LOOKBACK = get_env_int('DAYS_LOOKBACK', DEFAULT_DAYS_LOOKBACK)
    AI_MODEL = os.environ.get('AI_MODEL', DEFAULT_AI_MODEL)
    SUMMARY_MAX_TOKENS = get_env_int('SUMMARY_MAX_TOKENS', DEFAULT_SUMMARY_MAX_TOKENS)
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', DEFAULT_OUTPUT_DIR)
    
    # Check for OpenAI API key
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        print("Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
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