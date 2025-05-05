from typing import List, Optional
import logging
from datetime import datetime
from rss_buddy.models import Item, Feed, ItemGUID

def generate_digest(
        feed: Feed, # The feed to generate the digest for
        item_guids: List[ItemGUID] # GUIDs of items to include in the digest
    ) -> Optional[Item]:
    """
    Generate a single digest item from a list of items.
    """
    if not item_guids:
        logging.warning("No items to generate digest from. Skipping.")
        return None

    logging.info(f"Generating digest for {len(item_guids)} items")
    items = []
    description = ""
    for item_guid in item_guids:
        # Get the item from the feed
        item = next((item for item in feed.items if item.guid == item_guid), None)
        if not item:
            logging.warning(f"Item with GUID {item_guid} not found in feed. Skipping.")
            continue
        items.append(item)
        # Truncate description to 100 characters
        item_description = item.description
        if len(item_description) > 100:
            item_description = item_description[:100] + "..."
        
        description += (
            f"<a href=\"{item.link}\">{item.title}</a>"
            f"{item_description}"
        )
    
    if not items:
        logging.warning("No items to generate digest from. Skipping.")
        return None
        
    items_label = "item" if len(items) == 1 else "items"
    title = f"Digest of {len(items)} {items_label}"

    logging.info(f"Digest generated: {title}")
    return Item(
        title=title,
        link=f"",
        pub_date=items[-1].pub_date,
        description=description,
        guid=f"digest-{items[-1].guid}"
    )