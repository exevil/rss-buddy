#!/usr/bin/env python3
"""Run all tests for the RSS Buddy project."""

import argparse
import os
import subprocess
import sys
import unittest


def run_lint(paths=None, skip_on_fail=False):
    """Run the formatter and linter (Ruff) on the codebase.

    Args:
        paths: List of paths to lint/format, defaults to paths defined in lint.py
        skip_on_fail: If True, continue execution even if formatting/linting fails

    Returns:
        int: 0 for success, 1 for failure (or 0 if skip_on_fail is True)
    """
    print("Running Ruff (format and check)...")
    cmd = ["python", "lint.py"]
    # Pass paths if provided, otherwise lint.py uses its defaults
    if paths:
        cmd.append("--paths")
        cmd.extend(paths)

    # Add arguments for verbosity/statistics if desired, e.g.:
    # cmd.append("--statistics")
    # cmd.append("--show-source")

    result = subprocess.call(cmd)

    if result != 0 and not skip_on_fail:
        print("Ruff format/check failed. Fix the issues or use --skip-lint to skip linting.")
        return 1
    elif result != 0 and skip_on_fail:
        print("Warning: Ruff format/check failed, but continuing due to --skip-lint.")
        return 0  # Return 0 because we are skipping the failure

    return 0


def run_tests(verbosity=1):
    """Run all tests in the tests directory."""
    # Add src directory to path to allow importing our package
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover("tests")
    test_runner = unittest.TextTestRunner(verbosity=verbosity)
    result = test_runner.run(test_suite)

    # Return appropriate exit code (0 for success, 1 for failure)
    return 0 if result.wasSuccessful() else 1


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run RSS Buddy tests")

    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")

    parser.add_argument(
        "--skip-lint", action="store_true", help="Skip linting before running tests"
    )

    parser.add_argument("--lint-only", action="store_true", help="Run only linting, skip tests")

    parser.add_argument(
        "--lint-paths", nargs="+", help="Specific paths to lint (default: src tests *.py)"
    )

    return parser.parse_args()


def main():
    """Run linting and tests based on command-line arguments."""
    args = parse_args()
    verbosity = 2 if args.verbose else 1

    lint_result = 0
    test_result = 0

    # Handle --lint-only case first
    if args.lint_only:
        print("Running lint only...")
        lint_result = run_lint(args.lint_paths)
        return lint_result

    # Handle default case (lint then test)
    if not args.skip_lint:
        lint_result = run_lint(args.lint_paths)
        if lint_result != 0:
            return lint_result  # Exit early if lint fails

    # Run tests (if lint passed or was skipped)
    test_result = run_tests(verbosity)

    # Final exit code is based on test result (lint already passed or was skipped)
    return test_result


if __name__ == "__main__":
    sys.exit(main())
