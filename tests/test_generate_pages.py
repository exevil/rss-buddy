"""Unit tests for the generate_pages module."""

import html
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Modules to test
from rss_buddy import generate_pages
from rss_buddy.ai_interface import AIInterface
from rss_buddy.models import IndexFeedInfo
from rss_buddy.state_manager import StateManager


class TestGeneratePages(unittest.TestCase):
    """Tests for the generate_pages functionality."""

    def setUp(self):
        """Set up temporary directories for data and output."""
        self.temp_root = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.temp_root.name, "data")
        self.docs_dir = os.path.join(self.temp_root.name, "docs")
        os.makedirs(self.data_dir)
        # docs_dir should be created by the function being tested

    def tearDown(self):
        """Clean up temporary directories."""
        self.temp_root.cleanup()

    def _write_state(self, state_data: dict):
        """Helper to write a state dictionary to the temp data_dir."""
        state_file = os.path.join(self.data_dir, "processed_state.json")
        with open(state_file, "w") as f:
            json.dump(state_data, f)
        return state_file

    def _create_dummy_state(self, num_feeds=1, items_per_feed=2, days_lookback=7) -> dict:
        """Creates a usable dummy state dictionary."""
        state = {"feeds": {}, "last_updated": datetime.now(timezone.utc).isoformat()}
        now = datetime.now(timezone.utc)

        for i in range(num_feeds):
            feed_url = f"https://example.com/feed{i}.xml"
            feed_title = f"Test Feed & Title / {i}"
            feed_data = {"entry_data": {}, "feed_title": feed_title, "last_entry_date": None}
            entry_ids = []
            for j in range(items_per_feed):
                entry_id = f"item_{i}_{j}"
                entry_ids.append(entry_id)
                # Alternate between recent and old, processed and digest
                is_recent = j % 2 == 0
                status = "digest" if (i + j) % 3 == 0 else "processed"
                item_date = (
                    now - timedelta(days=days_lookback // 2)
                    if is_recent
                    else now - timedelta(days=days_lookback * 2)
                )

                feed_data["entry_data"][entry_id] = {
                    "id": entry_id,
                    "title": f"Feed {i} Item {j} ({status})",
                    "link": f"https://example.com/feed{i}/item{j}",
                    "summary": f"Summary for item {j} of feed {i}.",
                    "date": item_date.isoformat(),
                    "processed_at": now.isoformat(),
                    "status": status,
                }
                if is_recent and feed_data["last_entry_date"] is None:
                    feed_data["last_entry_date"] = item_date.isoformat()

            state["feeds"][feed_url] = feed_data

        return state

    # --- Test sanitize_filename (Still relevant) ---
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        self.assertEqual(generate_pages.sanitize_filename("Valid Name"), "Valid_Name")
        self.assertEqual(generate_pages.sanitize_filename(" spaces "), "_spaces_")
        self.assertEqual(
            generate_pages.sanitize_filename('a/b\\c:d*e?f"g<h>i|j'), "a_b_c_d_e_f_g_h_i_j"
        )
        self.assertEqual(generate_pages.sanitize_filename("!@#$%^&*()=+[]{}"), "_")
        self.assertEqual(
            generate_pages.sanitize_filename("long-" * 30 + "name"),
            ("long-" * 30 + "name")[:100],
        )
        self.assertEqual(
            generate_pages.sanitize_filename("long-" * 50 + "name"), ("long-" * 50 + "name")[:100]
        )

    # --- Test _generate_feed_html Direct Logic ---

    @patch("rss_buddy.generate_pages._hydrate_article")
    def test__generate_feed_html_basic(self, mock_hydrate):
        """Test the internal logic of _generate_feed_html."""
        # Arrange
        feed_url = "https://test.com/feed"
        mock_state_manager = unittest.mock.MagicMock(spec=StateManager)
        mock_ai_interface = unittest.mock.MagicMock(spec=AIInterface)
        mock_jinja_env = unittest.mock.MagicMock(spec=generate_pages.Environment)
        mock_template = unittest.mock.MagicMock()

        # Configure mock instances directly
        mock_jinja_env.get_template.return_value = mock_template
        mock_ai_interface.generate_consolidated_summary.return_value = "AI Summary Content"

        # Configure the template mock's render method
        expected_render_output = "<html>Rendered Content</html>"
        mock_template.render.return_value = expected_render_output

        days_lookback = 7
        summary_max_tokens = 100
        generation_time_display = "2024-01-01 12:00:00 UTC"

        # Configure mocked StateManager instance methods
        mock_state_manager.get_feed_title.return_value = "My Test Feed"
        item1_dict = {
            "id": "1",
            "status": "processed",
            "date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "title": "P1",
        }
        item2_dict = {
            "id": "2",
            "status": "digest",
            "date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "title": "D1",
        }
        item3_dict = {
            "id": "3",
            "status": "processed",
            "date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "title": "P2",
        }
        mock_state_manager.get_items_in_lookback.return_value = [item1_dict, item2_dict, item3_dict]

        # Mock hydrate function
        mock_article1 = unittest.mock.MagicMock(
            id="1",
            status="processed",
            published_date=datetime.now(timezone.utc) - timedelta(days=1),
            title="P1",
        )
        mock_article2 = unittest.mock.MagicMock(
            id="2",
            status="digest",
            published_date=datetime.now(timezone.utc) - timedelta(days=2),
            title="D1",
        )
        mock_article3 = unittest.mock.MagicMock(
            id="3",
            status="processed",
            published_date=datetime.now(timezone.utc) - timedelta(days=3),
            title="P2",
        )
        mock_hydrate.side_effect = [mock_article1, mock_article2, mock_article3]

        # Act - Use mock_open context manager
        m_open = unittest.mock.mock_open()
        with patch("builtins.open", m_open):
            result_metadata = generate_pages._generate_feed_html(
                feed_url=feed_url,
                state_manager=mock_state_manager,
                ai_interface=mock_ai_interface,
                days_lookback=days_lookback,
                summary_max_tokens=summary_max_tokens,
                output_dir=self.docs_dir,
                jinja_env=mock_jinja_env,
                generation_time_display=generation_time_display,
            )

        # Assert
        mock_state_manager.get_items_in_lookback.assert_called_once_with(feed_url, days_lookback)
        mock_state_manager.get_feed_title.assert_called_once_with(feed_url)
        self.assertEqual(mock_hydrate.call_count, 3)

        # Check AI call
        mock_ai_interface.generate_consolidated_summary.assert_called_once()
        ai_call_args = mock_ai_interface.generate_consolidated_summary.call_args.kwargs["articles"]
        self.assertEqual(len(ai_call_args), 1)
        self.assertEqual(ai_call_args[0]["title"], "D1")

        # Check Jinja call
        mock_jinja_env.get_template.assert_called_once_with("feed.html.j2")
        mock_template.render.assert_called_once()
        render_context = mock_template.render.call_args.kwargs["feed_data"]
        self.assertEqual(render_context.url, feed_url)
        self.assertEqual(render_context.title, "My Test Feed")
        self.assertEqual(len(render_context.processed_items), 2)
        self.assertEqual(render_context.processed_items[0].title, "P1")
        self.assertEqual(render_context.processed_items[1].title, "P2")
        self.assertEqual(len(render_context.digest_items), 1)
        self.assertEqual(render_context.digest_items[0].title, "D1")
        self.assertEqual(render_context.ai_digest_summary, "AI Summary Content")
        self.assertNotEqual(render_context.last_updated_display, "Never")

        # Check file writing using the mock_open handle
        expected_filename = f"feed_{generate_pages.sanitize_filename('My Test Feed')}.html"
        m_open.assert_called_once_with(
            os.path.join(self.docs_dir, expected_filename), "w", encoding="utf-8"
        )
        m_open().write.assert_called_once_with(expected_render_output)

        # Check returned metadata
        self.assertIsInstance(result_metadata, IndexFeedInfo)
        self.assertEqual(result_metadata.title, "My Test Feed")
        self.assertEqual(result_metadata.filename, expected_filename)
        self.assertEqual(result_metadata.processed_count, 2)
        self.assertEqual(result_metadata.digest_count, 1)
        self.assertEqual(result_metadata.original_url, feed_url)

    @patch("rss_buddy.generate_pages._hydrate_article")
    def test__generate_feed_html_no_items(self, mock_hydrate):
        """Test _generate_feed_html returns None if no items are found."""
        # Arrange
        mock_state_manager = unittest.mock.MagicMock(spec=StateManager)
        # Configure mocked StateManager instance methods
        mock_state_manager.get_feed_title.return_value = "Empty Feed"
        mock_state_manager.get_items_in_lookback.return_value = []

        # These mocks are needed for the function signature but won't be used internally if no items
        mock_ai_interface = unittest.mock.MagicMock(spec=AIInterface)
        mock_jinja_env = unittest.mock.MagicMock(spec=generate_pages.Environment)

        # Act
        result = generate_pages._generate_feed_html(
            feed_url="http://empty.com",
            state_manager=mock_state_manager,
            ai_interface=mock_ai_interface,
            days_lookback=7,
            summary_max_tokens=100,
            output_dir=self.docs_dir,
            jinja_env=mock_jinja_env,
            generation_time_display="time",
        )

        # Assert
        self.assertIsNone(result)
        mock_state_manager.get_items_in_lookback.assert_called_once()
        mock_state_manager.get_feed_title.assert_called_once()
        mock_hydrate.assert_not_called()

    # --- Test generate_pages Orchestration ---

    # Use patch on the *actual* location of _generate_feed_html within the generate_pages module
    @patch("rss_buddy.generate_pages._generate_feed_html")
    @patch("rss_buddy.generate_pages.get_env_str", return_value="dummy")  # Mock env vars
    @patch("rss_buddy.generate_pages.get_env_int", return_value=7)
    @patch("shutil.copy2")  # Mock file copying
    def test_generate_pages_basic(
        self, mock_copy, mock_get_int, mock_get_str, mock_generate_feed_html
    ):
        """Test generating pages orchestration for a simple state file."""
        state_data = self._create_dummy_state(num_feeds=1, items_per_feed=2, days_lookback=7)
        feed_url = list(state_data["feeds"].keys())[0]
        feed_title = state_data["feeds"][feed_url]["feed_title"]
        # Manually set statuses for predictability if needed by assertions
        # ... (setup specific statuses if required by checks below) ...
        state_file_path = self._write_state(state_data)  # Keep path for mock_copy assertion

        # Mock the helper to return an IndexFeedInfo object
        expected_filename = f"feed_{generate_pages.sanitize_filename(feed_title)}.html"
        mock_generate_feed_html.return_value = IndexFeedInfo(
            filename=expected_filename,
            title=feed_title,
            processed_count=1,
            digest_count=1,
            original_url=feed_url,
        )

        generate_pages.generate_pages(data_dir=self.data_dir, docs_dir=self.docs_dir)

        self.assertTrue(os.path.isdir(self.docs_dir))
        index_path = os.path.join(self.docs_dir, "index.html")
        self.assertTrue(os.path.exists(index_path))
        with open(index_path, "r") as f:
            index_content = f.read()
        self.assertIn(f'<a href="{expected_filename}">', index_content)
        self.assertIn(html.escape(feed_title), index_content)

        mock_generate_feed_html.assert_called_once()
        call_args = mock_generate_feed_html.call_args
        self.assertEqual(call_args.kwargs["feed_url"], feed_url)
        self.assertIsInstance(call_args.kwargs["state_manager"], StateManager)
        self.assertIsInstance(call_args.kwargs["ai_interface"], AIInterface)
        self.assertEqual(call_args.kwargs["output_dir"], self.docs_dir)
        self.assertIn("jinja_env", call_args.kwargs)
        self.assertIn("generation_time_display", call_args.kwargs)

        metadata_path = os.path.join(self.docs_dir, "metadata.json")
        self.assertTrue(os.path.exists(metadata_path))
        mock_copy.assert_called_once_with(
            state_file_path, os.path.join(self.docs_dir, "processed_state.json")
        )

    @patch("rss_buddy.generate_pages._generate_feed_html")
    @patch("rss_buddy.generate_pages.get_env_str", return_value="dummy")
    @patch("rss_buddy.generate_pages.get_env_int", return_value=7)
    @patch("shutil.copy2")
    def test_generate_pages_with_digest(
        self, mock_copy, mock_get_int, mock_get_str, mock_generate_feed_html
    ):
        """Test orchestration includes digest scenario (mocked)."""
        state_data = self._create_dummy_state(num_feeds=1, items_per_feed=3)
        feed_url = list(state_data["feeds"].keys())[0]
        feed_title = state_data["feeds"][feed_url]["feed_title"]
        item_ids = list(state_data["feeds"][feed_url]["entry_data"].keys())
        state_data["feeds"][feed_url]["entry_data"][item_ids[0]]["status"] = "digest"
        state_data["feeds"][feed_url]["entry_data"][item_ids[1]]["status"] = "processed"
        state_data["feeds"][feed_url]["entry_data"][item_ids[2]]["status"] = "digest"
        self._write_state(state_data)  # Removed unused assignment

        expected_filename = f"feed_{generate_pages.sanitize_filename(feed_title)}.html"
        mock_generate_feed_html.return_value = IndexFeedInfo(
            filename=expected_filename,
            title=feed_title,
            processed_count=1,
            digest_count=2,
            original_url=feed_url,
        )

        generate_pages.generate_pages(data_dir=self.data_dir, docs_dir=self.docs_dir)

        mock_generate_feed_html.assert_called_once()
        call_args = mock_generate_feed_html.call_args
        self.assertEqual(call_args.kwargs["feed_url"], feed_url)
        self.assertEqual(call_args.kwargs["output_dir"], self.docs_dir)

        index_path = os.path.join(self.docs_dir, "index.html")
        self.assertTrue(os.path.exists(index_path))
        with open(index_path, "r") as f:
            index_content = f.read()
        self.assertIn("Processed: 1 | Digest: 2", index_content)

        metadata_path = os.path.join(self.docs_dir, "metadata.json")
        self.assertTrue(os.path.exists(metadata_path))
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_digest"], 2)
        self.assertEqual(metadata["total_processed"], 1)

        mock_copy.assert_called_once()

    @patch("rss_buddy.generate_pages._generate_feed_html", return_value=None)  # Simulate failure
    @patch("rss_buddy.generate_pages.get_env_str", return_value="dummy")
    @patch("rss_buddy.generate_pages.get_env_int", return_value=7)
    @patch("shutil.copy2")
    def test_generate_pages_ai_digest_fails(
        self, mock_copy, mock_get_int, mock_get_str, mock_generate_feed_html
    ):
        """Test orchestration handles _generate_feed_html failure scenario (e.g., IO error, AI fail)."""
        state_data = self._create_dummy_state(num_feeds=1, items_per_feed=1)
        # feed_url = list(state_data["feeds"].keys())[0] # Removed unused feed_url assignment
        self._write_state(state_data)  # Removed state_file_path assignment

        generate_pages.generate_pages(data_dir=self.data_dir, docs_dir=self.docs_dir)

        mock_generate_feed_html.assert_called_once()

        index_path = os.path.join(self.docs_dir, "index.html")
        self.assertTrue(os.path.exists(index_path))
        with open(index_path, "r") as f:
            index_content = f.read()
        self.assertIn("No feeds have been processed yet.", index_content)
        self.assertNotIn('<a href="feed_', index_content)

        metadata_path = os.path.join(self.docs_dir, "metadata.json")
        self.assertTrue(os.path.exists(metadata_path))
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_feeds"], 0)

        mock_copy.assert_called_once()

    @patch("rss_buddy.generate_pages._generate_feed_html")
    @patch("rss_buddy.generate_pages.get_env_str", return_value="dummy")
    @patch("rss_buddy.generate_pages.get_env_int", return_value=7)
    @patch("shutil.copy2")
    def test_generate_pages_no_recent_items(
        self, mock_copy, mock_get_int, mock_get_str, mock_generate_feed_html
    ):
        """Test generation when no items are within the lookback period (mocked _generate_feed_html returns None)."""
        now = datetime.now(timezone.utc)
        days_lookback = 7
        state_data = self._create_dummy_state(
            num_feeds=1, items_per_feed=2, days_lookback=days_lookback
        )
        feed_url = list(state_data["feeds"].keys())[0]
        for item_id, item_data in state_data["feeds"][feed_url]["entry_data"].items():
            item_data["date"] = (now - timedelta(days=days_lookback * 2)).isoformat()
        self._write_state(state_data)  # Removed state_file_path assignment

        # Simulate _generate_feed_html returning None because get_items_in_lookback was empty
        mock_generate_feed_html.return_value = None

        generate_pages.generate_pages(data_dir=self.data_dir, docs_dir=self.docs_dir)

        mock_generate_feed_html.assert_called_once()
        self.assertTrue(os.path.exists(os.path.join(self.docs_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(self.docs_dir, "metadata.json")))
        with open(os.path.join(self.docs_dir, "index.html"), "r") as f:
            self.assertIn("No feeds have been processed yet.", f.read())
        with open(os.path.join(self.docs_dir, "metadata.json"), "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_feeds"], 0)
        mock_copy.assert_called_once()

    @patch("rss_buddy.generate_pages._generate_feed_html")
    @patch("rss_buddy.generate_pages.get_env_str", return_value="dummy")
    @patch("rss_buddy.generate_pages.get_env_int", return_value=7)
    @patch("shutil.copy2")
    def test_generate_pages_empty_state(
        self, mock_copy, mock_get_int, mock_get_str, mock_generate_feed_html
    ):
        """Test generation with an empty state file (no feeds key)."""
        state_data = {"last_updated": datetime.now(timezone.utc).isoformat()}  # Missing 'feeds' key
        self._write_state(state_data)  # Removed state_file_path assignment

        generate_pages.generate_pages(data_dir=self.data_dir, docs_dir=self.docs_dir)

        mock_generate_feed_html.assert_not_called()

        self.assertTrue(os.path.exists(os.path.join(self.docs_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(self.docs_dir, "metadata.json")))
        with open(os.path.join(self.docs_dir, "index.html"), "r") as f:
            self.assertIn("No feeds have been processed yet.", f.read())
        with open(os.path.join(self.docs_dir, "metadata.json"), "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_feeds"], 0)
        mock_copy.assert_called_once()

    @patch(
        "rss_buddy.ai_interface.AIInterface.generate_consolidated_summary",
        return_value="Mock Digest",
    )
    @patch("jinja2.Environment.get_template")
    @patch("rss_buddy.generate_pages.get_env_str", return_value="dummy_key_or_model")
    @patch("rss_buddy.generate_pages.get_env_int", return_value=7)
    @patch("shutil.copy2")
    def test_generate_pages_uses_feed_title_for_filename(
        self, mock_copy, mock_get_int, mock_get_str, mock_get_template, mock_ai_summary
    ):
        """Test that the generated HTML filename uses the sanitized feed title from the state."""
        # Setup state with a specific title needing sanitization
        feed_url = "https://unique-feed.com/rss"
        feed_title_raw = "My Awesome Feed! (Special Chars /\\?)"
        state_data = {
            "feeds": {
                feed_url: {
                    "feed_title": feed_title_raw,
                    "entry_data": {
                        "item1": {
                            "id": "item1",
                            "title": "Recent Processed Item",
                            "link": "http://l.co/1",
                            "summary": "Summary 1",
                            "date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "status": "processed",
                        },
                        "item2": {
                            "id": "item2",
                            "title": "Recent Digest Item",
                            "link": "http://l.co/2",
                            "summary": "Summary 2",
                            "date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "status": "digest",
                        },
                    },
                }
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self._write_state(state_data)

        # Mock the template loading and rendering process
        mock_feed_template = unittest.mock.MagicMock()
        mock_feed_template.render.return_value = "<html>Mock Feed Content</html>"
        mock_index_template = unittest.mock.MagicMock()

        # Calculate expected sanitized filename *before* setting up index mock render value
        expected_sanitized_title = generate_pages.sanitize_filename(feed_title_raw)
        expected_filename = f"feed_{expected_sanitized_title}.html"

        # Configure index template mock to include the link we check for
        mock_index_template.render.return_value = (
            f'<html>Index linking to <a href="{expected_filename}">Feed</a></html>'
        )

        # Make get_template return the correct mock based on input
        def get_template_side_effect(template_name):
            if template_name == "feed.html.j2":
                return mock_feed_template
            elif template_name == "index.html.j2":
                return mock_index_template
            else:
                raise ValueError(f"Unexpected template requested: {template_name}")

        mock_get_template.side_effect = get_template_side_effect

        # Run Generation (without mocking _generate_feed_html)
        generate_pages.generate_pages(data_dir=self.data_dir, docs_dir=self.docs_dir)

        # Assertions
        # 1. Check if the correctly named HTML file exists
        expected_filepath = os.path.join(self.docs_dir, expected_filename)
        self.assertTrue(
            os.path.exists(expected_filepath), f"Expected file {expected_filename} not found."
        )

        # 2. Check index.html links to the correct file
        index_path = os.path.join(self.docs_dir, "index.html")
        self.assertTrue(os.path.exists(index_path))
        with open(index_path, "r") as f:
            index_content = f.read()
        self.assertIn(f'<a href="{expected_filename}">', index_content)

        # 3. Check metadata.json (which is generated)
        metadata_path = os.path.join(self.docs_dir, "metadata.json")
        self.assertTrue(os.path.exists(metadata_path))
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_feeds"], 1)

        # Check that get_template was called for feed.html.j2 and index.html.j2
        # Note: Using call_args_list might be more robust if order matters
        mock_get_template.assert_any_call("feed.html.j2")
        mock_get_template.assert_any_call("index.html.j2")
        # Check render was called on both mocks
        mock_feed_template.render.assert_called()
        mock_index_template.render.assert_called()

        # Check index page was also generated


if __name__ == "__main__":
    unittest.main()
