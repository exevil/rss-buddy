from typing import List

from rss_buddy.models import Feed, FeedCredentials, FeedMetadata, Item

def generate_feed(
    credentials: FeedCredentials,
    metadata: FeedMetadata,
    passed_items: List[Item],
    digest_item: Item
) -> Feed:
    """
    Generate a feed from processed data.
    """
    return Feed(
        credentials=credentials,
        metadata=metadata,
        items=passed_items + [digest_item]
    )