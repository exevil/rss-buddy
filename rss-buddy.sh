#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

# Check if all required environment variables are set
REQUIRED_VARS=("OPENAI_API_KEY" "RSS_FEEDS" "DAYS_LOOKBACK" "AI_MODEL" "SUMMARY_MAX_TOKENS" "USER_PREFERENCE_CRITERIA")
MISSING_VARS=()

# Check if OpenAI API key is provided as argument or in env var
if [ -n "$1" ]; then
    export OPENAI_API_KEY="$1"
fi

# Check all required variables
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS+=("$VAR")
    fi
done

# If any variables are missing, show an error
if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "Error: The following required environment variables are not set:"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    echo ""
    echo "Please set these variables in your environment or in a .env file."
    echo "Example .env file content:"
    echo "OPENAI_API_KEY=your-key-here"
    echo "RSS_FEEDS=https://example.com/feed1.xml,https://example.com/feed2.xml"
    echo "DAYS_LOOKBACK=7"
    echo "AI_MODEL=gpt-4"
    echo "SUMMARY_MAX_TOKENS=150"
    echo "USER_PREFERENCE_CRITERIA=\"Your criteria for article evaluation\""
    exit 1
fi

# Run the RSS processor
echo "Running rss-buddy..."

# Check if --pages option is provided among arguments
GENERATE_PAGES_FLAG=""
for arg in "$@"; do
    if [ "$arg" == "--pages" ]; then
        echo "Will generate GitHub Pages..."
        GENERATE_PAGES_FLAG="--generate-pages"
        break
    fi
done

# Construct the command arguments directly, ensuring variables are quoted
# Using OUTPUT_DIR env var if set, otherwise default to processed_feeds
./run_rss_buddy.py \
    --api-key "$OPENAI_API_KEY" \
    --feeds "$RSS_FEEDS" \
    --days-lookback "$DAYS_LOOKBACK" \
    --model "$AI_MODEL" \
    --max-tokens "$SUMMARY_MAX_TOKENS" \
    --criteria "$USER_PREFERENCE_CRITERIA" \
    --output-dir "${OUTPUT_DIR:-processed_feeds}" \
    $GENERATE_PAGES_FLAG

# Removed VENV deactivation - handled by workflow

echo "Done!" 