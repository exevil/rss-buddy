import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from models import FeedCredentials
from rss_buddy.fetch_feeds import fetch_feeds

def input_credentials():
    return [
        FeedCredentials(
            url="https://www.example.com/rss1",
            filter_criteria="Test Criteria",
        ),
        FeedCredentials(
            url="https://www.example.com/rss2",
            filter_criteria="Test Criteria 2",
        ),
    ]

def response_text():
    return """
    <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            <link>https://www.example.com</link>
            <description>Test Description</description>
            <language>en</language>
            <lastBuildDate>Fri, 01 Jan 2021 00:00:00 GMT</lastBuildDate>
            <item>
                <title>Test Item 1</title>
                <link>https://www.example.com/test1</link>
                <description>Test Description 1</description>
                <pubDate>Fri, 01 Jan 2021 00:00:00 GMT</pubDate>
                <guid>Test Guid 1</guid>
            </item>
            <item>
                <title>Test Item 2</title>
                <link>https://www.example.com/test2</link>
                <description>Test Description 2</description>
                <pubDate>Fri, 01 Jan 2021 00:00:00 GMT</pubDate>
                <guid>Test Guid 2</guid>
            </item>
        </channel>
    </rss>
    """

@patch("requests.get")
def test_fetch_feeds(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = response_text()
    credentials = input_credentials()

    feeds = fetch_feeds(
        credentials=credentials,
        days_lookback=1,
    )
    
    assert len(feeds) == 2

    for index, feed in enumerate(feeds):
        assert feed.credentials.url == credentials[index].url
        assert feed.credentials.filter_criteria == credentials[index].filter_criteria
        
        assert feed.metadata.title == "Test Feed"
        assert feed.metadata.link == "https://www.example.com"
        assert feed.metadata.description == "Test Description"
        assert feed.metadata.language == "en"
        assert feed.metadata.last_build_date == datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc)

        assert len(feed.items) == 2

        for index, item in enumerate(feed.items):
            assert item.title == f"Test Item {index + 1}"
            assert item.link == f"https://www.example.com/test{index + 1}"
            assert item.description == f"Test Description {index + 1}"
            assert item.pub_date == datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc)
            assert item.guid == f"Test Guid {index + 1}"
