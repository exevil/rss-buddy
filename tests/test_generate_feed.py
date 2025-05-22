import pytest
from datetime import datetime, date
from typing import List

from rss_buddy.generate_feed import generate_feed
from models import ProcessedFeed, OutputFeed, Item, DigestItem
from .test_utils import generate_test_item, generate_test_feed

@pytest.mark.parametrize(
    "passed_item_indices, failed_item_indices, expected_passed_count, expected_digest_count",
    [
        # All items pass - no digests created
        ([1, 2, 3], [], 3, 0),
        # Some items pass, some fail on same day - one digest created
        ([1], [2, 3], 1, 1),
        # No items pass - one digest created
        ([], [1, 2, 3], 0, 1),
        # Mixed scenario with items on different days
        ([1, 3], [2], 2, 1),
    ]
)
def test_generate_feed_basic_scenarios(
    passed_item_indices: List[int],
    failed_item_indices: List[int], 
    expected_passed_count: int,
    expected_digest_count: int
):
    """Test basic scenarios of feed generation with passed and failed items."""
    # Create items with same date (2021-01-02) so they group into one digest
    all_items = []
    for i in passed_item_indices + failed_item_indices:
        all_items.append(generate_test_item(i, pub_date=datetime(2021, 1, 2)))
    
    # Create ProcessedFeed
    processed_feed = ProcessedFeed(
        feed=generate_test_feed(items=all_items),
        passed_item_guids=[f"test-guid-{i}" for i in passed_item_indices],
        failed_item_guids=[f"test-guid-{i}" for i in failed_item_indices]
    )
    
    # Generate output feed
    output_feed = generate_feed(processed_feed)
    
    # Verify output structure
    assert isinstance(output_feed, OutputFeed)
    assert output_feed.feed == processed_feed.feed
    
    # Count passed items and digests
    passed_items = [item for item in output_feed.items if isinstance(item, Item)]
    digest_items = [item for item in output_feed.items if isinstance(item, DigestItem)]
    
    assert len(passed_items) == expected_passed_count
    assert len(digest_items) == expected_digest_count
    
    # Verify digest content if any digests were created
    if expected_digest_count > 0:
        digest = digest_items[0]
        assert len(digest.items) == len(failed_item_indices)
        assert digest.title == "Daily Digest for 02 January 2021"
        assert digest.guid == f"daily-digest-02 January 2021-{len(failed_item_indices)}"

def test_generate_feed_multiple_days():
    """Test feed generation with items spanning multiple days."""
    # Create items on different days
    items = [
        generate_test_item(1, pub_date=datetime(2021, 1, 1)),  # Day 1
        generate_test_item(2, pub_date=datetime(2021, 1, 1)),  # Day 1  
        generate_test_item(3, pub_date=datetime(2021, 1, 2)),  # Day 2
        generate_test_item(4, pub_date=datetime(2021, 1, 2)),  # Day 2
        generate_test_item(5, pub_date=datetime(2021, 1, 3)),  # Day 3
    ]
    
    # Item 1 and 3 pass, others fail
    processed_feed = ProcessedFeed(
        feed=generate_test_feed(items=items),
        passed_item_guids=["test-guid-1", "test-guid-3"],
        failed_item_guids=["test-guid-2", "test-guid-4", "test-guid-5"]
    )
    
    output_feed = generate_feed(processed_feed)
    
    # Should have 2 passed items and 3 digests (one for each day with failed items)
    passed_items = [item for item in output_feed.items if isinstance(item, Item)]
    digest_items = [item for item in output_feed.items if isinstance(item, DigestItem)]
    
    assert len(passed_items) == 2
    assert len(digest_items) == 3
    
    # Verify digest dates and content
    digest_dates = [digest.pub_date.date() for digest in digest_items]
    expected_dates = [date(2021, 1, 1), date(2021, 1, 2), date(2021, 1, 3)]
    
    # Sort both lists to compare
    digest_dates.sort()
    expected_dates.sort()
    assert digest_dates == expected_dates

def test_generate_feed_empty_feed():
    """Test feed generation with no items."""
    processed_feed = ProcessedFeed(
        feed=generate_test_feed(items=[]),
        passed_item_guids=[],
        failed_item_guids=[]
    )
    
    output_feed = generate_feed(processed_feed)
    
    assert isinstance(output_feed, OutputFeed)
    assert len(output_feed.items) == 0

def test_generate_feed_all_items_pass():
    """Test feed generation where all items pass the filter."""
    items = [
        generate_test_item(1, pub_date=datetime(2021, 1, 1)),
        generate_test_item(2, pub_date=datetime(2021, 1, 2)),
        generate_test_item(3, pub_date=datetime(2021, 1, 3)),
    ]
    
    processed_feed = ProcessedFeed(
        feed=generate_test_feed(items=items),
        passed_item_guids=["test-guid-1", "test-guid-2", "test-guid-3"],
        failed_item_guids=[]
    )
    
    output_feed = generate_feed(processed_feed)
    
    # Should have 3 passed items and no digests
    passed_items = [item for item in output_feed.items if isinstance(item, Item)]
    digest_items = [item for item in output_feed.items if isinstance(item, DigestItem)]
    
    assert len(passed_items) == 3
    assert len(digest_items) == 0

def test_generate_feed_sorting():
    """Test that items are sorted by publication date (newest first)."""
    items = [
        generate_test_item(1, pub_date=datetime(2021, 1, 1)),
        generate_test_item(2, pub_date=datetime(2021, 1, 3)),  # Newest
        generate_test_item(3, pub_date=datetime(2021, 1, 2)),
    ]
    
    processed_feed = ProcessedFeed(
        feed=generate_test_feed(items=items),
        passed_item_guids=["test-guid-1", "test-guid-2", "test-guid-3"],
        failed_item_guids=[]
    )
    
    output_feed = generate_feed(processed_feed)
    
    # Items should be sorted by date (newest first)
    passed_items = [item for item in output_feed.items if isinstance(item, Item)]
    assert len(passed_items) == 3
    
    # Check that items are in correct order (newest first)
    assert passed_items[0].guid == "test-guid-2"  # 2021-01-03
    assert passed_items[1].guid == "test-guid-3"  # 2021-01-02  
    assert passed_items[2].guid == "test-guid-1"  # 2021-01-01