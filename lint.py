#!/usr/bin/env python3
"""Lint and format script for RSS Buddy using Ruff.

This script runs ruff format and ruff check --fix on the codebase
with the configuration defined in pyproject.toml.
It provides options for checking specific files or directories.
"""

import argparse
import glob
import os

# Remove shutil import if no longer needed after removing run_flake8
# import shutil
import subprocess
import sys

# Remove the run_flake8 function as it's no longer used
# def run_flake8(...): ...


def main():
    """Parse arguments and run the formatter and linter."""
    parser = argparse.ArgumentParser(description="Run Ruff formatter and linter on the codebase")

    parser.add_argument(
        "--paths",
        nargs="+",
        default=[
            "src",
            "tests",
            "run_rss_buddy.py",
            "run_tests.py",
            "setup.py",
            "lint.py",
        ],  # Added lint.py itself
        help="Paths to format and lint (default: src tests *.py lint.py)",
    )

    # Ruff format doesn't have --statistics or --count equivalents in the same way
    # We'll keep the check arguments though
    parser.add_argument(
        "--statistics", action="store_true", help="Show statistics during check phase"
    )

    parser.add_argument(
        "--show-source",
        action="store_true",
        help="Show source code snippets for errors during check phase",
    )

    args = parser.parse_args()

    # --- Determine target files ---
    all_paths = []
    for path_pattern in args.paths:
        # Handle potential directory patterns first
        if os.path.isdir(path_pattern):
            all_paths.extend(glob.glob(os.path.join(path_pattern, "**", "*.py"), recursive=True))
            all_paths.extend(
                glob.glob(os.path.join(path_pattern, "*.py"))
            )  # Add py files directly in the dir
        elif os.path.isfile(path_pattern) and path_pattern.endswith(".py"):
            all_paths.append(path_pattern)
        else:  # Assume it might be a glob pattern for files
            all_paths.extend(glob.glob(path_pattern, recursive=True))

    # Filter for actual files and remove duplicates
    target_files = sorted({f for f in all_paths if os.path.isfile(f)})

    if not target_files:
        print("No Python files found to format or lint based on provided paths.")
        return 0

    # --- Run Ruff Format ---
    print("\n--- Running Ruff Formatter ---")
    format_command = ["ruff", "format"] + target_files
    print(f"Running: {' '.join(format_command)}")
    format_result = subprocess.run(format_command, capture_output=True, text=True)

    print(format_result.stdout)
    if format_result.stderr:
        print("Formatter Error Output:", file=sys.stderr)
        print(format_result.stderr, file=sys.stderr)

    # Check formatter success (return code 0 indicates success)
    if format_result.returncode != 0:
        print("\nFormatter failed.", file=sys.stderr)
        # Decide if formatting failure should stop the process
        # For now, we continue to linting, but you might want to return 1 here
        # return 1

    # --- Run Ruff Check ---
    print("\n--- Running Ruff Linter (with fixes) ---")
    check_command = ["ruff", "check", "--fix"] + target_files
    if args.statistics:
        check_command.append("--statistics")
    if args.show_source:
        check_command.append("--show-source")

    print(f"Running: {' '.join(check_command)}")
    check_result = subprocess.run(check_command, capture_output=True, text=True)

    print(check_result.stdout)
    if check_result.stderr:
        print("Linter Error Output:", file=sys.stderr)
        print(check_result.stderr, file=sys.stderr)

    # Check linting success (return code 0 means no errors remain after fixing)
    if check_result.returncode != 0:
        print("\nRuff check found errors (even after attempting fixes).", file=sys.stderr)
        return 1
    else:
        print("\nRuff format and check passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
