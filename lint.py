#!/usr/bin/env python3
"""
Lint script for RSS Buddy.

This script runs flake8 on the codebase with the configuration
defined in .flake8 file. It provides options for checking specific files
or directories, and reporting statistics.
"""
import argparse
import os
import sys
import subprocess
from typing import List, Optional

def run_flake8(paths: List[str], statistics: bool = False, count: bool = False) -> int:
    """
    Run flake8 on the specified paths.
    
    Args:
        paths: List of file or directory paths to lint
        statistics: Whether to show statistics
        count: Whether to show count of errors
        
    Returns:
        int: Return code (0 for success, non-zero for errors)
    """
    cmd = ["flake8"]
    
    if statistics:
        cmd.append("--statistics")
    
    if count:
        cmd.append("--count")
    
    cmd.extend(paths)
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)

def main():
    """Parse arguments and run the linter."""
    parser = argparse.ArgumentParser(description="Run flake8 linter on the codebase")
    
    parser.add_argument(
        "--paths",
        nargs="+",
        default=["src", "tests", "run_rss_buddy.py", "run_tests.py", "setup.py"],
        help="Paths to lint (default: src tests *.py)"
    )
    
    parser.add_argument(
        "--statistics",
        action="store_true",
        help="Show statistics about errors"
    )
    
    parser.add_argument(
        "--count",
        action="store_true",
        help="Show total count of errors"
    )
    
    args = parser.parse_args()
    
    # Ensure flake8 is installed
    try:
        import flake8
    except ImportError:
        print("flake8 is not installed. Install it with: pip install flake8")
        return 1
    
    # Run the linter
    return run_flake8(args.paths, args.statistics, args.count)

if __name__ == "__main__":
    sys.exit(main()) 