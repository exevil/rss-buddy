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

    def append_digest(
            current_date: date,
            items: List[Item],
        ) -> None:
        """
        Append a digest to the output.
        """
        date_str = current_date.strftime('%d %B %Y')
        output_items.append(DigestItem(
            title=f"Daily Digest for {date_str}",
            description=f"Daily Digest for {date_str}",
            pub_date=datetime.combine(current_date, datetime.min.time()), # The pub date is the start of the day to appear under the passed items in the feed.
            items=items,
            guid=f"daily-digest-{date_str}-{len(items)}" # GUID is updated when the new items are added.
        ))
        daily_digest_items.clear()

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
            append_digest(current_date, daily_digest_items)
            daily_digest_items = [item]
            current_date = item_date
    # Add the last daily digest to the output.
    if len(daily_digest_items) > 0 and current_date is not None:
        append_digest(current_date, daily_digest_items)
        
    return OutputFeed(
        feed=processed_feed.feed,
        items=output_items
    )