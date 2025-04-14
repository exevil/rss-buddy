import pytest
from datetime import datetime
from typing import List

from rss_buddy.logics.generate_digest import generate_digest
from rss_buddy.models import Item   
from .test_utils import generate_test_item

@pytest.fixture
def items() -> List[Item]:
    return [
        generate_test_item(1, datetime(2025, 4, 1)),
        generate_test_item(2, datetime(2025, 4, 2)),
        generate_test_item(3, datetime(2025, 4, 3))
    ]

@pytest.mark.parametrize(
    "number_of_items, expected_title, expected_link, expected_pub_date, expected_description",
    [
        (
            1, 
            "Digest of 1 item", 
            "", 
            datetime(2025, 4, 1), 
            (
                "<a href=\"https://example.com/test-item-1\">Test Item 1</a>"
                "Test Description 1"
            )
        ),
        (
            2, 
            "Digest of 2 items", 
            "", 
            datetime(2025, 4, 2), 
            (
                "<a href=\"https://example.com/test-item-1\">Test Item 1</a>"
                "Test Description 1"
                "<a href=\"https://example.com/test-item-2\">Test Item 2</a>"
                "Test Description 2"
            )
        ),
        (
            3, 
            "Digest of 3 items", 
            "", 
            datetime(2025, 4, 3), 
            (
                "<a href=\"https://example.com/test-item-1\">Test Item 1</a>"
                "Test Description 1"
                "<a href=\"https://example.com/test-item-2\">Test Item 2</a>"
                "Test Description 2"
                "<a href=\"https://example.com/test-item-3\">Test Item 3</a>"
                "Test Description 3"
            )
        )
    ]
)

def test_generate_digest(
    items: List[Item], 
    number_of_items: int,
    expected_title: str, 
    expected_link: str, 
    expected_pub_date: datetime, 
    expected_description: str
):
    items = items[:number_of_items]
    
    digest_item = generate_digest(items)
    
    assert digest_item.title == expected_title
    assert digest_item.link == expected_link
    assert digest_item.pub_date == expected_pub_date
    assert digest_item.description == expected_description