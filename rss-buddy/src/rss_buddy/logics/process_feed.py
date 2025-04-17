from datetime import datetime, timedelta, timezone
import logging

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
    logging.info(f"Processing feed: {feed.metadata.title}")

    # Process the items
    passed_items = []
    failed_items = []
    for item in feed.items:
        # Skip items older than the lookback period
        lookback_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
        if item.pub_date < lookback_date:
            continue

        # Process the item
        processed_item = item_processor.process(item)
        if processed_item.passed_filter:
            logging.info(f"Passed filter: {item.title}")
            passed_items.append(item)
        else:
            logging.info(f"Failed filter: {item.title}")
            failed_items.append(item)

    logging.info(f"Feed successfully processed: {feed.metadata.title}. {len(passed_items)} items passed, {len(failed_items)} items failed")
    # Return the processed feed
    return ProcessedFeed(
        feed=feed,
        passed_items=passed_items,
        failed_items=failed_items
    )
