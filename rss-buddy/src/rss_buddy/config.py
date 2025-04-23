import os
import json
import logging
from typing import Optional
from argparse import ArgumentParser, Namespace as ArgNamespace
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

def load_config(cli_args: Optional[ArgNamespace] = None) -> AppConfig:
    """
    Load the configuration for the RSS feed.
    """

    # Load test environment if available.
    if os.getenv("DEBUG") == "1":
        test_env_path = os.path.join(os.path.dirname(__file__), "../../.env.json")
        if os.path.exists(test_env_path):
            with open(test_env_path, "r") as f:
                os.environ.update(json.load(f))
                

    # Feed credentials.
    feed_credentials = []
    if cli_args and cli_args.feed_credentials:
        # Load from CLI arguments.
        for credential in cli_args.feed_credentials:
            url, filter_criteria = credential.split(":").strip()
            feed_credentials.append(FeedCredentials(url=url, filter_criteria=filter_criteria))
    else:
        # Expects string in the format `feed_url : filter_criteria` with new lines as item separators.
        credentials_raw = os.getenv("FEED_CREDENTIALS")
        if not credentials_raw:
            raise ValueError("FEED_CREDENTIALS is not set")
        credential_rows = credentials_raw.split("\n")
        # Parse each credential row.
        for credential_row in credential_rows:
            split = credential_row.split(" : ")
            # Parse url.
            url = split[0].strip() if len(split) > 0 else None
            if not url:
                logging.warning(f"No url found in credential row: {credential_row}, skipping...")
                continue
            # Parse filter criteria.
            filter_criteria = split[1].strip() if len(split) > 1 else None
            if not filter_criteria:
                logging.warning(f"No filter criteria found in credential row: {credential_row}, only global filter criteria will be applied to this feed")
            # Append to feed credentials.
            feed_credentials.append(FeedCredentials(url=url, filter_criteria=filter_criteria))
    
    # Global filter criteria.
    if cli_args and cli_args.global_filter_criteria:
        global_filter_criteria = cli_args.global_filter_criteria
    elif (env_global_filter_criteria := os.getenv("GLOBAL_FILTER_CRITERIA")) is not None:
        global_filter_criteria = env_global_filter_criteria
    else:
        global_filter_criteria = None
        logging.warning("GLOBAL_FILTER_CRITERIA is not set, only feed's own filter criteria will be applied")
    
    # Days lookback.
    if cli_args and cli_args.days_lookback:
        days_lookback = cli_args.days_lookback
    elif (env_days_lookback := os.getenv("DAYS_LOOKBACK")) is not None:
        days_lookback = int(env_days_lookback)
    else:
        days_lookback = 1
        logging.warning(f"DAYS_LOOKBACK is not set, using {days_lookback}")

    # OpenAI API key.
    if cli_args and cli_args.openai_api_key:
        openai_api_key = cli_args.openai_api_key
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        
    # Output directory.
    if cli_args and cli_args.output_dir:
        output_dir = cli_args.output_dir
    elif (env_output_dir := os.getenv("OUTPUT_DIR")) is not None:
        output_dir = env_output_dir
    else:
        output_dir = "./output"
        logging.warning(f"OUTPUT_DIR is not set, using {output_dir}")

    return AppConfig(
        feed_credentials=feed_credentials,
        global_filter_criteria=global_filter_criteria,
        days_lookback=days_lookback,
        openai_api_key=openai_api_key,
        output_dir=output_dir,
    )