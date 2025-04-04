"""Integration tests for the generate_pages module using HTML parsing."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone  # Import datetime and timezone
from unittest.mock import patch

from bs4 import BeautifulSoup  # Import BeautifulSoup

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Modules to test
from rss_buddy.ai_interface import MockAIInterface
from rss_buddy.config import RssBuddyConfig  # Import config
from rss_buddy.generate_pages import generate_pages, sanitize_filename
from rss_buddy.state_manager import StateManager
from rss_buddy.utils.date_parser import RobustDateParser


class TestGeneratePages(unittest.TestCase):
    """Tests for the generate_pages functionality with HTML parsing."""

    def setUp(self):
        """Set up temporary directories and test configuration."""
        self.temp_root = tempfile.TemporaryDirectory()
        # Simulate the structure where state is in one dir, output goes to another
        self.state_dir = os.path.join(self.temp_root.name, "state_data")
        self.docs_dir = os.path.join(self.temp_root.name, "output_docs")
        os.makedirs(self.state_dir)
        # Note: docs_dir should be created by generate_pages

        self.state_file_path = os.path.join(self.state_dir, "processed_state.json")
        self.fixture_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "fixtures", "test_state_for_pages.json")
        )

        # Copy fixture to temp state directory
        shutil.copy2(self.fixture_path, self.state_file_path)

        # Common parser instance
        self.date_parser = RobustDateParser()
        # Fixed days lookback matching static fixture dates
        self.days_lookback = 7

        # Create a standard config for tests
        self.test_config = RssBuddyConfig(
            openai_api_key="mock-key-for-test",
            rss_feeds=["https://unique-feed.com/rss"],  # Can be minimal here
            user_preference_criteria="test criteria",
            days_lookback=self.days_lookback,
            ai_model="mock-model",
            summary_max_tokens=100,
            output_dir=self.state_dir,  # Point config to state dir
        )

        # Prepare mock AI response for the digest item
        self.expected_ai_summary_html = "<p>Mock Digest: Recent Digest Item</p>"
        self.mock_ai_instance = MockAIInterface(
            summary_responses={
                # Key is sorted titles ("+" joined)
                "Recent Digest Item": self.expected_ai_summary_html
            }
        )

        # Instantiate real StateManager using the temp state file
        self.state_manager_instance = StateManager(
            date_parser=self.date_parser, state_file=self.state_file_path
        )

    def tearDown(self):
        """Clean up temporary directories."""
        self.temp_root.cleanup()

    # --- Test sanitize_filename (Remains the same) ---
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        self.assertEqual(sanitize_filename("Valid Name"), "Valid_Name")
        self.assertEqual(sanitize_filename(" spaces "), "_spaces_")
        self.assertEqual(sanitize_filename('a/b\\c:d*e?f"g<h>i|j'), "a_b_c_d_e_f_g_h_i_j")
        self.assertEqual(
            sanitize_filename("!@#$%^&*()=+[]{}"), "_"
        )  # Expect underscore as fallback
        self.assertEqual(
            sanitize_filename("long-" * 30 + "name"),
            ("long-" * 30 + "name")[:100],
        )

    # --- Test generate_pages Orchestration (Using DI and HTML Parsing) ---
    @patch("rss_buddy.state_manager.datetime")
    def test_generate_pages_end_to_end_with_html_parsing(self, mock_datetime):
        """Test generate_pages end-to-end using DI and parsing HTML output."""
        # Configure the mock to return a fixed datetime
        # Choose a date where the lookback includes the fixture dates
        fixed_now = datetime(2024, 4, 3, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        # Also mock utcnow() if it's used anywhere (though .now(timezone.utc) is preferred)
        mock_datetime.utcnow.return_value = fixed_now.replace(tzinfo=None)

        # Arrange
        feed_url = "https://unique-feed.com/rss"
        # Load the raw title from the fixture to calculate expected filename
        with open(self.fixture_path, "r") as f:
            raw_state = json.load(f)
        feed_title_raw = raw_state["feeds"][feed_url]["feed_title"]
        # Correctly calculate the expected sanitized title based on the function's logic
        expected_sanitized_title = "My_Awesome_Feed_Special_Chars_____"
        expected_feed_filename = f"feed_{expected_sanitized_title}.html"

        # Act
        # Call generate_pages with injected config, state manager, and mock AI
        generate_pages(
            config=self.test_config,
            state_manager=self.state_manager_instance,
            ai_interface=self.mock_ai_instance,
            docs_dir=self.docs_dir,
        )

        # Assert
        # Check directories and basic files exist
        self.assertTrue(os.path.isdir(self.docs_dir))
        index_path = os.path.join(self.docs_dir, "index.html")
        feed_path = os.path.join(self.docs_dir, expected_feed_filename)
        metadata_path = os.path.join(self.docs_dir, "metadata.json")
        state_copy_path = os.path.join(self.docs_dir, "processed_state.json")

        self.assertTrue(os.path.exists(index_path), "index.html not found")
        self.assertTrue(os.path.exists(feed_path), f"{expected_feed_filename} not found")
        self.assertTrue(os.path.exists(metadata_path), "metadata.json not found")
        self.assertTrue(os.path.exists(state_copy_path), "processed_state.json copy not found")

        # --- Assert Index HTML Content using BeautifulSoup --- #
        with open(index_path, "r", encoding="utf-8") as f:
            index_soup = BeautifulSoup(f, "html.parser")

        # Select list items specifically within the ul with class "index-list"
        feed_list_items = index_soup.select("ul.index-list > li")
        self.assertEqual(len(feed_list_items), 1, "Expected 1 feed item in index list")

        feed_link = feed_list_items[0].find("a")
        self.assertIsNotNone(feed_link, "Feed link not found in list item")
        self.assertEqual(feed_link["href"], expected_feed_filename)
        # Check text content, stripping whitespace
        self.assertIn(feed_title_raw.strip(), feed_link.get_text(strip=True))

        # Check counts (more robustly)
        # Find the <small> tag within the list item
        count_small_tag = feed_list_items[0].find("small")
        self.assertIsNotNone(count_small_tag, "Count <small> tag not found")
        # Check the text content of the <small> tag
        count_text = count_small_tag.get_text(strip=True)
        self.assertIn("Processed: 1", count_text)
        self.assertIn("Digest: 1", count_text)

        # --- Assert Feed HTML Content using BeautifulSoup --- #
        with open(feed_path, "r", encoding="utf-8") as f:
            feed_soup = BeautifulSoup(f, "html.parser")

        # Check feed title in heading (assuming H1)
        main_heading = feed_soup.find("h1")
        self.assertIsNotNone(main_heading, "H1 heading not found in feed page")
        self.assertIn(feed_title_raw.strip(), main_heading.get_text(strip=True))

        # Check processed items using the correct structure
        processed_articles = feed_soup.select("div.article")
        self.assertEqual(len(processed_articles), 1, "Expected 1 processed article div")

        # Assertions relative to the first (and only) article div
        article_div = processed_articles[0]
        article_link = article_div.select_one("h2 > a")
        self.assertIsNotNone(article_link, "Link not found in processed article")
        self.assertEqual(article_link.get_text(strip=True), "Recent Processed Item")
        self.assertEqual(article_link["href"], "http://l.co/1")

        # Check summary (assuming it's in the next sibling div after the meta div)
        meta_div = article_div.find("div", class_="article-meta")
        self.assertIsNotNone(meta_div, "Meta div not found in article")
        summary_div = meta_div.find_next_sibling("div")
        self.assertIsNotNone(summary_div, "Summary div not found after meta div")
        self.assertEqual(summary_div.get_text(strip=True), "Summary 1")

        # Ensure the digest item title is NOT within any article div
        for article in processed_articles:
            self.assertNotIn("Recent Digest Item", article.get_text())

        # Check AI digest section (assuming a div with class="digest")
        digest_section = feed_soup.find("div", class_="digest")  # Find by class
        self.assertIsNotNone(digest_section, "AI Digest section (div.digest) not found")

        # Ensure the old item is NOT present anywhere on the page
        self.assertNotIn("Old Processed Item", feed_soup.get_text())

        # --- Assert Metadata Content --- #
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_feeds"], 1)
        self.assertEqual(metadata["total_processed"], 1)  # Based on fixture
        self.assertEqual(metadata["total_digest"], 1)  # Based on fixture
        self.assertIn("generation_timestamp_utc", metadata)
        self.assertIn("feeds", metadata)
        self.assertEqual(len(metadata["feeds"]), 1)
        feed_meta = metadata["feeds"][0]
        self.assertEqual(feed_meta["title"], feed_title_raw)
        self.assertEqual(feed_meta["filename"], expected_feed_filename)
        self.assertEqual(feed_meta["processed_count"], 1)
        self.assertEqual(feed_meta["digest_count"], 1)
        self.assertEqual(feed_meta["original_url"], feed_url)

    # --- Test Edge Case: Empty State --- #

    def test_generate_pages_empty_state_file(
        self,
    ):
        """Test generation with an empty state file using DI."""
        # Arrange
        # Create an empty state file
        empty_state_path = os.path.join(self.state_dir, "empty_state.json")
        with open(empty_state_path, "w") as f:
            json.dump({"feeds": {}, "last_updated": None}, f)

        # Create StateManager pointing to empty state
        empty_state_manager = StateManager(
            date_parser=self.date_parser, state_file=empty_state_path
        )

        # Create a config pointing to the dir containing the empty state
        empty_config = RssBuddyConfig(
            openai_api_key="",  # No key needed for empty state
            rss_feeds=[],
            user_preference_criteria="",
            days_lookback=7,
            ai_model="",
            summary_max_tokens=0,
            output_dir=self.state_dir,  # Points to dir with empty_state.json
        )

        # Act
        # Pass the empty state manager directly
        generate_pages(
            config=empty_config,
            state_manager=empty_state_manager,
            ai_interface=self.mock_ai_instance,  # Can pass mock or None
            docs_dir=self.docs_dir,
        )

        # Assert
        # Check basic output files are still created
        index_path = os.path.join(self.docs_dir, "index.html")
        metadata_path = os.path.join(self.docs_dir, "metadata.json")
        self.assertTrue(os.path.exists(index_path))
        self.assertTrue(os.path.exists(metadata_path))

        # Check content using BeautifulSoup
        with open(index_path, "r", encoding="utf-8") as f:
            index_soup = BeautifulSoup(f, "html.parser")
        # Find the body content area instead of main
        body_content = index_soup.find("body")
        self.assertIsNotNone(body_content, "<body> tag not found in empty index page")
        # Check for the introductory text and the specific 'no feeds' message within the body
        body_text = body_content.get_text()
        self.assertIn("These feeds are processed with AI", body_text)
        self.assertIn("No feeds have been processed yet.", body_text)

        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        self.assertEqual(metadata["total_feeds"], 0)

        # Check that state file WAS copied (as expected)
        state_copy_path = os.path.join(self.docs_dir, "processed_state.json")
        self.assertTrue(os.path.exists(state_copy_path))


if __name__ == "__main__":
    unittest.main()
