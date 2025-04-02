#!/usr/bin/env python3
"""Run all tests for the RSS Buddy project."""
import argparse
import os
import subprocess
import sys
import unittest


def run_lint(paths=None, skip_on_fail=False):
    """Run the linter on the codebase.
    
    Args:
        paths: List of paths to lint, defaults to standard paths
        skip_on_fail: If True, continue execution even if linting fails
        
    Returns:
        int: 0 for success, 1 for failure (or 0 if skip_on_fail is True)
    """
    if paths is None:
        paths = ["src", "tests", "run_rss_buddy.py", "run_tests.py", "setup.py"]
    
    print("Running linter...")
    cmd = ["python", "lint.py", "--statistics", "--paths"] + paths
    result = subprocess.call(cmd)
    
    if result != 0 and not skip_on_fail:
        print("Linting failed. Fix the issues or use --skip-lint to skip linting.")
        return 1
    
    return 0


def run_tests(verbosity=1):
    """Run all tests in the tests directory."""
    # Add src directory to path to allow importing our package
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
    
    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests')
    test_runner = unittest.TextTestRunner(verbosity=verbosity)
    result = test_runner.run(test_suite)
    
    # Return appropriate exit code (0 for success, 1 for failure)
    return 0 if result.wasSuccessful() else 1


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run RSS Buddy tests")
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increase output verbosity"
    )
    
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip linting before running tests"
    )
    
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="Run only linting, skip tests"
    )
    
    parser.add_argument(
        "--lint-paths",
        nargs="+",
        help="Specific paths to lint (default: src tests *.py)"
    )
    
    return parser.parse_args()


def main():
    """Run linting and tests based on command-line arguments."""
    args = parse_args()
    verbosity = 2 if args.verbose else 1
    
    # Skip everything if all args are default
    if not args.skip_lint and not args.lint_only:
        # Run linter
        lint_result = run_lint(args.lint_paths)
        if lint_result != 0:
            return lint_result
    
    # Run tests unless --lint-only is specified
    if not args.lint_only:
        return run_tests(verbosity)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 
