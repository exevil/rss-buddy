import os
import json
import logging
from typing import Optional, List
from argparse import ArgumentParser, Namespace as ArgNamespace
from dotenv import load_dotenv
from rss_buddy.models import FeedCredentials, AppEnvSettings, AppConfig

def parse_cli_arguments() -> ArgNamespace:
    """
    Parse the command line arguments.
    """
    parser = ArgumentParser(description="RSS Buddy")
    parser.add_argument(
        "-f", "--feed-credentials",
        action="append",
        type=str,
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
    parser.add_argument(
        "-s", "--state-file-name",
        type=str,
        help="The JSON file name to load/save the state relative inside the output directory.",
    )
    return parser.parse_args()

def parse_feed_credentials(cli_args: Optional[ArgNamespace] = None) -> List[FeedCredentials]:
    """
    Parse the feed credentials.
    """
    credential_splits = []
    # Load from CLI arguments if provided.
    if cli_args and cli_args.feed_credentials:
        for credential in cli_args.feed_credentials:
            split = credential.split(" : ")
            credential_splits.append(split)
    else:
        # Get all environment variables that start with "FEED_CREDENTIALS_".
        variables = os.environ.items()
        for key, value in variables:
            if key.startswith("FEED_CREDENTIALS_"):
                split = value.split("\n", maxsplit=1)
                credential_splits.append(split)
    # Parse each credential split.
    feed_credentials = []
    for split in credential_splits:
        if len(split) != 2:
            logging.warning(f"Invalid feed credential: {split}, skipping...")
            continue
        url, filter_criteria = split
        feed_credentials.append(
            FeedCredentials(
                url=url.strip(),
                filter_criteria=filter_criteria.strip(),
            )
        )
    return feed_credentials

def load_config() -> AppConfig:
    """
    Load the configuration.
    """
    load_dotenv(verbose=True)
    cli_args = parse_cli_arguments()
    env_settings = AppEnvSettings()
    feed_credentials = parse_feed_credentials(cli_args)

    if len(feed_credentials) == 0:
        raise ValueError("No feed credentials provided.")
    
    openai_api_key = cli_args.openai_api_key or env_settings.openai_api_key
    if openai_api_key is None:
        raise ValueError("No OpenAI API key provided.")

    return AppConfig(
        global_filter_criteria=cli_args.global_filter_criteria 
            or env_settings.global_filter_criteria,
        days_lookback=cli_args.days_lookback
            or env_settings.days_lookback,
        openai_api_key=openai_api_key,
        output_dir=cli_args.output_dir
            or env_settings.output_dir
            or "./output",
        state_file_name=cli_args.state_file_name
            or env_settings.state_file_name
            or "state.json",
        feed_credentials=feed_credentials,
    )