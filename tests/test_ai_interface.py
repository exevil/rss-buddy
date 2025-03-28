"""Unit tests for the AI interface component."""
import os
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rss_buddy.ai_interface import AIInterface, MockAIInterface

class TestAIInterface(unittest.TestCase):
    """Test the AIInterface class with mocks to avoid real API calls."""
    
    def setUp(self):
        """Set up test environment."""
        # Ensure we don't use a real API key for tests
        if "OPENAI_API_KEY" in os.environ:
            self.original_api_key = os.environ["OPENAI_API_KEY"]
            os.environ["OPENAI_API_KEY"] = "test_api_key"
        else:
            self.original_api_key = None
            os.environ["OPENAI_API_KEY"] = "test_api_key"
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original API key if there was one
        if self.original_api_key:
            os.environ["OPENAI_API_KEY"] = self.original_api_key
        else:
            del os.environ["OPENAI_API_KEY"]
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_initialize_client(self, mock_openai):
        """Test that the client is initialized with the correct API key."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        ai = AIInterface(api_key="test_key")
        
        # Check that OpenAI was initialized with the correct API key
        mock_openai.assert_called_once_with(api_key="test_key")
        self.assertEqual(ai.client, mock_client)
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_evaluate_article_preference_full(self, mock_openai):
        """Test article preference evaluation returning FULL."""
        # Set up mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "FULL"
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Create AI interface and call the method
        ai = AIInterface()
        result = ai.evaluate_article_preference(
            title="Test Article",
            summary="This is a test article about AI.",
            criteria="Show technical articles in FULL.",
            feed_url="https://example.com/feed.xml"
        )
        
        # Check the result
        self.assertEqual(result, "FULL")
        
        # Verify that the API was called with the expected parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-4")
        self.assertIn("system", [m["role"] for m in call_args["messages"]])
        self.assertIn("user", [m["role"] for m in call_args["messages"]])
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_evaluate_article_preference_summary(self, mock_openai):
        """Test article preference evaluation returning SUMMARY."""
        # Set up mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "SUMMARY"
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Create AI interface and call the method
        ai = AIInterface()
        result = ai.evaluate_article_preference(
            title="Test Article",
            summary="This is a test article about entertainment.",
            criteria="Show technical articles in FULL, entertainment in SUMMARY.",
            feed_url="https://example.com/feed.xml"
        )
        
        # Check the result
        self.assertEqual(result, "SUMMARY")
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_evaluate_article_preference_error(self, mock_openai):
        """Test article preference evaluation handling errors."""
        # Set up mock to raise an exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        # Create AI interface and call the method
        ai = AIInterface()
        result = ai.evaluate_article_preference(
            title="Test Article",
            summary="This is a test article.",
            criteria="Show technical articles in FULL.",
            feed_url="https://example.com/feed.xml"
        )
        
        # On error, should default to SUMMARY
        self.assertEqual(result, "SUMMARY")
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_generate_consolidated_summary(self, mock_openai):
        """Test generating a consolidated summary."""
        # Set up mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "<h3>Mock Summary</h3><p>Summary of multiple articles.</p>"
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Create AI interface and call the method
        ai = AIInterface()
        articles = [
            {
                "title": "Article 1",
                "link": "https://example.com/article1",
                "summary": "Summary of article 1"
            },
            {
                "title": "Article 2",
                "link": "https://example.com/article2",
                "summary": "Summary of article 2"
            }
        ]
        
        result = ai.generate_consolidated_summary(articles, max_tokens=100)
        
        # Check the result
        self.assertEqual(result, "<h3>Mock Summary</h3><p>Summary of multiple articles.</p>")
        
        # Verify that the API was called with the expected parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-4")
        self.assertEqual(call_args["max_tokens"], 200)  # 100 tokens per article
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_generate_consolidated_summary_empty_articles(self, mock_openai):
        """Test generating a consolidated summary with empty articles list."""
        # Create AI interface and call the method with empty articles
        ai = AIInterface()
        result = ai.generate_consolidated_summary([], max_tokens=100)
        
        # Should return None for empty articles
        self.assertIsNone(result)
        
        # API should not be called
        mock_openai.return_value.chat.completions.create.assert_not_called()
    
    @patch("rss_buddy.ai_interface.OpenAI")
    def test_generate_consolidated_summary_error(self, mock_openai):
        """Test generating a consolidated summary handling errors."""
        # Set up mock to raise an exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        # Create AI interface and call the method
        ai = AIInterface()
        articles = [
            {
                "title": "Article 1",
                "link": "https://example.com/article1",
                "summary": "Summary of article 1"
            }
        ]
        
        result = ai.generate_consolidated_summary(articles, max_tokens=100)
        
        # On error, should return None
        self.assertIsNone(result)

class TestMockAIInterface(unittest.TestCase):
    """Test the MockAIInterface class."""
    
    def test_evaluate_article_preference_predefined(self):
        """Test article preference evaluation with predefined responses."""
        # Create a mock interface with predefined responses
        evaluation_responses = {
            ("Test 1", "Summary 1"): "FULL",
            ("Test 2", "Summary 2"): "SUMMARY"
        }
        
        mock_ai = MockAIInterface(evaluation_responses=evaluation_responses)
        
        # Test exact match
        result1 = mock_ai.evaluate_article_preference(
            title="Test 1",
            summary="Summary 1",
            criteria="Doesn't matter for mock"
        )
        self.assertEqual(result1, "FULL")
        
        # Test exact match of second item
        result2 = mock_ai.evaluate_article_preference(
            title="Test 2",
            summary="Summary 2",
            criteria="Doesn't matter for mock"
        )
        self.assertEqual(result2, "SUMMARY")
    
    def test_evaluate_article_preference_title_match(self):
        """Test article preference evaluation with title-only match."""
        # Create a mock interface with predefined responses
        evaluation_responses = {
            ("Test 1", "Summary 1"): "FULL"
        }
        
        mock_ai = MockAIInterface(evaluation_responses=evaluation_responses)
        
        # Test title-only match (different summary)
        result = mock_ai.evaluate_article_preference(
            title="Test 1",
            summary="Different summary",
            criteria="Doesn't matter for mock"
        )
        self.assertEqual(result, "FULL")
    
    def test_evaluate_article_preference_default(self):
        """Test article preference evaluation with default behavior."""
        mock_ai = MockAIInterface()
        
        # Test AI in title should default to FULL
        result1 = mock_ai.evaluate_article_preference(
            title="Article about AI",
            summary="Some summary",
            criteria="Doesn't matter for mock"
        )
        self.assertEqual(result1, "FULL")
        
        # Test Breakthrough in title should default to FULL
        result2 = mock_ai.evaluate_article_preference(
            title="Major Breakthrough in science",
            summary="Some summary",
            criteria="Doesn't matter for mock"
        )
        self.assertEqual(result2, "FULL")
        
        # Test normal article should default to SUMMARY
        result3 = mock_ai.evaluate_article_preference(
            title="Regular news article",
            summary="Some summary",
            criteria="Doesn't matter for mock"
        )
        self.assertEqual(result3, "SUMMARY")
    
    def test_generate_consolidated_summary_predefined(self):
        """Test generating a consolidated summary with predefined responses."""
        # Create a mock interface with predefined responses
        summary_responses = {
            "Article 1+Article 2": "<h3>Predefined Summary</h3>"
        }
        
        mock_ai = MockAIInterface(summary_responses=summary_responses)
        
        # Test with matching articles
        articles = [
            {
                "title": "Article 1",
                "link": "https://example.com/article1",
                "summary": "Summary of article 1"
            },
            {
                "title": "Article 2",
                "link": "https://example.com/article2",
                "summary": "Summary of article 2"
            }
        ]
        
        result = mock_ai.generate_consolidated_summary(articles)
        self.assertEqual(result, "<h3>Predefined Summary</h3>")
    
    def test_generate_consolidated_summary_generated(self):
        """Test generating a consolidated summary with auto-generated content."""
        mock_ai = MockAIInterface()
        
        # Test with articles
        articles = [
            {
                "title": "Article 1",
                "link": "https://example.com/article1",
                "summary": "Summary of article 1"
            },
            {
                "title": "Article 2",
                "link": "https://example.com/article2",
                "summary": "Summary of article 2"
            }
        ]
        
        result = mock_ai.generate_consolidated_summary(articles)
        
        # Should generate a basic HTML summary
        self.assertIn("<h3>Mock Digest Summary</h3>", result)
        self.assertIn("<a href='https://example.com/article1'>Article 1</a>", result)
        self.assertIn("<a href='https://example.com/article2'>Article 2</a>", result)
    
    def test_generate_consolidated_summary_empty(self):
        """Test generating a consolidated summary with empty articles list."""
        mock_ai = MockAIInterface()
        
        # Test with empty articles
        result = mock_ai.generate_consolidated_summary([])
        
        # Should return None for empty articles
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main() 