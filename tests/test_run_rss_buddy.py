"""Tests for the command-line runner script run_rss_buddy.py."""

import os
import sys
import unittest
from unittest.mock import patch

# Add root directory to path to allow importing run_rss_buddy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the main function from the script we want to test
# Note: We need to be careful about how imports work when running a script vs importing a module
try:
    from run_rss_buddy import main as script_main
    from run_rss_buddy import parse_args  # To mock its return value
except ImportError:
    # This might happen depending on execution context, try relative import if needed
    print("Could not import run_rss_buddy directly, skipping these tests.")

    # Define dummy main to avoid errors if tests are discovered but script can't be imported
    def script_main():
        """Dummy function if import fails."""
        pass

    def parse_args():
        """Dummy function if import fails."""
        pass


# Define a dummy class for argparse results
class MockArgs:
    """A simple class to mock argparse Namespace objects."""

    def __init__(self, **kwargs):
        """Initialize with keyword arguments as attributes."""
        self.__dict__.update(kwargs)


@unittest.skipIf(script_main is None, "Skipping run_rss_buddy tests due to import issues.")
class TestRunRssBuddyScript(unittest.TestCase):
    """Tests the run_rss_buddy.py script execution flow."""

    @patch("run_rss_buddy.parse_args")
    @patch("run_rss_buddy.rss_buddy_main")  # Mock the main processing function
    @patch("rss_buddy.generate_pages.generate_pages")  # Corrected patch target
    @patch("run_rss_buddy.os.environ")  # Mock environment setting
    @patch("run_rss_buddy.load_dotenv")  # Mock dotenv loading
    def test_run_with_generate_pages(
        self,
        mock_load_dotenv,
        mock_environ,
        mock_generate_pages,
        mock_rss_buddy_main,
        mock_parse_args,
    ):
        """Test running the script with the --generate-pages flag."""
        # --- Setup Mocks ---
        # Mock parse_args to return args including --generate-pages and a specific output dir
        mock_output_dir = "test_state_dir"
        mock_parse_args.return_value = MockArgs(
            api_key="test_key",
            feeds="http://test.feed/rss",
            output_dir=mock_output_dir,
            days_lookback=3,
            model="test_model",
            max_tokens=100,
            criteria="test_criteria",
            generate_pages=True,
        )

        # Mock the main processing function to return success (exit code 0)
        mock_rss_buddy_main.return_value = 0

        # --- Run Test ---
        # Execute the main function from the script
        exit_code = script_main()

        # --- Assertions ---
        self.assertEqual(exit_code, 0)  # Expect success

        # Verify environment variables were set (optional, but good check)
        # We mocked os.environ directly, check calls to its __setitem__
        # Note: Direct os.environ mocking can be complex; checking calls might suffice
        # Example: self.assertIn(call('OPENAI_API_KEY', 'test_key'), mock_environ.__setitem__.call_args_list)

        # Verify the main processing function was called
        mock_rss_buddy_main.assert_called_once()

        # Verify generate_pages was called BECAUSE generate_pages=True and exit_code=0
        mock_generate_pages.assert_called_once()

        # Verify generate_pages was called with the correct arguments
        # It should read data from the script's output_dir and write to 'docs'
        mock_generate_pages.assert_called_once_with(data_dir=mock_output_dir, output_dir="docs")

    @patch("run_rss_buddy.parse_args")
    @patch("run_rss_buddy.rss_buddy_main")  # Mock the main processing function
    @patch("rss_buddy.generate_pages.generate_pages")  # Corrected patch target
    @patch("run_rss_buddy.os.environ")  # Mock environment setting
    @patch("run_rss_buddy.load_dotenv")  # Mock dotenv loading
    def test_run_with_generate_pages_main_fails(
        self,
        mock_load_dotenv,
        mock_environ,
        mock_generate_pages,
        mock_rss_buddy_main,
        mock_parse_args,
    ):
        """Test --generate-pages is skipped if main processing fails."""
        # --- Setup Mocks ---
        # Mock parse_args as before, with generate_pages=True
        mock_output_dir = "test_state_dir"
        mock_parse_args.return_value = MockArgs(
            api_key="test_key",
            feeds="http://test.feed/rss",
            output_dir=mock_output_dir,
            days_lookback=3,
            model="test_model",
            max_tokens=100,
            criteria="test_criteria",
            generate_pages=True,
        )

        # Mock the main processing function to return FAILURE (exit code 1)
        mock_rss_buddy_main.return_value = 1

        # --- Run Test ---
        # Execute the main function from the script
        exit_code = script_main()

        # --- Assertions ---
        self.assertEqual(exit_code, 1)  # Expect failure code from main

        # Verify the main processing function was called
        mock_rss_buddy_main.assert_called_once()

        # Verify generate_pages was NOT called because main processing failed
        mock_generate_pages.assert_not_called()

    @patch("run_rss_buddy.parse_args")
    @patch("run_rss_buddy.rss_buddy_main")  # Mock the main processing function
    @patch("rss_buddy.generate_pages.generate_pages")  # Corrected patch target
    @patch("run_rss_buddy.os.environ")  # Mock environment setting
    @patch("run_rss_buddy.load_dotenv")  # Mock dotenv loading
    def test_run_without_generate_pages(
        self,
        mock_load_dotenv,
        mock_environ,
        mock_generate_pages,
        mock_rss_buddy_main,
        mock_parse_args,
    ):
        """Test running the script WITHOUT the --generate-pages flag."""
        # --- Setup Mocks ---
        # Mock parse_args, this time with generate_pages=False
        mock_output_dir = "test_state_dir"
        mock_parse_args.return_value = MockArgs(
            api_key="test_key",
            feeds="http://test.feed/rss",
            output_dir=mock_output_dir,
            days_lookback=3,
            model="test_model",
            max_tokens=100,
            criteria="test_criteria",
            generate_pages=False,  # Explicitly false
        )

        # Mock the main processing function to return success
        mock_rss_buddy_main.return_value = 0

        # --- Run Test ---
        # Execute the main function from the script
        exit_code = script_main()

        # --- Assertions ---
        self.assertEqual(exit_code, 0)  # Expect success code from main

        # Verify the main processing function was called
        mock_rss_buddy_main.assert_called_once()

        # Verify generate_pages was NOT called because generate_pages=False
        mock_generate_pages.assert_not_called()


# We need to patch sys.argv to test parse_args directly
class TestArgParsing(unittest.TestCase):
    """Tests the parse_args function directly."""

    def setUp(self):
        """Keep track of original sys.argv."""
        self.original_argv = sys.argv

    def tearDown(self):
        """Restore original sys.argv."""
        sys.argv = self.original_argv

    def test_parse_args_all_required_provided(self):
        """Test parsing when all required arguments are provided."""
        test_argv = [
            "run_rss_buddy.py",
            "--api-key",
            "test_key",
            "--feeds",
            "http://feed1.com,http://feed2.com",
            "--days-lookback",
            "7",
            "--model",
            "gpt-4-test",
            "--max-tokens",
            "150",
            "--criteria",
            "Test Criteria",
            "--output-dir",
            "custom_output",
        ]
        sys.argv = test_argv
        args = parse_args()

        self.assertEqual(args.api_key, "test_key")
        self.assertEqual(args.feeds, "http://feed1.com,http://feed2.com")
        self.assertEqual(args.days_lookback, 7)
        self.assertEqual(args.model, "gpt-4-test")
        self.assertEqual(args.max_tokens, 150)
        self.assertEqual(args.criteria, "Test Criteria")
        self.assertEqual(args.output_dir, "custom_output")
        self.assertFalse(args.generate_pages)

    def test_parse_args_defaults(self):
        """Test default values for optional arguments."""
        test_argv = [
            "run_rss_buddy.py",
            "--api-key",
            "test_key",
            "--feeds",
            "http://feed1.com",
            "--days-lookback",
            "3",
            "--model",
            "gpt-3.5-test",
            "--max-tokens",
            "100",
            "--criteria",
            "Simple Criteria",
        ]
        sys.argv = test_argv
        args = parse_args()

        self.assertEqual(args.output_dir, "processed_feeds")  # Default value
        self.assertFalse(args.generate_pages)  # Default value

    def test_parse_args_generate_pages_flag(self):
        """Test the --generate-pages flag sets the value to True."""
        test_argv = [
            "run_rss_buddy.py",
            "--api-key",
            "test_key",
            "--feeds",
            "http://feed1.com",
            "--days-lookback",
            "3",
            "--model",
            "gpt-3.5-test",
            "--max-tokens",
            "100",
            "--criteria",
            "Simple Criteria",
            "--generate-pages",
        ]
        sys.argv = test_argv
        args = parse_args()

        self.assertTrue(args.generate_pages)

    def test_parse_args_missing_required(self):
        """Test that argparse exits if a required argument is missing."""
        test_argv = [
            "run_rss_buddy.py",
            # Missing --api-key
            "--feeds",
            "http://feed1.com",
            "--days-lookback",
            "3",
            "--model",
            "gpt-3.5-test",
            "--max-tokens",
            "100",
            "--criteria",
            "Simple Criteria",
        ]
        sys.argv = test_argv
        # argparse.parse_args() calls sys.exit() on error, which raises SystemExit
        with self.assertRaises(SystemExit):
            parse_args()

    def test_parse_args_invalid_type(self):
        """Test that argparse exits if an argument has the wrong type."""
        test_argv = [
            "run_rss_buddy.py",
            "--api-key",
            "test_key",
            "--feeds",
            "http://feed1.com",
            "--days-lookback",
            "not_an_int",  # Invalid type
            "--model",
            "gpt-3.5-test",
            "--max-tokens",
            "100",
            "--criteria",
            "Simple Criteria",
        ]
        sys.argv = test_argv
        with self.assertRaises(SystemExit):
            parse_args()


if __name__ == "__main__":
    unittest.main()
