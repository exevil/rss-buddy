from typing import List, Optional
import logging
from datetime import date, datetime
from models import Feed, Item, ItemGUID, ProcessedFeed, OutputFeed, OutputItem, DigestItem

def generate_feed(
    processed_feed: ProcessedFeed, # The processed feed to generate the output for
) -> OutputFeed:
    """
    Generate a new feed from processed data.
    """
    logging.info(f"Generating feed for {processed_feed.feed.metadata.title}, {len(processed_feed.passed_item_guids)} passed items, {len(processed_feed.failed_item_guids)} failed items")

    # Sort feed items by day.
    processed_feed.feed.items.sort(
        key=lambda x: x.pub_date,
        reverse=True
    )
    # Iterate over the original feed items and create a digest for each day.
    output_items: List[OutputItem] = []
    current_date: Optional[date] = None
    daily_digest_items: List[Item] = []

    def append_digest_if_needed() -> None:
        """
        Append a digest to the output if there are items in the digest.
        """
        nonlocal current_date, daily_digest_items
        if (current_date is not None) and len(daily_digest_items) > 0:
            date_str = current_date.strftime('%d %B %Y')
            if len(daily_digest_items) > 0:
                output_items.append(DigestItem(
                    title=f"Daily Digest for {date_str}",
                    description=f"Daily Digest for {date_str}",
                    pub_date=datetime.combine(current_date, datetime.min.time()), # The pub date is the start of the day to appear under the passed items in the feed.
                    items=daily_digest_items,
                    guid=f"daily-digest-{date_str}-{len(daily_digest_items)}" # GUID is updated when the new items are added.
                ))
        # Clear data for the next cycle.
        daily_digest_items.clear()
        current_date = None

    # Iterate over the original feed items and create a digest for each day.
    for item in processed_feed.feed.items:
        item_date = item.pub_date.date()
        # Make sure the current date is set.
        if current_date is None:
            current_date = item_date
        # Add item as is if it passed the filter.
        if item.guid in processed_feed.passed_item_guids:
            output_items.append(item)
        # If not passed, add to daily digest.
        elif item_date == current_date:
            daily_digest_items.append(item)
        # If from a different day, finish the daily digest and start a new one with the current item.
        else:
            append_digest_if_needed()
            daily_digest_items = [item]
            current_date = item_date
            
    # Add the last daily digest to the output.
    append_digest_if_needed()
        
    return OutputFeed(
        feed=processed_feed.feed,
        items=output_items
    )