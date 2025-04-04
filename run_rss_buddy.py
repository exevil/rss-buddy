#!/usr/bin/env python3
"""Simplified command-line runner for RSS Buddy."""

import argparse
import os
import sys

from dotenv import load_dotenv

# Add the src directory to the path so we can import our package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# Import the main entry point and configuration loader
from rss_buddy.main import main as rss_buddy_main_entry
from rss_buddy.config import RssBuddyConfig
from rss_buddy.generate_pages import generate_pages


def parse_args():
    """Parse command-line arguments (only --generate-pages)."""
    parser = argparse.ArgumentParser(
        description="Run RSS Buddy feed processing and optionally generate HTML pages."
    )
    # Keep arguments for compatibility with rss-buddy.sh, but they won't be used directly
    # The main logic now relies on environment variables via RssBuddyConfig
    parser.add_argument("--api-key", help=argparse.SUPPRESS) # Suppress help
    parser.add_argument("--feeds", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", help=argparse.SUPPRESS)
    parser.add_argument("--days-lookback", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--model", help=argparse.SUPPRESS)
    parser.add_argument("--max-tokens", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--criteria", help=argparse.SUPPRESS)

    # The only functional argument
    parser.add_argument(
        "--generate-pages", action="store_true", help="Generate HTML pages after processing"
    )

    return parser.parse_args()


def main():
    """Load .env, run main processing, and optionally generate pages."""
    # Load environment variables from .env file if it exists (for local runs)
    load_dotenv()

    args = parse_args()

    print("Starting RSS Buddy feed processing...")
    # Run the main feed processing entry point
    # This now loads config from environment variables internally
    exit_code = rss_buddy_main_entry()

    if exit_code != 0:
        print("Feed processing failed, skipping page generation.", file=sys.stderr)
        return exit_code

    # Generate pages if requested and processing succeeded
    if args.generate_pages:
        print("Feed processing successful. Generating HTML pages...")
        try:
            # Load config again, as main_entry doesn't return it
            config = RssBuddyConfig.from_environment()
            # Call generate_pages with the loaded config
            generate_pages(config=config, docs_dir="docs") # Default docs_dir
            print("Successfully generated HTML pages in docs/ directory.")
        except ValueError as e:
            print(f"Configuration Error during page generation: {e}", file=sys.stderr)
            exit_code = 1
        except Exception as e:
            print(f"Error generating pages: {e}", file=sys.stderr)
            exit_code = 1 # Ensure failure code is set

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
