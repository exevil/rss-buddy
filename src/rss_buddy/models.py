"""Data models for representing RSS articles and page generation data."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Article:
    """Represents a single article processed from an RSS feed."""

    id: str  # Unique identifier (e.g., hash of link or guid)
    title: str
    link: str
    summary: str
    published_date: Optional[datetime]
    processed_date: Optional[datetime] = None  # When RSS Buddy processed/classified it
    status: Optional[str] = None  # 'processed' or 'digest'


@dataclass
class FeedDisplayData:
    """Data required to render the HTML page for a single feed."""

    url: str  # Original feed URL
    title: str
    processed_items: List[Article] = field(default_factory=list)
    digest_items: List[Article] = field(default_factory=list)  # Items to be summarized
    ai_digest_summary: Optional[str] = None  # The generated summary text/HTML
    last_updated_display: str = "Never"  # Display-friendly string for latest item date


@dataclass
class IndexFeedInfo:
    """Metadata for a single feed shown on the index page."""

    title: str
    filename: str  # e.g., feed_My_Feed.html
    processed_count: int
    digest_count: int
    original_url: str


@dataclass
class IndexDisplayData:
    """Data required to render the main index.html page."""

    feeds: List[IndexFeedInfo] = field(default_factory=list)
    generation_time_display: str = ""  # Display-friendly generation timestamp
