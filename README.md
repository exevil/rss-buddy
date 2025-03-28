# rss-buddy

Help filtering out and summarizing my RSS feeds.

## Overview

RSS Buddy is a Python script that processes RSS feeds, extracts recent news, and creates filtered RSS feeds based on user preferences. It uses OpenAI to determine which articles should be shown in full and which should be consolidated into a single digest. This approach reduces noise while ensuring you don't miss important content.

## How It Works

RSS Buddy uses an innovative approach to RSS processing:

1. **Important articles** are kept as individual items and shown in full
2. **Less important articles** are consolidated into a single digest item
3. The AI analyzes each article to determine which category it belongs in

This creates a clean feed with focused content for important topics while still providing a brief overview of other news.

## Features

- Processes multiple RSS feeds
- Tracks already processed articles to avoid duplication
- Uses OpenAI to identify important articles to show in full
- Consolidates less important articles into a single digest
- Creates streamlined RSS feeds that can be read by any RSS reader
- Designed for automated execution with tools like GitHub Actions
- Can generate a GitHub Pages site to browse processed feeds
- Smart digest handling: only updates the digest ID when content changes
- Precise lookback window: processes items from the past N days (configurable)
- Robust date parsing with fallback mechanisms for handling problematic timezone formats
- Maintains all recent articles in the output feed, regardless of whether they've been processed before

## Setup

### Configuration

RSS Buddy uses environment variables for all configuration, which can be set either directly or through a `.env` file. Here's how to set it up:

1. Copy the example environment file:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file to include your OpenAI API key and customize your preferences.

3. Alternatively, you can set environment variables directly:
   ```
   export OPENAI_API_KEY="your-api-key-here"
   export RSS_FEEDS="https://example.com/feed1.xml,https://example.com/feed2.xml"
   ```

### Configuration Options

| Environment Variable    | Description                                    | Default                  |
|-------------------------|------------------------------------------------|--------------------------|
| `OPENAI_API_KEY`        | Your OpenAI API key (required)                | -                        |
| `RSS_FEEDS`             | List of RSS feed URLs (newline separated) | See example below        |
| `USER_PREFERENCE_CRITERIA` | Criteria for determining article preferences | See example below        |
| `DAYS_LOOKBACK`         | Number of days to look back for articles | 7                        |
| `AI_MODEL`              | OpenAI model to use                           | gpt-4                    |
| `SUMMARY_MAX_TOKENS`    | Maximum token length for summaries           | 150                      |

### Example Configuration

```env
# OpenAI API Key (required)
OPENAI_API_KEY=your-openai-api-key-here

# RSS Feeds to process (one per line or comma-separated)
RSS_FEEDS="https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml
https://www.wired.com/feed/rss
https://feeds.arstechnica.com/arstechnica/index"

# User preference criteria for determining which articles to show in full
USER_PREFERENCE_CRITERIA="When determining if an article should be shown in full or summarized, consider these factors:
- Technical deep dives in machine learning, AI, and quantum computing should be shown in FULL
- Breaking news about major tech companies should be shown in FULL
- General technology news can be SUMMARIZED
- Scientific breakthroughs should be shown in FULL
- Political news should be SUMMARIZED unless it relates directly to technology policy
- Entertainment news should be SUMMARIZED"

# Number of days to look back for articles
DAYS_LOOKBACK=7

# OpenAI model to use
AI_MODEL=gpt-4

# Maximum token length for summaries
SUMMARY_MAX_TOKENS=150
```

## Output Format

The processed feeds contain two types of items:

1. **Full Articles**: Important articles are kept as individual items with full content
2. **Digest Item**: A single item containing a summary of all other articles from the period

The digest item is organized by themes and highlights the most noteworthy stories, so you can quickly scan what else happened without reading every article.

## Usage

### Installing as a Package

You can install RSS Buddy as a package:

```
pip install -e .
```

This will make the `rss-buddy` command available in your environment.

### Using the Command-Line Runner

To run RSS Buddy from the command line:

```
./run_rss_buddy.py --api-key YOUR_OPENAI_API_KEY --feeds "https://example.com/feed1.xml,https://example.com/feed2.xml"
```

Or using environment variables or a `.env` file:

```
./run_rss_buddy.py
```

Note: The scripts `run_rss_buddy.py` and `run_tests.py` are executable, so you can run them directly without explicitly calling Python.

### Command-Line Options

```
usage: run_rss_buddy.py [-h] [--api-key API_KEY] [--feeds FEEDS] [--output-dir OUTPUT_DIR]
                        [--days-lookback DAYS_LOOKBACK] [--model MODEL] [--max-tokens MAX_TOKENS]
                        [--criteria CRITERIA] [--generate-pages]
```

### Using the Shell Script

An alternative way to run RSS Buddy is with the provided shell script:

```
./rss-buddy.sh YOUR_OPENAI_API_KEY
```

To generate GitHub Pages output:

```
./rss-buddy.sh YOUR_OPENAI_API_KEY --pages
```

## Advanced Features

### Robust Date Handling

RSS Buddy includes sophisticated date handling capabilities:

- **Multiple Fallback Mechanisms**: Can parse dates in various formats, including those with problematic timezone abbreviations (like PDT, EST, CEST).
- **Timezone Awareness**: Properly compares dates with different timezone information.
- **Regex-Based Extraction**: For extremely non-standard formats, extracts date and time components using regular expressions.
- **Complete Timezone Mapping**: Handles abbreviations like PDT, PST, EDT, EST, CEST, CET, AEST, and AEDT.

### Smart Article Processing

RSS Buddy optimizes AI usage by:

1. **Processing New Articles**: Uses AI to evaluate only newly discovered articles
2. **Preserving Previous Evaluations**: Keeps track of previous categorizations
3. **Including All Recent Articles**: Shows all articles from within the lookback window, regardless of whether they've been processed before

This approach ensures that:
- You see all recent content
- AI costs are minimized by only evaluating new content
- The RSS feed remains comprehensive within your specified time window

## Development

### Project Structure

The codebase consists of these key files:
- `src/rss_buddy/` - Main package containing the core functionality
  - `main.py`: Entry point for the application
  - `feed_processor.py`: Processes RSS feeds and creates filtered outputs
  - `state_manager.py`: Manages the state tracking to avoid reprocessing articles
  - `ai_interface.py`: Interface for AI operations with real and mock implementations
  - `generate_pages.py`: Creates HTML pages for browsing the feeds
- `run_rss_buddy.py`: Command-line script to run the processor
- `run_tests.py`: Script to run the test suite
- `rss-buddy.sh`: A convenience shell script to run the processor

### Running the Tests

RSS Buddy has a comprehensive test suite that can be run without needing an actual OpenAI API key or real RSS feeds:

```
./run_tests.py
```

For verbose output:

```
./run_tests.py -v
```

The tests cover all the main components:
- State Manager: Tests for state tracking and persistence
- AI Interface: Tests for both real and mock AI interfaces
- Feed Processor: Tests for feed processing and article evaluation
- Date Handling: Specialized tests for the date parsing and comparison logic

## GitHub Pages Setup

Processed RSS feeds are saved directly to GitHub Pages with filenames based on the original feed titles. These XML files can be imported into any RSS reader.

You can access your processed feeds through a web interface at `https://yourusername.github.io/rss-buddy/`, or directly use the XML files as feed URLs in your RSS reader.
