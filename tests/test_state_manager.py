import pytest
from unittest.mock import patch, mock_open

from rss_buddy.state_manager import StateManager, State
from models import ProcessedFeed, ItemGUID

def feed_url():
    return "https://example.com/feed"

def default_state():
    return State(
        last_processed_feeds={
            feed_url(): ProcessedFeed.ProcessingResult(
                passed_item_guids=[
                    ItemGUID("test-guid-1"),
                ],
                failed_item_guids=[
                    ItemGUID("test-guid-2"),
                ],
            )
        }
    )

@pytest.mark.parametrize(
    "path_exists, expected_state",
    [
        (True, default_state()),
        (False, State(last_processed_feeds={})),
    ]
)
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists", name="mock_exists")
def test_state_manager_init(
        mock_exists,
        mock_open,
        path_exists,
        expected_state,
    ):

    mock_exists.return_value = path_exists
    mock_open.return_value.read.return_value = expected_state.model_dump_json()

    state_manager = StateManager(
        file_path="test_state.json"
    )

    assert state_manager._state == expected_state

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

    state_manager = StateManager(file_path="")
    state_manager._state = default_state()

    previous_processing_result = state_manager.item_previous_processing_result(
        feed_url(), item_guid
    )

    assert previous_processing_result == expected_result

@pytest.mark.parametrize(
    "processing_result",
    [
        ProcessedFeed.ProcessingResult(
            passed_item_guids=[
                ItemGUID("test-guid-1"),
            ],
            failed_item_guids=[
                ItemGUID("test-guid-2"),
            ],
        ),
        ProcessedFeed.ProcessingResult(
            passed_item_guids=[],
            failed_item_guids=[],
        ),
    ]
)
def test_state_manager_update_state(processing_result):
    state_manager = StateManager(file_path="")
    state_manager._state = default_state()

    state_manager.update_state(feed_url(), processing_result)

    assert state_manager._state.last_processed_feeds[feed_url()] == processing_result

@patch("builtins.open", new_callable=mock_open)
def test_state_manager_write(mock_open):
    test_file_path = "test_state.json"

    state_manager = StateManager(file_path=test_file_path)
    state_manager._state = default_state()

    state_manager.write()

    mock_open.assert_called_once_with(test_file_path, "w")
    mock_open.return_value.write.assert_called_once_with(
        default_state().model_dump_json()
    )
