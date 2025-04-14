from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Item:
    """
    Item in an RSS feed.
    """
    title: str # The title of the item.
    link: str # The URL of the item.
    pub_date: datetime # The date and time the item was published.
    description: str # The full content of the item.
    guid: str # The unique identifier for the item.

@dataclass
class ProcessedItem:
    """
    Processed item in an RSS feed.
    """
    item: Item # The item in the RSS feed.
    passed_filter: bool # Whether the item passed the filter.

@dataclass
class FeedCredentials:
    """
    Initial credentials for an RSS feed.
    """
    url: str # The URL of the RSS feed.
    filter_criteria: str # A criteria to filter the feed.

@dataclass
class FeedMetadata:
    """
    Metadata for an RSS feed.
    """
    title: str # The title of the feed.
    link: str # The URL of the feed.
    description: str # The description of the feed.
    language: str # The language of the feed.
    last_build_date: datetime # The date and time the feed was last built.
    ttl: int # The time to live of the feed.
    docs: str # The documentation of the feed.
    pub_date: datetime # The date and time the feed was published.

@dataclass
class Feed:
    """
    RSS feed.
    """
    credentials: FeedCredentials # Initial credentials for the feed.
    metadata: FeedMetadata # Metadata for the feed.
    items: List[Item] # A list of items in the feed.

@dataclass
class ProcessedFeed:
    """
    Processed RSS feed with its essential properties.
    """
    feed: Feed # The original RSS feed.
    passed_items: List[Item] # A list of items that passed the filter.
    failed_items: List[Item] # A list of items that failed the filter.

@dataclass(frozen=True)
class OutputType:
    """
    An output type.
    """
    template_name: str # The name of the template to use.
    relative_output_path: str # The relative path inside the output folder where the output will be saved.

@dataclass
class AppConfig:
    """
    Global App Configuration.
    """
    feed_credentials: List[FeedCredentials] # The credentials for each feed.
    global_filter_criteria: str # A criteria to filter every feed additionally to the feed's own filter.
    days_lookback: int # The number of days to look back for each feed.
    openai_api_key: str # The API key for the OpenAI API.
    output_dir: str # The directory to save the output.