import os
from typing import Optional
from argparse import ArgumentParser, Namespace as ArgNamespace
from dotenv import load_dotenv

from rss_buddy.models import AppConfig, FeedCredentials

def parse_cli_arguments() -> ArgNamespace:
    """
    Parse the command line arguments.
    """
    parser = ArgumentParser(description="RSS Buddy")
    parser.add_argument(
        "-f", "--feed-credentials",
        action="append",
        help="The credentials for the RSS feed in the `url : filter_criteria` format.",
    )
    parser.add_argument(
        "-c", "--global-filter-criteria",
        type=str,
        help="The criteria to filter every feed additionally to the feed's own filter.",
    )
    parser.add_argument(
        "-d", "--days-lookback",
        type=int,
        help="The number of days to look back for each feed.",
    )
    parser.add_argument(
        "-k", "--openai-api-key",
        type=str,
        help="The API key for the OpenAI API.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        help="The directory to save the output.",
    )
    return parser.parse_args()

def load_config(cli_args: ArgNamespace = ArgNamespace()) -> AppConfig:
    """
    Load the configuration for the RSS feed.
    """
    # Load environment variables.
    load_dotenv(verbose=True)

    # Feed credentials.
    feed_credentials = []
    if cli_args.feed_credentials:
        # Load from CLI arguments.
        for credential in cli_args.feed_credentials:
            url, filter_criteria = credential.split(":").strip()
            feed_credentials.append(FeedCredentials(url=url, filter_criteria=filter_criteria))
    else:
        # Expects string in the format `feed_url : filter_criteria` with new lines as item separators.
        credentials_raw = os.getenv("FEED_CREDENTIALS")
        if not credentials_raw:
            raise ValueError("FEED_CREDENTIALS is not set")
        credential_rows = credentials_raw.split("\\n")
        for credential_row in credential_rows:
            url, filter_criteria = [
                attr.strip() 
                for attr in credential_row.split(" : ")
            ]
            feed_credentials.append(FeedCredentials(url=url, filter_criteria=filter_criteria))
    
    # Global filter criteria.
    global_filter_criteria = os.getenv("GLOBAL_FILTER_CRITERIA")
    if not global_filter_criteria:
        raise ValueError("GLOBAL_FILTER_CRITERIA is not set")
    
    # Days lookback.
    if cli_args.days_lookback:
        days_lookback = cli_args.days_lookback
    else:
        days_lookback = os.getenv("DAYS_LOOKBACK")
        if not days_lookback:
            raise ValueError("DAYS_LOOKBACK is not set")

    # OpenAI API key.
    if cli_args.openai_api_key:
        openai_api_key = cli_args.openai_api_key
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        
    # Output directory.
    if cli_args.output_dir:
        output_dir = cli_args.output_dir
    else:
        output_dir = os.getenv("OUTPUT_DIR")
        if not output_dir:
            raise ValueError("OUTPUT_DIR is not set")

    return AppConfig(
        feed_credentials=feed_credentials,
        global_filter_criteria=global_filter_criteria,
        days_lookback=int(days_lookback),
        openai_api_key=openai_api_key,
        output_dir=output_dir,
    )