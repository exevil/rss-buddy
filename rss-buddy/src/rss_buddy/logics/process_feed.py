from datetime import datetime, timedelta

from rss_buddy.models import Feed, ProcessedFeed
from rss_buddy.protocols import FeedItemProcessor

def process_feed(
    feed: Feed,
    item_processor: FeedItemProcessor,
    days_lookback: int
) -> ProcessedFeed:
    """
    Process the RSS feed.
    """
    # Process the items
    passed_items = []
    failed_items = []
    for item in feed.items:
        # Skip items older than the lookback period
        lookback_date = datetime.now() - timedelta(days=days_lookback)
        if item.pub_date < lookback_date:
            continue
        # Process the item
        processed_item = item_processor.process(item)
        if processed_item.passed_filter:
            passed_items.append(item)
        else:
            failed_items.append(item)

    # Return the processed feed
    return ProcessedFeed(
        feed=feed,
        passed_items=passed_items,
        failed_items=failed_items
    )
