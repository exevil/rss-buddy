from datetime import datetime, timedelta, timezone
import logging
from typing import Callable

from models import Feed, Item, ProcessedFeed

def process_feed(
    feed: Feed, # The RSS feed to process
    is_passed_filter: Callable[[Item], bool], # A function to check if an item passed the filter
    days_lookback: int # The number of days to look back for each feed
) -> ProcessedFeed:
    """
    Process the RSS feed.
    """
    logging.info(f"Processing feed: {feed.metadata.title}")

    # Process the items
    passed_item_guids = []
    failed_item_guids = []
    for item in feed.items:
        # Skip items older than the lookback period
        lookback_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
        if item.pub_date < lookback_date:
            logging.info(f"Old item: \"{item.title}\" is more than {days_lookback} days old. Skipping.")
            continue

        # Process the item
        passed_filter = is_passed_filter(item)
        if passed_filter:
            logging.info(f"Passed filter: \"{item.title}\"")
            passed_item_guids.append(item.guid)
        else:
            logging.info(f"Failed filter: \"{item.title}\"")
            failed_item_guids.append(item.guid)

    logging.info(f"Feed successfully processed: {feed.metadata.title}. {len(passed_item_guids)} items passed, {len(failed_item_guids)} items failed")
    # Return the processed feed
    return ProcessedFeed(
        feed=feed,
        passed_item_guids=passed_item_guids,
        failed_item_guids=failed_item_guids
    )
