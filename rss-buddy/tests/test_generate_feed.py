import pytest
from datetime import datetime
from typing import List

from rss_buddy.logics.generate_feed import generate_feed
from rss_buddy.models import Feed, Item
from .test_utils import generate_test_item, generate_test_feed

@pytest.fixture
def digest_item() -> Item:
    return Item(
        title="Digest Item",
        link="",
        pub_date=datetime(2021, 1, 4),
        description="Test Digest Description",
        guid="test-guid-4"
    )

@pytest.mark.parametrize(
    "number_of_passed_items, expected_number_of_items",
    [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4)
    ]
)
def test_generate_feed(
        digest_item: Item,
        number_of_passed_items: int,
        expected_number_of_items: int
    ):
    passed_items = [
        generate_test_item(1),
        generate_test_item(2),
        generate_test_item(3)
    ]
    needed_passed_items = passed_items[:number_of_passed_items]

    feed = generate_feed(
        original_feed=generate_test_feed(items=passed_items),
        passed_item_guids=[item.guid for item in needed_passed_items],
        digest_item=digest_item
    )

    assert len(feed.items) == expected_number_of_items
    assert feed.items[-1] == digest_item