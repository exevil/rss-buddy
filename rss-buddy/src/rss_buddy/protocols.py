from typing import Protocol

from rss_buddy.models import Feed, Item, ProcessedItem

class FeedItemProcessor(Protocol):
    """
    Feed item processor.
    """

    def process(self, item: Item) -> ProcessedItem:
        """
        Process the item.
        """
        ...
