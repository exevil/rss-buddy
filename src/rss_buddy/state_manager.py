import os
import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from models import ItemGUID, ProcessedFeed, FeedCredentials

# Original feed link.
OriginalFeedLink = str

class State(BaseModel):
    """
    The state of the RSS Buddy.
    """
    class FeedData(BaseModel):
        """
        The data for a feed.
        """
        filter_criteria: Optional[str] # The filter criteria of the feed
        processing_result: ProcessedFeed.ProcessingResult # The processing result of the feed

    global_filter_criteria: Optional[str] = None # The global filter criteria
    processed_feeds: Dict[OriginalFeedLink, FeedData] = {} # Processed items for each feed

class StateManager:
    def __init__(
            self,
            file_path: str, # The path to load/save the state file
            feed_credentials: List[FeedCredentials] , # The credentials of the feeds
            global_filter_criteria: Optional[str] = None, # The global filter criteria
        ):
        """
        Initialize the state manager and load the state from the given path if present.
        """

        self._file_path = file_path

        # Load the state
        if state := self._load_state(file_path):
            self._state = self._validate_state(state, global_filter_criteria, feed_credentials)
        else:
            self._state = State(global_filter_criteria=global_filter_criteria)

    @classmethod
    def _load_state(
            cls,
            file_path: str
        ) -> Optional[State]:
        """
        Load the state from the given path.
        """
        # Load or create the state
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return State.model_validate_json(f.read())
        
        return None

    @classmethod
    def _validate_state(
            cls,
            state: State,
            new_global_filter_criteria: Optional[str],
            new_feed_credentials: List[FeedCredentials],
        ) -> State:
        """
        Validate the state against the new data.

        Returns:
            Returns the original state if it is valid; otherwise, returns a new state containing only the data that remains valid for retrieving previous processing results.
        """
        # Check if the global filter criteria is valid
        if new_global_filter_criteria != state.global_filter_criteria:
            logging.warning(f"Global filter criteria has changed from \"{state.global_filter_criteria}\" to \"{new_global_filter_criteria}\". Starting with empty state.")
            return State(global_filter_criteria=new_global_filter_criteria)
        
        # Check if the feeds metadata is valid
        for feed_credentials in new_feed_credentials:
            # Check if the feed is in the state
            if feed_credentials.url not in state.processed_feeds:
                logging.warning(f"Feed \"{feed_credentials.url}\" not found in state. Removing from state.")
                del state.processed_feeds[feed_credentials.url]
            # Check if the feed filter criteria is changed
            if feed_credentials.filter_criteria != state.processed_feeds[feed_credentials.url].filter_criteria:
                logging.warning(f"Feed filter criteria has changed for \"{feed_credentials.url}\". Removing from state.")
                del state.processed_feeds[feed_credentials.url]
        
        # Return the original state
        return state

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
        feed_processing_result = self._state.processed_feeds.get(feed_link)
        if not feed_processing_result:
            logging.info(f"Feed \"{feed_link}\" has not been previously processed.")
            return None
        
        if item_guid in feed_processing_result.processing_result.passed_item_guids:
            logging.info(f"Item \"{item_guid}\" has been previously processed and passed filter.")
            return True
        elif item_guid in feed_processing_result.processing_result.failed_item_guids:
            logging.info(f"Item \"{item_guid}\" has been previously processed and failed filter.")
            return False
        else:
            logging.info(f"Item \"{item_guid}\" has not been previously processed.")
            return None

    def update_state(
            self,
            feed_credentials: FeedCredentials,
            processing_result: ProcessedFeed.ProcessingResult,
        ):
        """
        Update the state with the new processing result.
        """
        self._state.processed_feeds[feed_credentials.url] = State.FeedData(
            filter_criteria=feed_credentials.filter_criteria,
            processing_result=processing_result,
        )

    def write(self):
        """
        Write the state to the file.
        """
        with open(self._file_path, "w") as f:
            f.write(self._state.model_dump_json())
            logging.info(f"State written to \"{self._file_path}\".")
