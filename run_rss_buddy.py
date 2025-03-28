#!/usr/bin/env python3
"""
Command-line runner for RSS Buddy.
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Add the src directory to the path so we can import our package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from rss_buddy.main import main as rss_buddy_main

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process RSS feeds with AI filtering")
    
    parser.add_argument(
        "--api-key", 
        help="OpenAI API key (overrides environment variable)"
    )
    
    parser.add_argument(
        "--feeds", 
        help="Comma-separated list of RSS feed URLs to process"
    )
    
    parser.add_argument(
        "--output-dir", 
        default="processed_feeds",
        help="Directory to store processed feeds"
    )
    
    parser.add_argument(
        "--days-lookback", 
        type=int, 
        help="Number of days to look back for articles"
    )
    
    parser.add_argument(
        "--model", 
        help="OpenAI model to use"
    )
    
    parser.add_argument(
        "--max-tokens", 
        type=int, 
        help="Maximum tokens for summaries"
    )
    
    parser.add_argument(
        "--criteria", 
        help="User preference criteria"
    )
    
    parser.add_argument(
        "--generate-pages", 
        action="store_true",
        help="Generate HTML pages after processing"
    )
    
    return parser.parse_args()

def main():
    """Parse arguments and run RSS Buddy."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    args = parse_args()
    
    # Override environment variables with command-line arguments
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    
    if args.feeds:
        os.environ["RSS_FEEDS"] = args.feeds
    
    if args.output_dir:
        os.environ["OUTPUT_DIR"] = args.output_dir
    
    if args.days_lookback:
        os.environ["DAYS_LOOKBACK"] = str(args.days_lookback)
    
    if args.model:
        os.environ["AI_MODEL"] = args.model
    
    if args.max_tokens:
        os.environ["SUMMARY_MAX_TOKENS"] = str(args.max_tokens)
    
    if args.criteria:
        os.environ["USER_PREFERENCE_CRITERIA"] = args.criteria
    
    # Run RSS Buddy
    exit_code = rss_buddy_main()
    
    # Generate pages if requested
    if args.generate_pages and exit_code == 0:
        try:
            from rss_buddy.generate_pages import generate_pages
            generate_pages(args.output_dir, "docs")
            print("Generated HTML pages in docs/ directory")
        except Exception as e:
            print(f"Error generating pages: {e}")
            exit_code = 1
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 