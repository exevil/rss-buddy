import os
import logging
from typing import Dict, Optional

from pydantic import BaseModel

from models import ItemGUID, ProcessedFeed

# Original feed link.
OriginalFeedLink = str

class State(BaseModel):
    last_processed_feeds: Dict[OriginalFeedLink, ProcessedFeed.ProcessingResult] # Last processed items for each feed

class StateManager:
    def __init__(
            self,
            file_path: str, # The path to load/save the state file
        ):
        """
        Initialize the state manager and load the state from the given path if present.
        """

        self._file_path = file_path

        if os.path.exists(self._file_path):
            with open(self._file_path, "r") as f:
                self._state = State.model_validate_json(f.read())
        else:
            logging.warning(f"State not found at {self._file_path}. Starting with empty state.")
            self._state = State(last_processed_feeds={})

    def item_previous_processing_result(
            self,
            feed_link: OriginalFeedLink, # The link of the feed
            item_guid: ItemGUID, # The GUID of the item
        ) -> Optional[bool]:
        """
        Check if an item has been processed.

        Returns:
            bool: True if the item has been processed, False otherwise.
            None: If the item has not been processed.
        """
        feed_processing_result = self._state.last_processed_feeds.get(feed_link)
        if not feed_processing_result:
            logging.info(f"Feed {feed_link} has not been previously processed.")
            return None
        
        if item_guid in feed_processing_result.passed_item_guids:
            logging.info(f"Item {item_guid} has been previously processed and passed filter.")
            return True
        elif item_guid in feed_processing_result.failed_item_guids:
            logging.info(f"Item {item_guid} has been previously processed and failed filter.")
            return False
        else:
            logging.info(f"Item {item_guid} has not been previously processed.")
            return None

    def update_state(
            self,
            feed_link: OriginalFeedLink,
            processing_result: ProcessedFeed.ProcessingResult,
        ):
        """
        Update the state with the new processing result.
        """
        self._state.last_processed_feeds[feed_link] = processing_result

    def write(self):
        """
        Write the state to the file.
        """
        with open(self._file_path, "w") as f:
            f.write(self._state.model_dump_json())
            logging.info(f"State written to {self._file_path}.")
