"""Unit tests for the RobustDateParser utility."""

import datetime
import os
import sys
import unittest
from datetime import timezone

# Add path to allow importing package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.rss_buddy.utils.date_parser import RobustDateParser


class TestRobustDateParser(unittest.TestCase):
    """Test the RobustDateParser class."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = RobustDateParser()
        self.utc = timezone.utc

    def test_standard_rfc822(self):
        """Test standard RFC 822 format."""
        date_str = "Fri, 21 Nov 1997 09:55:06 -0600"
        expected = datetime.datetime(1997, 11, 21, 15, 55, 6, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_standard_iso8601(self):
        """Test standard ISO 8601 format with Z timezone."""
        date_str = "2023-12-01T12:00:00Z"
        expected = datetime.datetime(2023, 12, 1, 12, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_iso8601_with_offset(self):
        """Test ISO 8601 format with explicit offset."""
        date_str = "2023-12-01T10:00:00+02:00"
        expected = datetime.datetime(2023, 12, 1, 8, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_naive_datetime(self):
        """Test a naive datetime string (should assume UTC)."""
        date_str = "2023-12-01 14:30:00"
        expected = datetime.datetime(2023, 12, 1, 14, 30, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_common_web_format(self):
        """Test a common web format like 'Day, DD Mon YYYY HH:MM:SS GMT'."""
        date_str = "Tue, 15 Nov 1994 08:12:31 GMT"
        expected = datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_timezone_abbreviation_pdt(self):
        """Test parsing with PDT timezone abbreviation."""
        date_str = "Mon, 10 Apr 2023 17:00:00 PDT"  # PDT is UTC-7
        expected = datetime.datetime(2023, 4, 11, 0, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_timezone_abbreviation_est(self):
        """Test parsing with EST timezone abbreviation."""
        date_str = "Mon, 10 Apr 2023 17:00:00 EST"  # EST is UTC-5
        expected = datetime.datetime(2023, 4, 10, 22, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_timezone_abbreviation_cest(self):
        """Test parsing with CEST timezone abbreviation."""
        date_str = "Mon, 10 Apr 2023 17:00:00 CEST"  # CEST is UTC+2
        expected = datetime.datetime(2023, 4, 10, 15, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_ignoretz_fallback(self):
        """Test fallback to ignoretz=True if standard parsing fails due to TZ."""
        # Example where a standard parser might fail but ignoretz works (assuming UTC)
        date_str = "2023-10-26T10:00:00 WEIRDZONE"  # Assume WEIRDZONE causes failure
        # If ignoretz=True works, it should parse as 10:00 UTC
        expected = datetime.datetime(2023, 10, 26, 10, 0, 0, tzinfo=self.utc)
        # This test relies on the internal logic using ignoretz as a fallback
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_fuzzy_parsing_fallback(self):
        """Test fuzzy parsing fallback for dates embedded in strings."""
        date_str = "Published on: 2024-03-15 09:00:00 UTC by Author"
        expected = datetime.datetime(2024, 3, 15, 9, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_regex_fallback_yyyy_mm_dd(self):
        """Test regex fallback for YYYY-MM-DD HH:MM:SS format."""
        date_str = "DATE:2024-02-20 18:30:55"
        expected = datetime.datetime(2024, 2, 20, 18, 30, 55, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_regex_fallback_dd_mm_yyyy(self):
        """Test regex fallback for DD/MM/YYYY HH:MM:SS format."""
        date_str = "Timestamp: 25/12/2023 10:00:00 - Event Log"
        expected = datetime.datetime(2023, 12, 25, 10, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_invalid_date_string(self):
        """Test an completely unparseable date string."""
        date_str = "not a date at all"
        self.assertIsNone(self.parser.parse_date(date_str))

    def test_empty_string(self):
        """Test parsing an empty string."""
        self.assertIsNone(self.parser.parse_date(""))

    def test_none_input(self):
        """Test parsing None input."""
        self.assertIsNone(self.parser.parse_date(None))

    def test_date_with_milliseconds(self):
        """Test date strings with milliseconds."""
        date_str = "2023-12-01T12:00:00.123Z"
        expected = datetime.datetime(2023, 12, 1, 12, 0, 0, 123000, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)

    def test_timezone_in_middle(self):
        """Test timezone abbreviation appearing mid-string (should normalize)."""
        date_str = "Apr 10, 2023 17:00:00 EST USA"
        expected = datetime.datetime(2023, 4, 10, 22, 0, 0, tzinfo=self.utc)
        self.assertEqual(self.parser.parse_date(date_str), expected)


if __name__ == "__main__":
    unittest.main()
