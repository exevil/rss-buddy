from typing import List, Optional
import logging

from models import Feed, FeedCredentials, FeedMetadata, Item, ItemGUID

def generate_feed(
    original_feed: Feed, # The original feed to generate the output for
    passed_item_guids: List[ItemGUID], # GUIDs of items to include in the feed
    digest_item: Optional[Item] # The digest item to include in the feed
) -> Feed:
    """
    Generate a feed from processed data.
    """
    logging.info(f"Generating feed for {original_feed.metadata.title}, {len(passed_item_guids)} items, digest item exists: {digest_item is not None}")

    items = []
    for item_guid in passed_item_guids:
        item = next(
            (item for item in original_feed.items if item.guid == item_guid),
            None
        )
        if not item:
            logging.warning(f"Item with GUID {item_guid} not found in feed. Skipping.")
            continue
        items.append(item)
    if digest_item:
        items += [digest_item]
        
    return Feed(
        credentials=original_feed.credentials,
        metadata=original_feed.metadata,
        items=items
    )