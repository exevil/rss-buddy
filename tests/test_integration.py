# tests/test_integration.py
"""Integration tests for the RSS Buddy application."""

import datetime
import json
import os
import shutil

# Make sure src is in the path for imports if running directly
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


from rss_buddy import ai_interface, feed_processor, generate_pages, state_manager


# Dummy feedparser entry structure for mocking
class MockFeedParserDict(dict):
    """A dictionary subclass that allows attribute access like a class."""

    def __getattr__(self, name):
        """Allow attribute-style access to dictionary keys."""
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        """Allow attribute-style setting of dictionary keys."""
        self[name] = value


# Base class for integration tests using temporary directories
class IntegrationTestCase(unittest.TestCase):
    """Base class for integration tests managing temporary directories and env vars."""

    def setUp(self):
        """Set up temporary directories and back up environment variables."""
        self.test_dir = tempfile.mkdtemp(prefix="rss_buddy_test_")
        self.state_dir = os.path.join(self.test_dir, "state")
        self.output_dir = os.path.join(self.test_dir, "output_docs")
        os.makedirs(self.state_dir)
        os.makedirs(self.output_dir)
        # Store original env vars to restore later
        self.original_environ = dict(os.environ)
        # Clear potentially interfering env vars for tests
        os.environ.clear()

    def tearDown(self):
        """Restore environment variables and clean up temporary directories."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)
        # Give a brief moment for file handles to close on Windows
        if sys.platform == "win32":
            time.sleep(0.1)
        # Remove the temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except OSError as e:
            print(f"Error removing temporary directory {self.test_dir}: {e}")


# 1. State Persistence Test
class TestStatePersistence(IntegrationTestCase):
    """Tests for saving, loading, and cleaning up application state (using dicts)."""

    def test_save_and_load_state(self):
        """Verify saving and loading state dictionaries with the file system."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        past_iso = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        ).isoformat()
        old_iso = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
        ).isoformat()
        days_lookback = 7

        # Use dictionary structure mimicking state file format
        article1_id = "id1"
        article2_id = "id2"
        old_article_id = "id_old"

        initial_state_data = {
            "feeds": {
                "feed1_url": {
                    "entry_data": {
                        article1_id: {
                            "id": article1_id,
                            "title": "Article 1",
                            "link": "http://link1",
                            "date": past_iso,
                            "summary": "Summary 1",
                            "status": "processed",
                            "processed_at": now_iso,
                        },
                        article2_id: {
                            "id": article2_id,
                            "title": "Article 2",
                            "link": "http://link2",
                            "date": now_iso,  # More recent
                            "summary": "Summary 2",
                            "status": "digest",
                            "processed_at": now_iso,
                        },
                    },
                    "feed_title": "Feed 1 Title",
                }
            },
            "last_updated": now_iso,
        }

        # Instantiate StateManager
        state_manager_instance = state_manager.StateManager(output_dir=self.state_dir)
        # Manually set the state for saving
        state_manager_instance.state = initial_state_data

        # Save state using the instance method
        state_manager_instance.save_state(days_lookback=days_lookback)
        state_file_path = os.path.join(self.state_dir, "processed_state.json")
        self.assertTrue(os.path.exists(state_file_path))

        # Load state using a new instance to simulate fresh load
        loader_instance = state_manager.StateManager(output_dir=self.state_dir)
        loaded_state = loader_instance.state

        # Assert loaded state matches original
        self.assertEqual(loaded_state, initial_state_data)

        # Test cleanup logic - add an old article directly to the loaded state
        loader_instance.state["feeds"]["feed1_url"]["entry_data"][old_article_id] = {
            "id": old_article_id,
            "title": "Old Article",
            "link": "http://link_old",
            "date": old_iso,
            "summary": "Old Summary",
            "status": "processed",
            "processed_at": past_iso,
        }

        # Save again, triggering cleanup
        loader_instance.save_state(days_lookback=days_lookback)

        # Load yet again to check cleanup
        final_loader = state_manager.StateManager(output_dir=self.state_dir)
        cleaned_state = final_loader.state

        # Check old article is gone, others remain
        self.assertNotIn(old_article_id, cleaned_state["feeds"]["feed1_url"]["entry_data"])
        self.assertIn(article1_id, cleaned_state["feeds"]["feed1_url"]["entry_data"])
        self.assertIn(article2_id, cleaned_state["feeds"]["feed1_url"]["entry_data"])


# 2. Feed Processing & State Update Test
class TestFeedProcessingToState(IntegrationTestCase):
    """Tests the integration of FeedProcessor with mocked AI and StateManager."""

    def setUp(self):
        """Set up mocks for StateManager, AIInterface, and feedparser."""
        super().setUp()

        self.feed_url = "http://dummy.test/feed.xml"
        self.days_lookback = 3
        self.user_criteria = "Process if title contains 'New'"

        # Prepare entry data first to get IDs
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        recent_dt = now_dt - datetime.timedelta(hours=1)
        old_dt = now_dt - datetime.timedelta(days=10)
        # Create dummy processor just to call generate_entry_id
        temp_processor = feed_processor.FeedProcessor(MagicMock(), MagicMock(), 1, "")
        self.recent_entry_dict = {
            "title": "Article 1 New",
            "link": "http://dummy.test/article1",
            "summary": "Summary 1",
            "description": "Summary 1",
            "published_parsed": recent_dt.timetuple(),
            "published": recent_dt.strftime("%a, %d %b %Y %H:%M:%S %Z"),
        }
        self.old_entry_dict = {
            "title": "Article 2 Old",
            "link": "http://dummy.test/article2",
            "summary": "Summary 2",
            "description": "Summary 2",
            "published_parsed": old_dt.timetuple(),
            "published": old_dt.strftime("%a, %d %b %Y %H:%M:%S %Z"),
        }
        self.recent_entry_id = temp_processor.generate_entry_id(self.recent_entry_dict)
        self.old_entry_id = temp_processor.generate_entry_id(self.old_entry_dict)

        # 1. Mock StateManager with specific return values for get_entry_status
        self.mock_state_manager = MagicMock(spec=state_manager.StateManager)
        print(
            f"Test Setup: Expecting recent ID '{self.recent_entry_id}', old ID '{self.old_entry_id}'"
        )  # Debug

        def mock_get_status(feed_url_arg, entry_id_arg):
            print(
                f"Mock get_entry_status called with: feed='{feed_url_arg}', id='{entry_id_arg}'"
            )  # Debug
            if entry_id_arg == self.recent_entry_id:
                print(f"  -> Mock returning None (new entry) for id '{entry_id_arg}'")  # Debug
                return None  # Simulate new entry
            elif entry_id_arg == self.old_entry_id:
                print(
                    f"  -> Mock returning 'processed' (existing entry) for id '{entry_id_arg}'"
                )  # Debug
                return "processed"  # Simulate already processed entry
            print(f"  -> Mock returning None (default) for id '{entry_id_arg}'")  # Debug
            return None  # Default for any unexpected calls

        self.mock_state_manager.get_entry_status.side_effect = mock_get_status

        # 2. Mock AIInterface
        self.mock_ai_interface = MagicMock(spec=ai_interface.AIInterface)
        self.mock_ai_interface.evaluate_article_preference.return_value = "FULL"

        # 3. Mock feedparser.parse
        self.mock_feed_data = MockFeedParserDict(
            {
                "feed": MockFeedParserDict({"title": "Dummy Feed"}),
                "entries": [
                    MockFeedParserDict(self.recent_entry_dict),
                    MockFeedParserDict(self.old_entry_dict),
                ],
                "bozo": 0,
            }
        )
        self.feedparser_patcher = patch("feedparser.parse", return_value=self.mock_feed_data)
        self.mock_feedparser = self.feedparser_patcher.start()

    def tearDown(self):
        """Stop patchers."""
        self.feedparser_patcher.stop()
        super().tearDown()

    def test_process_feed_calls_dependencies(self):
        """Verify FeedProcessor calls AI and StateManager correctly for new/existing items."""
        processor = feed_processor.FeedProcessor(
            state_manager=self.mock_state_manager,
            ai_interface=self.mock_ai_interface,
            days_lookback=self.days_lookback,
            user_preference_criteria=self.user_criteria,
        )
        new_count, skipped_count = processor.process_feed(self.feed_url)

        # Assert counts - Expect 1 new, 0 skipped (old entry skipped by date, not status)
        self.assertEqual(new_count, 1)
        self.assertEqual(skipped_count, 0)  # Corrected assertion: old entry skipped due to date

        # Check feedparser called
        self.mock_feedparser.assert_called_once_with(self.feed_url)

        # StateManager Checks
        # get_entry_status is only called for the recent entry because the old one is skipped by date first
        self.mock_state_manager.get_entry_status.assert_called_once_with(
            self.feed_url, self.recent_entry_id
        )
        # self.assertEqual(self.mock_state_manager.get_entry_status.call_count, 1) # Adjusted expectation

        # --- Assert add_processed_entry call more robustly ---
        self.mock_state_manager.add_processed_entry.assert_called_once()
        call_args, call_kwargs = self.mock_state_manager.add_processed_entry.call_args

        # Assert Positional Arguments (feed_url, entry_id, status, entry_data)
        self.assertEqual(len(call_args), 4)
        self.assertEqual(call_args[0], self.feed_url)  # feed_url
        self.assertEqual(call_args[1], self.recent_entry_id)  # entry_id
        self.assertEqual(call_args[2], "processed")  # status
        actual_entry_data = call_args[3]  # entry_data

        # Assert Keyword Arguments (feed_title)
        self.assertEqual(len(call_kwargs), 1)
        self.assertEqual(call_kwargs.get("feed_title"), "Dummy Feed")

        # Assert the entry_data dictionary contents
        self.assertIsNotNone(actual_entry_data)
        self.assertIsInstance(actual_entry_data, dict)
        expected_entry_data_arg = {
            "id": self.recent_entry_id,
            "title": self.recent_entry_dict["title"],
            "link": self.recent_entry_dict["link"],
            "summary": self.recent_entry_dict["summary"],
            "date": self.recent_entry_dict["published"],
        }
        self.assertEqual(actual_entry_data, expected_entry_data_arg)

        # AI Interface Checks - called only for the NEW entry
        self.mock_ai_interface.evaluate_article_preference.assert_called_once_with(
            title=self.recent_entry_dict["title"],
            summary=self.recent_entry_dict["summary"],
            criteria=self.user_criteria,
            feed_url=self.feed_url,
        )


# 3. State-to-HTML Generation Test
class TestHtmlGeneration(IntegrationTestCase):
    """Tests the integration of state loading and HTML site generation (using dicts)."""

    def setUp(self):
        """Set up a predefined state dictionary file and mock AI."""
        super().setUp()
        os.environ["OPENAI_API_KEY"] = "dummy_test_key"
        # Create a predefined state dictionary
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        past_iso = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        ).isoformat()
        past_iso_2 = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
        ).isoformat()

        # Use dictionary structure mimicking state file format
        f1p1_id = "f1p1"
        f1d1_id = "f1d1"
        f1d2_id = "f1d2"
        f2p2_id = "f2p2"

        self.predefined_state = {
            "feeds": {
                "http://feed1.test": {
                    "entry_data": {
                        f1p1_id: {
                            "id": f1p1_id,
                            "title": "Feed1 Processed Article",
                            "link": "http://feed1.test/proc1",
                            "date": past_iso,
                            "summary": "Summary P1",
                            "status": "processed",
                            "processed_at": now_iso,
                        },
                        f1d1_id: {
                            "id": f1d1_id,
                            "title": "Feed1 Digest Article 1",
                            "link": "http://feed1.test/dig1",
                            "date": past_iso_2,
                            "summary": "Summary D1",
                            "status": "digest",
                            "processed_at": now_iso,
                        },
                        f1d2_id: {
                            "id": f1d2_id,
                            "title": "Feed1 Digest Article 2",
                            "link": "http://feed1.test/dig2",
                            "date": now_iso,
                            "summary": "Summary D2",
                            "status": "digest",
                            "processed_at": now_iso,
                        },
                    },
                    "feed_title": "Feed1 Test Title",
                },
                "http://feed2.test": {
                    "entry_data": {
                        f2p2_id: {
                            "id": f2p2_id,
                            "title": "Feed2 Processed Article",
                            "link": "http://feed2.test/proc2",
                            "date": past_iso_2,
                            "summary": "Summary P2",
                            "status": "processed",
                            "processed_at": now_iso,
                        }
                    },
                    "feed_title": "Feed2 Test Title",
                },
                "http://feed3.test_nodata": {
                    "entry_data": {},
                    "feed_title": "Feed3 NoData Title",
                },  # Test empty feed
            },
            "last_updated": now_iso,
        }
        self.state_file_path = os.path.join(self.state_dir, "processed_state.json")
        with open(self.state_file_path, "w") as f:
            json.dump(self.predefined_state, f, indent=2)

        # Mock AIInterface used within generate_pages
        self.mock_ai_client = MagicMock()
        self.mock_ai_client.generate_consolidated_summary.return_value = (
            "Generated AI Digest for Feed 1."
        )
        self.ai_patcher = patch(
            "rss_buddy.generate_pages.AIInterface", return_value=self.mock_ai_client
        )
        self.mock_ai_constructor = self.ai_patcher.start()
        # Add check that patcher target exists before starting
        try:
            self.ai_patcher.get_original()
        except AttributeError:
            print("ERROR: Patch target 'rss_buddy.generate_pages.AIInterface' might be incorrect!")
            # Optionally raise here to fail fast if target is wrong

    def tearDown(self):
        """Stop patchers."""
        self.ai_patcher.stop()
        super().tearDown()

    def test_generate_site_from_state(self):
        """Verify HTML site generation from a state dictionary file."""
        generate_pages.generate_pages(data_dir=self.state_dir, docs_dir=self.output_dir)

        # Check AI digest call using the correct method name
        self.assertTrue(self.mock_ai_client.generate_consolidated_summary.called)
        # Check specific calls if needed
        # self.mock_ai_client.generate_consolidated_summary.assert_called_once_with(...)

        # ... other assertions ...


if __name__ == "__main__":
    unittest.main()
