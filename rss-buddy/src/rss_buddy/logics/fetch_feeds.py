import requests
import feedparser
from typing import List
from email.utils import parsedate_to_datetime

from rss_buddy.models import Feed, FeedMetadata, FeedCredentials, Item

def fetch_feeds(
    credentials: List[FeedCredentials],
    days_lookback: int
) -> List[Feed]:
    """
    Fetch the RSS feeds.
    """
    feeds = []
    for credential in credentials:
        response = requests.get(credential.url)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch the RSS feed from {credential.url}. Code: {response.status_code}")
        
        parsed_feed = feedparser.parse(response.text)

        # Metadata.
        metadata = FeedMetadata(
            title=parsed_feed.feed.title,
            link=parsed_feed.feed.link,
            description=parsed_feed.feed.description,
            language=parsed_feed.feed.language,
            last_build_date=parsedate_to_datetime(parsed_feed.feed.updated),
            ttl=int(parsed_feed.feed.ttl),
            docs=parsed_feed.feed.docs,
            pub_date=parsedate_to_datetime(parsed_feed.feed.published),
        )

        # Items.
        items = []
        for item in parsed_feed.entries:
            items.append(Item(
                title=item.title,
                link=item.link,
                description=item.description,
                pub_date=parsedate_to_datetime(item.published),
                guid=item.guid,
            ))
            
        # Feed.
        feed = Feed(
            credentials=credential,
            metadata=metadata,
            items=items,
        )
        feeds.append(feed)
        
    return feeds