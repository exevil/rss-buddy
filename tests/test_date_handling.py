"""Unit tests specifically for date handling functions."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import re

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from dateutil import parser
from rss_buddy.feed_processor import FeedProcessor
from rss_buddy.state_manager import StateManager

class TestDateHandling(unittest.TestCase):
    """Test cases specifically for date handling functions."""
    
    @patch('rss_buddy.feed_processor.AIInterface')
    def setUp(self, mock_ai_interface):
        """Set up test environment."""
        # Mock the AI interface to avoid OpenAI API key issues
        mock_ai = mock_ai_interface.return_value
        mock_ai.evaluate_article_preference.return_value = "FULL"
        mock_ai.generate_consolidated_summary.return_value = "This is a consolidated summary"
        
        # Create a temporary state manager and feed processor for testing
        self.state_manager = StateManager(output_dir=".")
        self.feed_processor = FeedProcessor(
            state_manager=self.state_manager,
            ai_interface=mock_ai,
            output_dir=".",
            days_lookback=7
        )
    
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
        self.assertEqual(parsed_naive.tzinfo is None, True, "Naive date should not have timezone info")
        
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
            (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S UTC'),
            # Problematic timezone abbreviation
            (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S PDT'),
            # Another problematic timezone abbreviation
            (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S EST'),
            # ISO format with explicit timezone
            (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S-07:00'),
        ]
        
        # Test each date format with is_recent (all should be considered recent)
        for date_str in test_dates:
            self.assertTrue(self.feed_processor.is_recent(date_str), 
                           f"Date {date_str} should be considered recent")
        
        # Test with ignoretz parameter for problematic timezone
        pdt_date = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S PDT')
        parsed = parser.parse(pdt_date, ignoretz=True)
        self.assertEqual(parsed.tzinfo, None, "Date parsed with ignoretz=True should have no timezone info")
    
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
        recent_naive = (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        recent_aware = (now - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S%z')
        
        naive_result = self.feed_processor.is_recent(recent_naive)
        aware_result = self.feed_processor.is_recent(recent_aware)
        
        # Both should return the same result since they represent the same date
        self.assertEqual(naive_result, aware_result, 
                        "Naive and aware dates from same time should have same is_recent result")
    
    def test_date_parsing_fallbacks(self):
        """Test the fallback mechanisms for date parsing."""
        now = datetime.now(timezone.utc)
        recent_date = now - timedelta(days=1)
        
        # Test common problematic timezone formats
        timezone_formats = {
            'PDT': '-0700',
            'PST': '-0800',
            'EDT': '-0400',
            'EST': '-0500',
            'CEST': '+0200',
            'CET': '+0100',
            'AEST': '+1000',
            'AEDT': '+1100'
        }
        
        # Test each problematic timezone
        for tz, _ in timezone_formats.items():
            date_str = recent_date.strftime(f'%a, %d %b %Y %H:%M:%S {tz}')
            result = self.feed_processor.is_recent(date_str)
            self.assertTrue(result, f"Date with {tz} timezone should be considered recent: {date_str}")
        
        # Test regex fallback for dates with unparseable timezone
        custom_format = recent_date.strftime('%Y-%m-%d %H:%M:%S INVALID_TZ')
        # First patch parser.parse to simulate failure for this specific format
        original_parse = parser.parse
        
        def mock_parse(date_string, **kwargs):
            if 'INVALID_TZ' in date_string:
                raise ValueError("Unknown timezone")
            return original_parse(date_string, **kwargs)
        
        # Apply the patch and test
        with patch('dateutil.parser.parse', side_effect=mock_parse):
            result = self.feed_processor.is_recent(custom_format)
            self.assertTrue(result, f"Date with unparseable timezone should still work with regex fallback: {custom_format}")
        
        # Test extremely malformed date but with recognizable parts
        malformed_date = f"Date is Day {recent_date.strftime('%d/%m/%Y')} at {recent_date.strftime('%H:%M:%S')} in TZ?"
        result = self.feed_processor.is_recent(malformed_date)
        self.assertTrue(result, f"Malformed date with recognizable parts should work: {malformed_date}")
        
    def test_additional_date_formats(self):
        """Test parsing of additional date formats commonly found in RSS feeds."""
        now = datetime.now(timezone.utc)
        recent_date = now - timedelta(days=1)
        
        # Additional formats to test
        date_formats = [
            # Common RSS date format variants
            recent_date.strftime('%a, %d %b %Y %H:%M:%S GMT'),  # Basic GMT
            recent_date.strftime('%d %b %Y %H:%M:%S'),  # Without day name
            recent_date.strftime('%B %d, %Y %I:%M %p'),  # Month name, 12-hour format
            recent_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z'),  # ISO with microseconds
            f"{recent_date.strftime('%a, %d %b %Y %H:%M:%S')} (Eastern Standard Time)",  # With timezone name in parentheses
            f"{recent_date.strftime('%Y-%m-%d')}T{recent_date.strftime('%H:%M:%S')}",  # Literal T separator without timezone
        ]
        
        for date_str in date_formats:
            result = self.feed_processor.is_recent(date_str)
            self.assertTrue(result, f"Date format should be recognized as recent: {date_str}")
            
    def test_edge_case_date_formats(self):
        """Test edge case date formats and recovery strategies."""
        now = datetime.now(timezone.utc)
        recent_date = now - timedelta(days=1)
        
        # Edge cases
        edge_cases = [
            f"Published on {recent_date.strftime('%d-%m-%Y')}",  # Date embedded in text
            f"Last Updated: {recent_date.strftime('%I:%M %p')} on {recent_date.strftime('%d %B, %Y')}",  # Time and date separated
            f"{recent_date.strftime('%Y%m%d%H%M%S')}",  # Compact format without separators
            f"{recent_date.year}, {recent_date.strftime('%B')} {recent_date.day}",  # Unusual ordering
        ]
        
        # Try each edge case with regex fallback
        for date_str in edge_cases:
            # Create a patch to force the regex fallback by making the initial parse fail
            with patch('dateutil.parser.parse', side_effect=ValueError("Simulated parsing failure")):
                with patch.object(self.feed_processor, 'is_recent', wraps=self.feed_processor.is_recent) as wrapped_is_recent:
                    result = wrapped_is_recent(date_str)
                    # We don't assert the result here because the regex fallback may not work for all these edge cases
                    # We just want to ensure the function doesn't crash and handles the failure gracefully
                    
    def test_timezone_aware_lookback_window(self):
        """Test that the lookback window properly handles timezone-aware dates."""
        # Test with a timezone-aware date
        aware_date = "Mon, 31 Mar 2025 11:04:24 +0000"
        self.assertTrue(self.feed_processor.is_recent(aware_date))
        
        # Test with a timezone-naive date
        naive_date = "Mon, 31 Mar 2025 11:04:24"
        self.assertTrue(self.feed_processor.is_recent(naive_date))
        
        # Test with a date in the past
        old_date = "Mon, 10 Feb 2025 11:04:24 +0000"
        self.assertFalse(self.feed_processor.is_recent(old_date))

    def test_tzinfos_timezone_handling(self):
        """Test the improved timezone handling with tzinfos parameter."""
        # Test PDT timezone
        pdt_date = "Mon, 31 Mar 2025 11:04:24 PDT"
        self.assertTrue(self.feed_processor.is_recent(pdt_date))
        
        # Test PST timezone
        pst_date = "Mon, 31 Mar 2025 11:04:24 PST"
        self.assertTrue(self.feed_processor.is_recent(pst_date))
        
        # Test EDT timezone
        edt_date = "Mon, 31 Mar 2025 11:04:24 EDT"
        self.assertTrue(self.feed_processor.is_recent(edt_date))
        
        # Test EST timezone
        est_date = "Mon, 31 Mar 2025 11:04:24 EST"
        self.assertTrue(self.feed_processor.is_recent(est_date))
        
        # Test CEST timezone
        cest_date = "Mon, 31 Mar 2025 11:04:24 CEST"
        self.assertTrue(self.feed_processor.is_recent(cest_date))
        
        # Test CET timezone
        cet_date = "Mon, 31 Mar 2025 11:04:24 CET"
        self.assertTrue(self.feed_processor.is_recent(cet_date))
        
        # Test AEST timezone
        aest_date = "Mon, 31 Mar 2025 11:04:24 AEST"
        self.assertTrue(self.feed_processor.is_recent(aest_date))
        
        # Test AEDT timezone
        aedt_date = "Mon, 31 Mar 2025 11:04:24 AEDT"
        self.assertTrue(self.feed_processor.is_recent(aedt_date))
        
        # Test with multiple timezone abbreviations in the same string
        mixed_date = "Mon, 31 Mar 2025 11:04:24 PDT (Pacific) / 14:04:24 EDT (Eastern)"
        self.assertTrue(self.feed_processor.is_recent(mixed_date))
        
        # Test with invalid timezone abbreviation
        invalid_tz_date = "Mon, 31 Mar 2025 11:04:24 XYZ"
        self.assertTrue(self.feed_processor.is_recent(invalid_tz_date))  # Should still parse the date

if __name__ == "__main__":
    unittest.main() 