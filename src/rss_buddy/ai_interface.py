"""Interface for AI operations, making them easier to test and mock."""

import os
from typing import Any, Dict, List, Optional, Tuple

# Import OpenAI at module level to make it easier to mock in tests
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .interfaces.protocols import AIInterfaceProtocol


class AIInterface(AIInterfaceProtocol):
    """Interface for AI operations, provides methods for article evaluation and summary generation.

    This class provides a standardized way to interact with OpenAI APIs.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """Initialize the AI interface.

        Args:
            api_key: OpenAI API key. If None, tries to get from environment.
            model: OpenAI model to use for requests.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize the OpenAI client. Override in mock implementations."""
        if OpenAI is None:
            raise ImportError("OpenAI package is required. Install it with 'pip install openai'")
        return OpenAI(api_key=self.api_key)

    def evaluate_article_preference(
        self, title: str, summary: str, criteria: str, feed_url: Optional[str] = None
    ) -> str:
        """Evaluate if an article should be shown in full or summarized.

        Args:
            title: The article title
            summary: The article summary or description
            criteria: User-defined criteria for determining preference
            feed_url: The URL of the feed (for context)

        Returns:
            str: "FULL" or "SUMMARY" preference
        """
        try:
            # Extract domain from feed URL for better context
            feed_source = ""
            if feed_url:
                from urllib.parse import urlparse

                parsed_url = urlparse(feed_url)
                domain = parsed_url.netloc
                feed_source = f"\nSource: {domain}"

            system_prompt = (
                f"You are an assistant that helps determine article preferences. "
                f"Based on the title, summary, and source of an article, determine if it "
                f"should be shown in full or summarized based on these user preferences:"
                f"\n\n{criteria}\n\nRespond with either 'FULL' or 'SUMMARY' only."
            )

            user_content = (
                f"Title: {title}\n\n"
                f"Summary: {summary}{feed_source}\n\n"
                f"Should this article be shown in full or summarized?"
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=10,
            )
            preference = response.choices[0].message.content.strip().upper()
            return "FULL" if preference == "FULL" else "SUMMARY"
        except Exception as e:
            print(f"Error determining preference: {e}")
            return "SUMMARY"  # Default to summary on error

    def generate_consolidated_summary(
        self, articles: List[Dict[str, Any]], max_tokens: int = 150
    ) -> Optional[str]:
        """Generate a consolidated summary for multiple articles.

        Args:
            articles: List of article dictionaries with title, link, and summary
            max_tokens: Maximum tokens for the summary

        Returns:
            str: Generated summary with HTML formatting or None on error
        """
        if not articles:
            return None

        try:
            # Create article list for the prompt
            article_list_str = ""
            for i, article in enumerate(articles, 1):
                article_list_str += f"Article {i}: {article['title']}\n"
                article_list_str += f"Link: {article['link']}\n"
                article_list_str += f"Summary: {article['summary']}\n\n"

            system_content = (
                "You are an assistant that creates a consolidated summary of multiple articles. "
                "Your task is to identify key themes and important stories, and organize them into "
                "a readable digest. Each article title you mention should be a clickable link to "
                "the original article."
            )

            user_content = (
                f"Here are {len(articles)} articles that I want a brief overview of:"
                f"\n\n{article_list_str}\n\n"
                f"Please create a consolidated summary that organizes these into themes and "
                f"highlights the most noteworthy stories. Format the response as a readable "
                f"digest with HTML. Each article title you mention should be wrapped in an "
                f"HTML link tag pointing to its original URL "
                f"(e.g., <a href='article_url'>Article Title</a>)."
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens * len(articles),
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating consolidated summary: {e}")
            return None


class MockAIInterface(AIInterfaceProtocol):
    """Mock implementation of the AI interface for testing."""

    def __init__(
        self,
        evaluation_responses: Dict[Tuple[str, str], str] = None,
        summary_responses: Dict[str, str] = None,
        model: str = "mock-model",
    ):
        """Initialize the mock AI interface with predefined responses.

        Args:
            evaluation_responses: Dictionary mapping (title, summary) tuples to evaluation responses
            summary_responses: Dictionary mapping concatenated article titles to summary responses
            model: Name of the mock model
        """
        self.model = model
        self.evaluation_responses = evaluation_responses or {}
        self.summary_responses = summary_responses or {}
        # No need to initialize a real client
        self.client = None
        self.api_key = "mock-api-key"

    def _initialize_client(self):
        """Return a dummy client since we're not making real API calls."""
        return None

    def evaluate_article_preference(
        self, title: str, summary: str, criteria: str, feed_url: Optional[str] = None
    ) -> str:
        """Return a predefined response based on the title and summary."""
        # Try to find an exact match
        key = (title, summary)
        if key in self.evaluation_responses:
            return self.evaluation_responses[key]

        # Try to find a match just based on title
        for (t, _s), response in self.evaluation_responses.items():
            if t == title:
                return response

        # Default response for testing
        if "AI" in title or "Breakthrough" in title or "Breaking" in title:
            return "FULL"
        return "SUMMARY"

    def generate_consolidated_summary(
        self, articles: List[Dict[str, Any]], max_tokens: int = 150
    ) -> Optional[str]:
        """Return a predefined summary or a generated one for testing."""
        if not articles:
            return None

        # Create a key from article titles
        key = "+".join(sorted([a["title"] for a in articles]))

        # Return predefined response if available
        if key in self.summary_responses:
            return self.summary_responses[key]

        # Generate a basic mock summary for testing
        summary = "<h3>Mock Digest Summary</h3><ul>"
        for article in articles:
            summary += f"<li><a href='{article['link']}'>{article['title']}</a>: "
            if "ai_summary" in article:
                summary += f"{article['ai_summary']}</li>"
        summary += "</ul>"

        return summary
