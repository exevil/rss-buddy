#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

# Check if OpenAI API key is provided as argument or in env var
if [ -n "$1" ]; then
    export OPENAI_API_KEY="$1"
elif [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OpenAI API key not provided"
    echo "Usage: $0 [OPENAI_API_KEY]"
    echo "  or set OPENAI_API_KEY environment variable before running"
    echo "  or add it to a .env file"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Run the RSS processor
echo "Running rss-buddy..."
python rss_processor.py

# Generate GitHub Pages (if --pages option is provided)
if [ "$2" == "--pages" ]; then
    echo "Generating GitHub Pages..."
    python generate_pages.py processed_feeds docs
    echo "GitHub Pages files generated in docs/ directory"
fi

# Deactivate virtual environment
deactivate

echo "Done!" 