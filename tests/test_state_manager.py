import pytest
from unittest.mock import patch, mock_open
from typing import Optional
from rss_buddy.state_manager import StateManager, State
from models import ItemGUID, FeedCredentials, ProcessedFeed, Feed, FeedMetadata
from tests.test_utils import generate_test_feed, generate_test_item

def feed_url(id: int):
    return f"https://example.com/feed{id}"

def filter_criteria(id: int):
    return f"test-filter-criteria-{id}"

def default_feed_data(id: int):
    return State.FeedData(
        filter_criteria=filter_criteria(id),
        passed_item_guids=[
            ItemGUID(f"test-guid-1"),
        ],
        failed_item_guids=[
            ItemGUID(f"test-guid-2"),
        ],
    )

def default_processed_feeds():
    return {
        feed_url(1): default_feed_data(1),
        feed_url(2): default_feed_data(2),
    }

def default_state():
    return State(
        global_filter_criteria="test-global-filter-criteria",
        processed_feeds=default_processed_feeds(),
    )

def default_feed_credentials(
        id: int,
        criteria: Optional[str] = None,
    ):
    return FeedCredentials(
        url=feed_url(id),
        filter_criteria=criteria or filter_criteria(id),
    )

def empty_state_manager():
    return StateManager(
        file_path="",
        feed_credentials=[],
        global_filter_criteria="",
    )

@pytest.mark.parametrize(
    "path_exists, expected_state",
    [
        (True, default_state()),
        (False, None),
    ]
)
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists", name="mock_exists")
def test_state_manager_load_state(
        mock_exists,
        mock_open,
        path_exists,
        expected_state,
    ):

    mock_exists.return_value = path_exists
    mock_open.return_value.read.return_value = expected_state.model_dump_json() if expected_state else None

    state = StateManager._load_state(file_path="test_state.json")

    assert state == expected_state

@pytest.mark.parametrize(
    "new_global_filter_criteria, new_feed_credentials, expected_state",
    [
        # No changes
        (
            default_state().global_filter_criteria,
            [default_feed_credentials(1), default_feed_credentials(2)],
            default_state(),
        ),
        # Global filter criteria changed
        (
            "new-global-filter-criteria",
            [default_feed_credentials(1), default_feed_credentials(2)],
            State(global_filter_criteria="new-global-filter-criteria"),
        ),
        # Feed credentials changed
        (
            default_state().global_filter_criteria,
            [
                FeedCredentials(
                    url=feed_url(1),
                    filter_criteria="new-filter-criteria-1",
                ),
                FeedCredentials(
                    url=feed_url(2),
                    filter_criteria="new-filter-criteria-2",
                ),
            ],
            State(
                global_filter_criteria=default_state().global_filter_criteria,
                processed_feeds={},
            ),
        ),
    ]
)
def test_state_manager_validate_state(
        new_global_filter_criteria,
        new_feed_credentials,
        expected_state,
    ):
    state = StateManager._validate_state(
        state=default_state(),
        new_global_filter_criteria=new_global_filter_criteria,
        new_feed_credentials=new_feed_credentials,
    )

    assert state == expected_state

@pytest.mark.parametrize(
    "item_guid, expected_result",
    [
        (ItemGUID("test-guid-1"), True),
        (ItemGUID("test-guid-2"), False),
        (ItemGUID("test-guid-3"), None),
    ]
)
def test_state_manager_item_previous_processing_result(
        item_guid,
        expected_result,
    ):

    state_manager = empty_state_manager()
    state_manager._state = default_state()

    previous_processing_result = state_manager.item_previous_processing_result(
        feed_url(1), 
        item_guid
    )

    assert previous_processing_result == expected_result

@pytest.mark.parametrize(
    "processed_feed",
    [
        ProcessedFeed(
            feed=generate_test_feed(
                items=[
                    generate_test_item(1),
                    generate_test_item(2),
                ],
            ),
            passed_item_guids=[
                generate_test_item(1).guid,
            ],
            failed_item_guids=[
                generate_test_item(2).guid,
            ],
        ),
        ProcessedFeed(
            feed=generate_test_feed(
                items=[],
            ),
            passed_item_guids=[],
            failed_item_guids=[],
        ),
    ]
)
def test_state_manager_update_state(
        processed_feed,
    ):
    state_manager = empty_state_manager()
    state_manager._state = default_state()

    state_manager.update_state(
        processed_feed=processed_feed,
    )

    assert state_manager._state.processed_feeds[processed_feed.feed.credentials.url] == State.FeedData(
        filter_criteria=processed_feed.feed.credentials.filter_criteria,
        passed_item_guids=processed_feed.passed_item_guids,
        failed_item_guids=processed_feed.failed_item_guids,
    )

@patch("builtins.open", new_callable=mock_open)
def test_state_manager_write(mock_open):
    test_file_path = "test_state.json"

    state_manager = empty_state_manager()
    state_manager._file_path = test_file_path
    state_manager._state = default_state()

    state_manager.write()

    mock_open.assert_called_once_with(test_file_path, "w")
    mock_open.return_value.write.assert_called_once_with(
        default_state().model_dump_json()
    )
