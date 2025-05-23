from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
# GUID of the last processed item.
ItemGUID = str
# Path to the output file.
OutputPath = str

### Item

class Item(BaseModel):
    """
    Item in an RSS feed.
    """
    title: str # The title of the item.
    link: str # The URL of the item.
    pub_date: datetime # The date and time the item was published.
    description: str # The full content of the item.
    guid: str # The unique identifier for the item.

class DigestItem(BaseModel):
    """
    Digest of items in an RSS feed.
    """
    title: str # The title of the digest.
    description: str # The description of the digest.
    pub_date: datetime # The date and time the digest was published.
    items: List[Item] # A list of items in the digest.
    guid: str # The unique identifier for the digest.

OutputItem = Union[Item, DigestItem]

### Feed

class FeedCredentials(BaseModel):
    """
    Initial credentials for an RSS feed.
    """
    url: str # The URL of the RSS feed.
    filter_criteria: Optional[str] # A criteria to filter the feed.

class FeedMetadata(BaseModel):
    """
    Metadata for an RSS feed.
    """
    title: str # The title of the feed.
    link: str # The URL of the feed.
    description: str # The description of the feed.
    language: str # The language of the feed.
    last_build_date: datetime # The date and time the feed was last built.

class Feed(BaseModel):
    """
    RSS feed.
    """
    credentials: FeedCredentials # Initial credentials for the feed.
    metadata: FeedMetadata # Metadata for the feed.
    items: List[Item] # A list of items in the feed.

class ProcessedFeed(BaseModel):
    """
    Processed RSS feed with its essential properties.
    """
    feed: Feed # The original RSS feed.
    passed_item_guids: List[ItemGUID] # GUIDs of items that passed the filter.
    failed_item_guids: List[ItemGUID] # GUIDs of items that failed the filter.

class OutputFeed(BaseModel):
    """
    Output RSS feed.
    """
    feed: Feed # The original RSS feed.
    items: List[OutputItem] # A list of the output items in the feed.

### Output

class OutputType(BaseModel):
    """
    An output type.
    """
    template_name: str # The name of the template to use.
    relative_output_path: OutputPath # The relative path inside the output folder where the output will be saved.

    model_config = ConfigDict(
        frozen = True,
    )

### App

class AppEnvSettings(BaseSettings):
    """
    App settings from environment variables.
    """
    global_filter_criteria: Optional[str] = None # A criteria to filter every feed additionally to the feed's own filter.
    days_lookback: int = 1 # The number of days to look back for each feed.
    openai_api_key: Optional[str] = None # The API key for the OpenAI API.
    output_dir: Optional[str] = None # The directory to save the output.
    state_file_name: Optional[str] = None # The name of the state file to load/save relative to the output directory.

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )

class AppConfig(BaseModel):
    """
    Global app config.
    """
    global_filter_criteria: Optional[str] = None # A criteria to filter every feed additionally to the feed's own filter.
    days_lookback: int # The number of days to look back for each feed.
    openai_api_key: str # The API key for the OpenAI API.
    output_dir: str # The directory to save the output.
    state_file_name: str # The name of the state file to load/save relative to the output directory.
    feed_credentials: List[FeedCredentials] # Feed credentials.

    model_config = ConfigDict(
        frozen = True,
    )
