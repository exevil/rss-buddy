import pytest
import os
from datetime import datetime

from models import Feed, OutputType
from rss_buddy.generate_outputs import generate_outputs
from .test_utils import generate_test_item, generate_test_feed_metadata, generate_test_feed_credentials

def feed():
    return Feed(
        credentials=generate_test_feed_credentials(),
        metadata=generate_test_feed_metadata(
            last_build_date=datetime(2025, 4, 10),
        ),
        items=[
            generate_test_item(1),
            generate_test_item(2)
        ]
    )

def template_output():
    return """Credentials:
- https://example.com/feed
- test_filter_criteria

Metadata:
- Test Feed
- https://example.com/feed
- Test Feed Description
- en-us
- 2025-04-10 00:00:00
- 60

Items:
- Test Item 1
- https://example.com/test-item-1
- 2021-01-02 00:00:00
- Test Description 1
- test-guid-1

- Test Item 2
- https://example.com/test-item-2
- 2021-01-03 00:00:00
- Test Description 2
- test-guid-2
"""

def output_types():
    return [
        # Normal
        OutputType(
            template_name="test_template.test.j2",
            relative_output_path="test_output.test"
        ),
        # Different output path
        OutputType(
            template_name="test_template.test.j2",
            relative_output_path="test_output2.test"
        )
    ]

@pytest.mark.parametrize(
    "output_types,expected_output",
    [
        (output_types(), template_output()),
        ([], "")
    ]
)
def test_generate_outputs(
    output_types,
    expected_output
    ):
    # Construct the absolute path to the fixtures directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    fixtures_dir = os.path.join(test_dir, "fixtures")

    rendered_outputs = generate_outputs(
        input=feed(), 
        template_dir=fixtures_dir, 
        outputs=output_types
    )

    for output_type in output_types:
        assert rendered_outputs[output_type.relative_output_path] == expected_output
