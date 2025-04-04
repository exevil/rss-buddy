"""Configuration handling for RSS Buddy using dataclasses and environment variables."""

import os
from dataclasses import dataclass, field
from typing import List


def get_env_str(key: str, default: str | None = None) -> str:
    """Get a string environment variable."""
    value = os.environ.get(key)
    if value is None:
        if default is None:
            raise ValueError(f"Required environment variable {key} is not set.")
        return default
    return value


def get_env_int(key: str, default: int | None = None) -> int:
    """Get an integer environment variable."""
    value_str = os.environ.get(key)
    if value_str is None:
        if default is None:
            raise ValueError(f"Required environment variable {key} is not set.")
        return default
    try:
        return int(value_str)
    except ValueError as e:
        raise ValueError(f"Environment variable {key} must be an integer.") from e


def get_env_list(key: str, default: List[str] | None = None) -> List[str]:
    """Get a list of strings environment variable (comma or newline separated)."""
    value_str = os.environ.get(key)
    if value_str is None:
        if default is None:
            raise ValueError(f"Required environment variable {key} is not set.")
        return default

    # Split by newline first, then by comma, and filter empty strings
    items = []
    for line in value_str.split("\n"):
        items.extend(item.strip() for item in line.split(",") if item.strip())
    return items


@dataclass(frozen=True)
class RssBuddyConfig:
    """Configuration settings for RSS Buddy."""

    openai_api_key: str = field(repr=False)  # Avoid printing API key
    rss_feeds: List[str]
    user_preference_criteria: str
    days_lookback: int
    ai_model: str
    summary_max_tokens: int
    output_dir: str

    @classmethod
    def from_environment(cls) -> "RssBuddyConfig":
        """Load configuration from environment variables."""
        return cls(
            openai_api_key=get_env_str("OPENAI_API_KEY"),
            rss_feeds=get_env_list("RSS_FEEDS"),
            user_preference_criteria=get_env_str("USER_PREFERENCE_CRITERIA"),
            days_lookback=get_env_int("DAYS_LOOKBACK"),
            ai_model=get_env_str("AI_MODEL"),
            summary_max_tokens=get_env_int("SUMMARY_MAX_TOKENS"),
            output_dir=get_env_str("OUTPUT_DIR", default="processed_feeds"),
        )
