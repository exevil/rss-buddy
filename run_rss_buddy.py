#!/usr/bin/env python3
"""Command-line runner for RSS Buddy."""
import argparse
import os
import sys

from dotenv import load_dotenv

from rss_buddy.main import main as rss_buddy_main

# Add the src directory to the path so we can import our package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process RSS feeds with AI filtering")
    
    parser.add_argument(
        "--api-key", 
        required=True,
        help="OpenAI API key (required)"
    )
    
    parser.add_argument(
        "--feeds", 
        required=True,
        help="Comma-separated list of RSS feed URLs to process (required)"
    )
    
    parser.add_argument(
        "--output-dir", 
        default="processed_feeds",
        help="Directory to store processed feeds (default: processed_feeds)"
    )
    
    parser.add_argument(
        "--days-lookback", 
        type=int,
        required=True, 
        help="Number of days to look back for articles (required)"
    )
    
    parser.add_argument(
        "--model", 
        required=True,
        help="OpenAI model to use (required)"
    )
    
    parser.add_argument(
        "--max-tokens", 
        type=int,
        required=True, 
        help="Maximum tokens for summaries (required)"
    )
    
    parser.add_argument(
        "--criteria", 
        required=True,
        help="User preference criteria for article evaluation (required)"
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
    
    # Set environment variables from command-line arguments
    os.environ["OPENAI_API_KEY"] = args.api_key
    os.environ["RSS_FEEDS"] = args.feeds
    os.environ["OUTPUT_DIR"] = args.output_dir
    os.environ["DAYS_LOOKBACK"] = str(args.days_lookback)
    os.environ["AI_MODEL"] = args.model
    os.environ["SUMMARY_MAX_TOKENS"] = str(args.max_tokens)
    os.environ["USER_PREFERENCE_CRITERIA"] = args.criteria
    
    # Run RSS Buddy
    exit_code = rss_buddy_main()
    
    # Generate pages if requested
    if args.generate_pages and exit_code == 0:
        try:
            from rss_buddy.generate_pages import generate_pages
            # Generate pages directly in the output directory
            generate_pages(args.output_dir, args.output_dir)
            print(f"Generated HTML pages in {args.output_dir}/ directory")
        except Exception as e:
            print(f"Error generating pages: {e}")
            exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())