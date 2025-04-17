import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from rss_buddy.models import Feed, ProcessedFeed, ProcessedItem
from rss_buddy.logics.process_feed import process_feed
from .test_utils import generate_test_item, generate_test_feed_metadata, generate_test_feed_credentials

@pytest.fixture
def feed():
    return Feed(
        credentials=generate_test_feed_credentials(),
        metadata=generate_test_feed_metadata(
            last_build_date=datetime.now(),
        ),
        items=[
            generate_test_item(1, datetime.now()),
            generate_test_item(2, datetime.now() - timedelta(days=2)),
            generate_test_item(3, datetime.now() - timedelta(days=4))
        ]
    )

@pytest.mark.parametrize(
    "days_lookback, passed_filter, expected_passed_items, expected_failed_items", 
    [
        (1, True, 1, 0),
        (3, True, 2, 0),
        (5, True, 3, 0),
        (1, False, 0, 1),
        (3, False, 0, 2),
        (5, False, 0, 3)
    ]
)
@patch("rss_buddy.logics.process_feed.FeedItemProcessor")
def test_process_feed(
    MockFeedItemProcessorClass, 
    feed, 
    days_lookback, 
    passed_filter, 
    expected_passed_items, 
    expected_failed_items
    ):
    mock_instance = MockFeedItemProcessorClass.return_value
    mock_instance.process.return_value = ProcessedItem(
        item=generate_test_item(1, datetime.now()),
        passed_filter=passed_filter
    )

    processed_feed = process_feed(
        feed=feed,
        item_processor=mock_instance,
        days_lookback=days_lookback
    )

    assert len(processed_feed.passed_items) == expected_passed_items
    assert len(processed_feed.failed_items) == expected_failed_items
