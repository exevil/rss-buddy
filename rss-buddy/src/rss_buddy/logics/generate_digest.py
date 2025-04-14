from typing import List

from rss_buddy.models import Item

def generate_digest(items: List[Item]) -> Item:
    """
    Generate a single digest item from a list of items.
    """
    description = ""
    for item in items:
        # Truncate description to 100 characters
        item_description = item.description
        if len(item_description) > 100:
            item_description = item_description[:100] + "..."
        
        description += (
            f"<a href=\"{item.link}\">{item.title}</a>"
            f"{item_description}"
        )
        
    items_label = "item" if len(items) == 1 else "items"
    title = f"Digest of {len(items)} {items_label}"

    return Item(
        title=title,
        link=f"",
        pub_date=items[-1].pub_date,
        description=description,
        guid=f"digest-{items[-1].guid}"
    )