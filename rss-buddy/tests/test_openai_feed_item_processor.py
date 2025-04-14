import pytest
from unittest.mock import patch, MagicMock

from rss_buddy.logics.openai_feed_item_processor import OpenAIFeedItemProcessor
from .test_utils import generate_test_item

sample_item = generate_test_item(1)

@pytest.mark.parametrize(
    "response_int, expected_passed_filter, expected_error",
    [
        (1, True, None),
        (0, False, None),
        (3, None, ValueError)
    ]
)
def test_process_item(response_int, expected_passed_filter, expected_error):
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
        client=openai_mock
    )

    if expected_error is None:
        processed_item = processor.process(sample_item)
        assert processed_item.passed_filter == expected_passed_filter
    else:
        with pytest.raises(expected_error):
            processor.process(sample_item)
