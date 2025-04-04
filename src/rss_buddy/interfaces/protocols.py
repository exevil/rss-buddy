"""Defines protocols for dependency injection and mocking core components."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol


class StateManagerProtocol(Protocol):
    """Protocol defining the interface for managing application state."""

    def get_entry_status(self, feed_url: str, entry_id: str) -> Optional[str]:
        """Check if an entry has been processed and return its status."""
        ...

    def add_processed_entry(
        self,
        feed_url: str,
        entry_id: str,
        status: str,
        entry_data: Dict[str, Any],
        feed_title: Optional[str] = None,
    ):
        """Add or update a processed entry's state."""
        ...

    def get_items_in_lookback(self, feed_url: str, days_lookback: int) -> List[Dict[str, Any]]:
        """Get all processed items within the lookback period for a specific feed."""
        ...

    def get_all_feed_urls(self) -> List[str]:
        """Return a list of all feed URLs currently tracked in the state."""
        ...

    def get_feed_title(self, feed_url: str) -> Optional[str]:
        """Get the stored title for a specific feed."""
        ...

    def save_state(self, days_lookback: Optional[int] = None):
        """Save the current state, optionally cleaning up old entries."""
        ...

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse a date string using the configured date parser."""  # Note: May remove later if parser is injected
        ...


class AIInterfaceProtocol(Protocol):
    """Protocol defining the interface for AI operations."""

    def evaluate_article_preference(
        self, title: str, summary: str, criteria: str, feed_url: Optional[str] = None
    ) -> str:
        """Evaluate if an article should be shown in full or summarized."""
        ...

    def generate_consolidated_summary(
        self, articles: List[Dict[str, Any]], max_tokens: int = 150
    ) -> Optional[str]:
        """Generate a consolidated summary for multiple articles."""
        ...
