import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from rss_buddy.models import Feed, ProcessedFeed
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
            generate_test_item(1, datetime.now(timezone.utc)),
            generate_test_item(2, datetime.now(timezone.utc) - timedelta(days=2)),
            generate_test_item(3, datetime.now(timezone.utc) - timedelta(days=4))
        ]
    )

@pytest.mark.parametrize(
    "days_lookback, passed_filter, expected_passed_items_count, expected_failed_items_count", 
    [
        (1, True, 1, 0),
        (3, True, 2, 0),
        (5, True, 3, 0),
        (1, False, 0, 1),
        (3, False, 0, 2),
        (5, False, 0, 3)
    ]
)
def test_process_feed(
    feed, 
    days_lookback, 
    passed_filter, 
    expected_passed_items_count, 
    expected_failed_items_count
    ):

    processed_feed = process_feed(
        feed=feed,
        is_passed_filter=lambda item: passed_filter,
        days_lookback=days_lookback
    )

    assert len(processed_feed.result.passed_item_guids) == expected_passed_items_count
    assert len(processed_feed.result.failed_item_guids) == expected_failed_items_count
