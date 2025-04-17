from typing import List, Optional
import logging

from rss_buddy.models import Feed, FeedCredentials, FeedMetadata, Item

def generate_feed(
    credentials: FeedCredentials,
    metadata: FeedMetadata,
    passed_items: List[Item],
    digest_item: Optional[Item]
) -> Feed:
    """
    Generate a feed from processed data.
    """
    logging.info(f"Generating feed for {metadata.title}, {len(passed_items)} items, digest item exists: {digest_item is not None}")

    items = passed_items
    if digest_item:
        items = items + [digest_item]
        
    return Feed(
        credentials=credentials,
        metadata=metadata,
        items=items
    )