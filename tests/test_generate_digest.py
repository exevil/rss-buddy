import pytest
from datetime import datetime
import textwrap
from typing import List

from rss_buddy.generate_digest import generate_digest
from models import Item
from .test_utils import generate_test_item, generate_test_feed

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
            textwrap.dedent("""
            <a href=\"https://example.com/test-item-1\">Test Item 1</a>
            <p>Test Description 1</p>
            """)
        ),
        (
            2, 
            "Digest of 2 items", 
            "", 
            datetime(2025, 4, 2), 
            textwrap.dedent("""
            <a href=\"https://example.com/test-item-1\">Test Item 1</a>
            <p>Test Description 1</p>
                            
            <a href=\"https://example.com/test-item-2\">Test Item 2</a>
            <p>Test Description 2</p>
            """)
        ),
        (
            3, 
            "Digest of 3 items", 
            "", 
            datetime(2025, 4, 3), 
            textwrap.dedent("""
            <a href=\"https://example.com/test-item-1\">Test Item 1</a>
            <p>Test Description 1</p>
                            
            <a href=\"https://example.com/test-item-2\">Test Item 2</a>
            <p>Test Description 2</p>
                            
            <a href=\"https://example.com/test-item-3\">Test Item 3</a>
            <p>Test Description 3</p>
            """)
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
    
    digest_item = generate_digest(
        feed=generate_test_feed(items=items),
        item_guids=[item.guid for item in items]
    )

    assert digest_item is not None
    assert digest_item.title == expected_title
    assert digest_item.link == expected_link
    assert digest_item.pub_date == expected_pub_date
    assert digest_item.description == expected_description