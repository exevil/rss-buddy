#!/usr/bin/env python3
"""
Run all tests for the RSS Buddy project.
"""
import os
import sys
import unittest
import argparse

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
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    verbosity = 2 if args.verbose else 1
    sys.exit(run_tests(verbosity)) 