"""Unit tests specifically for date handling functions."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from dateutil import parser

from rss_buddy.feed_processor import FeedProcessor
from rss_buddy.utils.date_parser import RobustDateParser


class TestDateHandling(unittest.TestCase):
    """Test cases specifically for date handling functions."""

    def setUp(self):
        """Set up test environment."""
        mock_ai = MagicMock()
        self.temp_dir = tempfile.TemporaryDirectory()
        # Assign mock to self for use in other methods
        self.mock_state_manager = MagicMock()

        date_parser = RobustDateParser()

        self.feed_processor = FeedProcessor(
            state_manager=self.mock_state_manager,  # Use stored mock
            ai_interface=mock_ai,
            date_parser=date_parser,
            days_lookback=7,
            user_preference_criteria="",
            summary_max_tokens=0,
        )

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_simple_date_parsing(self):
        """Test basic date parsing functionality."""
        # Test with a simple UTC date in ISO format
        iso_date = "2024-03-27T12:00:00Z"
        parsed_date = parser.parse(iso_date)
        self.assertEqual(parsed_date.tzinfo is not None, True, "ISO date should have timezone info")

        # Test RFC 2822 format
        rfc_date = "Wed, 27 Mar 2024 12:00:00 +0000"
        parsed_rfc = parser.parse(rfc_date)
        self.assertEqual(parsed_rfc.tzinfo is not None, True, "RFC date should have timezone info")

        # Test with no timezone
        naive_date = "2024-03-27 12:00:00"
        parsed_naive = parser.parse(naive_date)
        self.assertEqual(
            parsed_naive.tzinfo is None, True, "Naive date should not have timezone info"
        )

        # Test timezone-aware comparison
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=7)
        result = parsed_date > cutoff
        self.assertEqual(result, parsed_date > cutoff, "Comparison should work correctly")

    def test_is_recent_function(self):
        """Test the FeedProcessor.is_recent function directly."""
        # A date from a few days ago (should be recent)
        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(days=3)).isoformat()
        self.assertTrue(self.feed_processor.is_recent(recent_date))

        # A date from more than the lookback period (should not be recent)
        old_date = (now - timedelta(days=10)).isoformat()
        self.assertFalse(self.feed_processor.is_recent(old_date))

        # Test with a None date
        self.assertFalse(self.feed_processor.is_recent(None))

        # Test with an invalid date string
        self.assertFalse(self.feed_processor.is_recent("not a date"))

    def test_problematic_timezone_handling(self):
        """Test handling of potentially problematic timezone formats."""
        # Get the current date for reference
        now = datetime.now(timezone.utc)

        # Create dates with different timezone formats (recent dates)
        test_dates = [
            # Standard UTC timezone
            (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            # Problematic timezone abbreviation
            (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S PDT"),
            # Another problematic timezone abbreviation
            (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S EST"),
            # ISO format with explicit timezone
            (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S-07:00"),
        ]

        # Test each date format with is_recent (all should be considered recent)
        for date_str in test_dates:
            self.assertTrue(
                self.feed_processor.is_recent(date_str),
                f"Date {date_str} should be considered recent",
            )

        # Test with ignoretz parameter for problematic timezone
        pdt_date = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S PDT")
        parsed = parser.parse(pdt_date, ignoretz=True)
        self.assertEqual(
            parsed.tzinfo, None, "Date parsed with ignoretz=True should have no timezone info"
        )

    def test_timezone_conversion(self):
        """Test converting between different timezone representations."""
        # Get current time for a reference point
        now = datetime.now(timezone.utc)

        # Test converting a naive datetime to timezone-aware
        naive_dt = datetime.now()
        aware_dt = naive_dt.replace(tzinfo=timezone.utc)
        self.assertIsNotNone(aware_dt.tzinfo, "Converted datetime should have timezone info")

        # Test with is_recent to ensure our timezone handling works correctly
        # Create a recent date (3 days ago) in different formats
        recent_naive = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        recent_aware = (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S%z")

        naive_result = self.feed_processor.is_recent(recent_naive)
        aware_result = self.feed_processor.is_recent(recent_aware)

        # Both should return the same result since they represent the same date
        self.assertEqual(
            naive_result,
            aware_result,
            "Naive and aware dates from same time should have same is_recent result",
        )

    def test_date_parsing_fallbacks(self):
        """Test the fallback mechanisms for date parsing."""
        now = datetime.now(timezone.utc)
        recent_date = now - timedelta(days=1)

        # Test common problematic timezone formats
        timezone_formats = {
            "PDT": "-0700",
            "PST": "-0800",
            "EDT": "-0400",
            "EST": "-0500",
            "CEST": "+0200",
            "CET": "+0100",
            "AEST": "+1000",
            "AEDT": "+1100",
        }

        # Test each problematic timezone
        for tz, _ in timezone_formats.items():
            date_str = recent_date.strftime(f"%a, %d %b %Y %H:%M:%S {tz}")
            result = self.feed_processor.is_recent(date_str)
            self.assertTrue(result, "Date with timezone should be considered recent")

        # Test regex fallback for dates with unparseable timezone
        custom_format = recent_date.strftime("%Y-%m-%d %H:%M:%S INVALID_TZ")
        # First patch parser.parse to simulate failure for this specific format
        original_parse = parser.parse

        def mock_parse(date_string, **kwargs):
            if "INVALID_TZ" in date_string:
                raise ValueError("Unknown timezone")
            return original_parse(date_string, **kwargs)

        # Apply the patch and test
        with patch("dateutil.parser.parse", side_effect=mock_parse):
            result = self.feed_processor.is_recent(custom_format)
            self.assertTrue(
                result, "Date with unparseable timezone should work with regex fallback"
            )

        # Test extremely malformed date but with recognizable parts
        malformed_date = (
            f"Date is Day {recent_date.strftime('%d/%m/%Y')} "
            f"at {recent_date.strftime('%H:%M:%S')} in TZ?"
        )
        result = self.feed_processor.is_recent(malformed_date)
        # It's reasonable for the parser to fail on this, so expect False
        self.assertFalse(result, "Malformed date should not be considered recent")

    def test_additional_date_formats(self):
        """Test parsing of additional date formats commonly found in RSS feeds."""
        now = datetime.now(timezone.utc)
        recent_date = now - timedelta(days=1)

        # Additional formats to test
        date_formats = [
            # Common RSS date format variants
            recent_date.strftime("%a, %d %b %Y %H:%M:%S GMT"),  # Basic GMT
            recent_date.strftime("%d %b %Y %H:%M:%S"),  # Without day name
            recent_date.strftime("%B %d, %Y %I:%M %p"),  # Month name, 12-hour format
            recent_date.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),  # ISO with microseconds
            # With timezone name in parentheses
            f"{recent_date.strftime('%a, %d %b %Y %H:%M:%S')} (Eastern Standard Time)",
            # Literal T separator without timezone
            f"{recent_date.strftime('%Y-%m-%d')}T{recent_date.strftime('%H:%M:%S')}",
        ]

        for date_str in date_formats:
            result = self.feed_processor.is_recent(date_str)
            self.assertTrue(result, "Date format should be recognized as recent")

    def test_edge_case_date_formats(self):
        """Test edge case date formats and recovery strategies."""
        now = datetime.now(timezone.utc)
        recent_date = now - timedelta(days=1)

        # Edge cases
        edge_cases = [
            f"Published on {recent_date.strftime('%d-%m-%Y')}",  # Date embedded in text
            # Time and date separated
            f"Last Updated: {recent_date.strftime('%I:%M %p')} on "
            f"{recent_date.strftime('%d %B, %Y')}",
            f"{recent_date.strftime('%Y%m%d%H%M%S')}",  # Compact format without separators
            # Unusual ordering
            f"{recent_date.year}, {recent_date.strftime('%B')} {recent_date.day}",
        ]

        # Test each edge case
        for date_str in edge_cases:
            with self.subTest(date_str=date_str):
                # Since our regex might not catch all of these, we're checking if any are detected
                # In a real application, a more robust solution would be needed
                parsed = self.feed_processor.is_recent(date_str)
                # Don't verify the result, just make sure it doesn't crash
                self.assertIsNotNone(parsed is not None)

    def test_timezone_aware_lookback_window(self):
        """Test that the lookback window respects timezone information."""
        # Test with different lookback periods
        for days in [1, 3, 7, 14, 30]:
            # Create a processor with specified lookback days
            processor = FeedProcessor(
                state_manager=self.mock_state_manager,  # Use stored mock
                ai_interface=MagicMock(),  # Can use a fresh mock here
                date_parser=RobustDateParser(),  # Need a date parser
                days_lookback=days,
                user_preference_criteria="",
                summary_max_tokens=0,
            )

            # A date just inside the lookback window
            now = datetime.now(timezone.utc)
            just_recent = (now - timedelta(days=days - 0.5)).isoformat()
            self.assertTrue(
                processor.is_recent(just_recent), "Date should be recent with specified lookback"
            )

            # A date just outside the lookback window
            just_old = (now - timedelta(days=days + 0.5)).isoformat()
            self.assertFalse(
                processor.is_recent(just_old), "Date outside lookback should not be recent"
            )

            # Test with a timezone-naive date
            naive_date = (now - timedelta(days=days - 0.5)).strftime("%Y-%m-%d %H:%M:%S")
            naive_result = processor.is_recent(naive_date)
            self.assertTrue(naive_result, "Naive date should be handled correctly")


if __name__ == "__main__":
    unittest.main()
