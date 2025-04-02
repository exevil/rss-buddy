"""Tests the integration between feed processing and state saving."""

import json
import os

import pytest

from rss_buddy.main import main as rss_buddy_main  # Rename to avoid collision


# Fixture for temporary output directory used by StateManager
@pytest.fixture
def temp_output_dir(tmp_path):
    """Pytest fixture for creating a temporary directory for state output."""
    output_dir = tmp_path / "test_state_output"
    output_dir.mkdir()
    # StateManager expects this directory to exist
    print(f"Created temporary directory: {output_dir}")
    return str(output_dir)


# Fixture for mock feed data (parsed structure)
@pytest.fixture
def mock_feed_parsed_data():
    """Pytest fixture providing mock feed data mimicking feedparser.parse output."""
    # This mimics the structure returned by feedparser.parse
    return {
        "feed": {"title": "Mock Feed Title"},
        "entries": [
            {
                "title": "Entry 1 Title",
                "link": "http://example.com/entry1",
                "guid": "http://example.com/entry1-guid",  # Use non-link guid
                "guidislink": False,
                "published": "Tue, 02 Apr 2024 10:00:00 GMT",  # Within default 7-day lookback
                "summary": "Summary for entry 1.",
            },
            {
                "title": "Entry 2 Title",
                "link": "http://example.com/entry2",
                # No guid, should use link as ID
                "published": "Mon, 01 Apr 2024 11:00:00 GMT",  # Within default 7-day lookback
                "summary": "Summary for entry 2.",
            },
            {
                "title": "Entry 3 Old",
                "link": "http://example.com/entry3-old",
                "guid": "http://example.com/entry3-old",
                "published": "Sun, 10 Mar 2024 12:00:00 GMT",  # Outside default 7-day lookback
                "summary": "Summary for old entry 3.",
            },
        ],
        "bozo": 0,  # Indicates a well-formed feed parse result
    }


def test_feed_processing_saves_state(temp_output_dir, mock_feed_parsed_data, monkeypatch, mocker):
    """Integration Test: Verifies that running main() processes a mock feed via FeedProcessor.

    using a mocked AIInterface and saves the expected state via StateManager.
    """
    mock_feed_url = "http://mock.feed.com/rss"  # URL used as key in state

    # --- Mocking ---
    # 1. Mock environment variables required by main() and components
    monkeypatch.setenv("RSS_FEEDS", mock_feed_url)
    monkeypatch.setenv("OUTPUT_DIR", temp_output_dir)  # Direct StateManager output
    monkeypatch.setenv("USER_PREFERENCE_CRITERIA", "test criteria")
    monkeypatch.setenv("DAYS_LOOKBACK", "7")  # Default, but set explicitly for clarity
    monkeypatch.setenv("AI_MODEL", "mock-ai-model")
    monkeypatch.setenv("SUMMARY_MAX_TOKENS", "150")
    monkeypatch.setenv("OPENAI_API_KEY", "mock-api-key")  # Needed for AIInterface init

    # 2. Mock feedparser.parse to return our fixture data
    # No actual file/URL fetching occurs
    mock_parse = mocker.patch("feedparser.parse", return_value=mock_feed_parsed_data)

    # 3. Mock AIInterface methods
    # Mock __init__ to prevent actual initialization (e.g., API client setup)
    mocker.patch("rss_buddy.ai_interface.AIInterface.__init__", return_value=None)

    # Mock evaluate_article_preference: Entry 1 -> Processed, Entry 2 -> Digest
    def mock_evaluate_preference(*args, **kwargs):
        title = kwargs.get("title", "")
        print(f"Mock AI Evaluate called for title: {title}")  # Debugging print
        if title == "Entry 1 Title":
            return "FULL"  # Results in 'processed' status
        elif title == "Entry 2 Title":
            return "SUMMARY"  # Results in 'digest' status
        # Note: Old Entry 3 won't reach here due to date filtering
        return "SUMMARY"  # Default fallback if needed

    mock_ai_evaluate = mocker.patch(
        "rss_buddy.ai_interface.AIInterface.evaluate_article_preference",
        side_effect=mock_evaluate_preference,
    )

    # --- Execution ---
    # Run the main script function
    print("Running rss_buddy_main()...")
    result_code = rss_buddy_main()
    print(f"rss_buddy_main() finished with code: {result_code}")

    # --- Assertions ---
    assert result_code == 0, "main() should return success code 0"

    # Verify state file was created
    state_file_path = os.path.join(temp_output_dir, "processed_state.json")
    print(f"Checking for state file at: {state_file_path}")
    assert os.path.exists(state_file_path), "processed_state.json should be created"

    # Load and validate state file content
    with open(state_file_path, "r") as f:
        state_data = json.load(f)
    print(f"Loaded state data: {json.dumps(state_data, indent=2)}")

    # Check basic structure
    assert "feeds" in state_data, "State JSON should contain 'feeds' key"
    assert mock_feed_url in state_data["feeds"], (
        f"State should contain data for feed URL: {mock_feed_url}"
    )
    assert "entry_data" in state_data["feeds"][mock_feed_url], (
        "Feed state should contain 'entry_data'"
    )

    feed_entry_data = state_data["feeds"][mock_feed_url]["entry_data"]

    # Verify only recent entries are processed and present
    assert len(feed_entry_data) == 2, "Only the 2 recent entries should be processed and saved"

    # Define expected entry IDs (based on FeedProcessor.generate_entry_id logic)
    # Entry 1 has non-link guid
    entry1_id = mock_feed_parsed_data["entries"][0]["guid"]
    # Entry 2 has no guid, uses link
    entry2_id = mock_feed_parsed_data["entries"][1]["link"]
    # Entry 3 ID (not expected in state, but for reference)
    entry3_id = mock_feed_parsed_data["entries"][2]["guid"]

    assert entry3_id not in feed_entry_data, "Old Entry 3 should not be in the state"

    # Check Entry 1 details (processed)
    assert entry1_id in feed_entry_data, "Entry 1 ID should be in entry_data"
    entry1_state = feed_entry_data[entry1_id]
    assert entry1_state.get("title") == "Entry 1 Title"
    assert entry1_state.get("link") == "http://example.com/entry1"
    assert entry1_state.get("status") == "processed", (
        "Entry 1 status should be 'processed' based on AI mock ('FULL')"
    )
    assert "processed_at" in entry1_state, "Entry 1 should have a 'processed_at' timestamp"
    assert entry1_state.get("date") == mock_feed_parsed_data["entries"][0]["published"], (
        "Entry 1 state should store original published date string"
    )

    # Check Entry 2 details (digest)
    assert entry2_id in feed_entry_data, "Entry 2 ID should be in entry_data"
    entry2_state = feed_entry_data[entry2_id]
    assert entry2_state.get("title") == "Entry 2 Title"
    assert entry2_state.get("link") == "http://example.com/entry2"
    assert entry2_state.get("status") == "digest", (
        "Entry 2 status should be 'digest' based on AI mock ('SUMMARY')"
    )
    assert "processed_at" in entry2_state, "Entry 2 should have a 'processed_at' timestamp"
    assert entry2_state.get("date") == mock_feed_parsed_data["entries"][1]["published"], (
        "Entry 2 state should store original published date string"
    )

    # Verify mocks were called as expected
    mock_parse.assert_called_once_with(mock_feed_url)
    # AI evaluate should only be called for the 2 recent entries
    assert mock_ai_evaluate.call_count == 2, (
        "AI evaluate should be called twice (for recent entries)"
    )
    mock_ai_evaluate.assert_any_call(
        title="Entry 1 Title",
        summary="Summary for entry 1.",
        criteria="test criteria",
        feed_url=mock_feed_url,
    )
    mock_ai_evaluate.assert_any_call(
        title="Entry 2 Title",
        summary="Summary for entry 2.",
        criteria="test criteria",
        feed_url=mock_feed_url,
    )
