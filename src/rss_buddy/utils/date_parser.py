"""Utility for robust date string parsing."""

import datetime
import re
from datetime import timezone
from typing import Optional, Protocol

from dateutil import parser


class DateParserProtocol(Protocol):
    """Protocol defining the interface for date parsing."""

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime.datetime]:
        """Parse a date string into a timezone-aware datetime object (UTC).

        Args:
            date_str: The date string to parse.

        Returns:
            A timezone-aware datetime object (UTC) or None if parsing fails.
        """
        ...


class RobustDateParser(DateParserProtocol):
    """Provides robust date parsing logic, handling various formats and timezones."""

    # Common problematic timezone abbreviations and their approximate UTC offsets
    _timezone_replacements = {
        "PDT": "-0700",
        "PST": "-0800",
        "EDT": "-0400",
        "EST": "-0500",
        "CEST": "+0200",
        "CET": "+0100",
        "AEST": "+1000",
        "AEDT": "+1100",
        # Add GMT/UTC explicitly, though parser usually handles them
        "GMT": "+0000",
        "UTC": "+0000",
    }

    def _tzinfos(self, tzname: str, _offset: Optional[int]):
        """Callback for dateutil.parser to handle custom timezone names."""
        return self._timezone_replacements.get(tzname)

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime.datetime]:
        """Parse a date string into a timezone-aware datetime object (UTC)."""
        if not date_str:
            return None

        parsed_date = None

        # Attempt 1: Standard parsing (might handle GMT, +0000 etc.)
        try:
            parsed_date = parser.parse(date_str)
        except Exception:
            pass  # Ignore failure, try next method

        # Attempt 2: Try parsing ignoring timezone info (common fallback)
        if parsed_date is None:
            try:
                # This might succeed where standard parsing fails due to odd TZ
                parsed_date = parser.parse(date_str, ignoretz=True)
            except Exception:
                pass  # Ignore failure, try next method

        # Attempt 3: Normalize known timezone strings (PDT, EST etc.) and parse
        if parsed_date is None:
            try:
                normalized_date_str = date_str
                for tz, offset in self._timezone_replacements.items():
                    # Use regex to replace tz only if it's a standalone word
                    pattern = r"\b" + re.escape(tz) + r"\b"
                    if re.search(pattern, normalized_date_str):
                        normalized_date_str = re.sub(pattern, offset, normalized_date_str)

                # If normalization occurred, try parsing with tzinfos
                if normalized_date_str != date_str:
                    parsed_date = parser.parse(normalized_date_str, tzinfos=self._tzinfos)
                else:  # If no normalization, try standard parse with tzinfos as fallback
                    parsed_date = parser.parse(date_str, tzinfos=self._tzinfos)

            except Exception:
                pass  # Ignore failure, try next method

        # Attempt 4: Try fuzzy parsing as a last resort
        if parsed_date is None:
            try:
                # Fuzzy parsing tries to find date/time within a larger string
                parsed_date = parser.parse(date_str, fuzzy=True)
            except Exception:
                pass  # All parsing attempts failed

        # Attempt 5: Simplified Regex fallback for YYYY-MM-DD HH:MM:SS or DD/MM/YYYY HH:MM:SS
        if parsed_date is None:
            try:
                # Try YYYY-MM-DD HH:MM:SS format
                match = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", date_str)
                if match:
                    date_part, time_part = match.groups()
                    parsed_date = parser.parse(f"{date_part} {time_part}")
                else:
                    # Try DD/MM/YYYY HH:MM:SS format
                    match = re.search(r"(\d{2}/\d{2}/\d{4})[ T](\d{2}:\d{2}:\d{2})", date_str)
                    if match:
                        date_part, time_part = match.groups()
                        # Need dayfirst=True for DD/MM/YYYY
                        parsed_date = parser.parse(f"{date_part} {time_part}", dayfirst=True)
            except Exception:
                pass  # Regex fallback failed

        # Final check and timezone handling
        if parsed_date is not None:
            try:
                # If parsed date is naive, assume UTC
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                # Convert any aware datetime to UTC
                return parsed_date.astimezone(timezone.utc)
            except Exception as e:
                print(f"    Warning: Error converting parsed date '{parsed_date}' to UTC: {e}")
                return None  # Failed during timezone conversion

        # All attempts failed
        # print(f"    Warning: Could not parse date: '{date_str}'. All attempts failed.")
        return None
