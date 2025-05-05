import pytest
from unittest.mock import patch, MagicMock

from rss_buddy.logics.openai_feed_item_processor import OpenAIFeedItemProcessor
from .test_utils import generate_test_item

sample_item = generate_test_item(1)

@pytest.mark.parametrize(
    "has_item_criteria, response_int, expected_passed_filter",
    [
        (False, 1, True),
        (False, 0, True),
        (False, 3, True),
        (True, 1, True),
        (True, 0, False),
        (True, 3, True)
    ]
)
def test_process_item(has_item_criteria, response_int, expected_passed_filter):
    openai_mock = MagicMock()
    openai_mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content=str(response_int))
            )
        ]
    )

    processor = OpenAIFeedItemProcessor(
        openai_api_key="test_api_key",
        item_filter_criteria="test_item_criteria" if has_item_criteria else None,
        client=openai_mock
    )

    is_passed_filter = processor.is_passed_filter(sample_item)
    assert is_passed_filter == expected_passed_filter
