from typing import Optional, List
from datetime import datetime

from models import Item, FeedMetadata, FeedCredentials, Feed

def generate_test_item(
        index: int,
        pub_date: Optional[datetime] = None
    ) -> Item:
    """
    Generate a test item with the given index and pub_date.
    """
    return Item(
        title=f"Test Item {index}",
        link=f"https://example.com/test-item-{index}",
        pub_date=pub_date if pub_date else datetime(2021, 1, index + 1),
        description=f"Test Description {index}",
        guid=f"test-guid-{index}"
    )

def generate_test_feed_metadata(
        last_build_date: Optional[datetime] = None
) -> FeedMetadata:
    """
    Generate a test feed metadata with the given last_build_date.
    """
    return FeedMetadata(
        title="Test Feed",
        link="https://example.com/feed",
        description="Test Feed Description",
        language="en-us",
        last_build_date=last_build_date if last_build_date else datetime.now()
    )

def generate_test_feed_credentials() -> FeedCredentials:
    """
    Generate a test feed credentials.
    """
    return FeedCredentials(
        url="https://example.com/feed",
        filter_criteria="test_filter_criteria"
    )

def generate_test_feed(
        items: List[Item],
        credentials: FeedCredentials = generate_test_feed_credentials(),
        metadata: FeedMetadata = generate_test_feed_metadata(),
) -> Feed:
    """
    Generate a test feed with the given items.
    """
    return Feed(
        credentials=credentials,
        metadata=metadata,
        items=items
    )
