#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the temporary venv directory name
VENV_DIR=".test_venv_$$" # Add PID for potential parallel runs, though unlikely needed

# Function to ensure cleanup even if the script fails
cleanup() {
  echo "Cleaning up temporary venv: $VENV_DIR"
  # Deactivate isn't strictly necessary as we aren't activating globally
  # but good practice if activation was used.
  # deactivate 2>/dev/null || true
  rm -rf "$VENV_DIR"
}

# Register the cleanup function to run on script exit (normal or error)
trap cleanup EXIT

echo "--- Creating temporary virtual environment ($VENV_DIR)..."
# Use python3 explicitly if needed, or just python if aliased correctly
python3 -m venv "$VENV_DIR"

echo "--- Installing dependencies (including dev)..."
# Use the pip from the new venv. Install in editable mode with dev extras.
"$VENV_DIR/bin/pip" install --quiet -e ".[dev]"

echo "--- Running tests using run_tests.py..."
# Execute run_tests.py using the python from the new venv
# Pass any command-line arguments received by test.sh to run_tests.py
"$VENV_DIR/bin/python" run_tests.py "$@"

echo "--- Tests finished successfully."
# Cleanup will happen automatically via trap EXIT

# Explicitly exit with success code
exit 0 