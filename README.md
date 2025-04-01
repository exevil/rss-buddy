# rss-buddy

Help filtering out and summarizing my RSS feeds.

## Overview

RSS Buddy processes RSS feeds using OpenAI to determine which articles should be shown in full and which should be consolidated into a single digest, reducing noise while ensuring you don't miss important content.

## How It Works

1. **Important articles** are kept as individual items and shown in full
2. **Less important articles** are consolidated into a single digest item
3. The AI analyzes each article to determine which category it belongs in

## Features

- Processes multiple RSS feeds
- Tracks already processed articles to avoid duplication
- Uses OpenAI to identify important articles to show in full
- Consolidates less important articles into a single digest
- Creates streamlined feeds readable by any RSS reader
- Supports automated execution with GitHub Actions
- Generates GitHub Pages site to browse processed feeds
- Smart digest handling: only updates digest ID when content changes
- Configurable lookback window for processing recent articles
- Robust date parsing with fallback mechanisms for problematic timezone formats
- Maintains all recent articles in output feeds

## Configuration

RSS Buddy requires the following environment variables, which can be set in a `.env` file or directly in your shell:

| Environment Variable    | Description                                    |
|-------------------------|------------------------------------------------|
| `OPENAI_API_KEY`        | Your OpenAI API key                           |
| `RSS_FEEDS`             | List of RSS feed URLs (newline or comma-separated) |
| `USER_PREFERENCE_CRITERIA` | Criteria for determining article preferences |
| `DAYS_LOOKBACK`         | Number of days to look back for articles       |
| `AI_MODEL`              | OpenAI model to use                           |
| `SUMMARY_MAX_TOKENS`    | Maximum token length for summaries            |

Only `OUTPUT_DIR` is optional and defaults to "processed_feeds".

### Example Configuration

```env
# OpenAI API Key 
OPENAI_API_KEY=your-openai-api-key-here

# RSS Feeds to process (one per line or comma-separated)
RSS_FEEDS="https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml
https://www.wired.com/feed/rss
https://feeds.arstechnica.com/arstechnica/index"

# User preference criteria
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

## Usage

### Installing as a Package

```
pip install -e .
```

This will make the `rss-buddy` command available in your environment.

### Command-Line Options

There are two ways to run RSS Buddy:

1. **Using run_rss_buddy.py with explicit parameters:**

```
./run_rss_buddy.py --api-key YOUR_API_KEY --feeds "https://example.com/feed1.xml" \
                  --days-lookback 7 --model "gpt-4" --max-tokens 150 \
                  --criteria "Your criteria" [--output-dir DIR] [--generate-pages]
```

2. **Using the shell script with environment variables:**

```
# First set up your .env file or export variables
./rss-buddy.sh [YOUR_API_KEY] [--pages]
```

Note: When using the shell script, all other required parameters must be provided via environment variables or a `.env` file.

## Output Format

The processed feeds contain two types of items:

1. **Full Articles**: Important articles as individual items
2. **Digest Item**: A single item summarizing all less important articles

The digest is organized by themes to quickly scan what happened without reading every article.

## Advanced Features

### Robust Date Handling

- Multiple fallback mechanisms for various date formats
- Timezone-aware comparisons
- Regex-based extraction for non-standard formats
- Complete mapping for timezone abbreviations (PDT, EST, CEST, etc.)

### Smart Article Processing

1. Uses AI only for newly discovered articles
2. Preserves previous article categorizations
3. Includes all recent articles within the lookback window

This optimizes AI usage while maintaining a comprehensive feed.

## Development

### Project Structure

- `src/rss_buddy/` - Main package
  - `main.py`: Entry point
  - `feed_processor.py`: Core feed processing logic
  - `state_manager.py`: State tracking 
  - `ai_interface.py`: AI operations interface
  - `generate_pages.py`: HTML page generation
- `run_rss_buddy.py`: Command-line runner
- `run_tests.py`: Test runner
- `rss-buddy.sh`: Convenience shell script

### Running Tests

```
./run_tests.py [-v]
```

The test suite covers state management, AI interface, feed processing, and date handling without requiring an actual OpenAI API key.

## GitHub Pages Integration

Processed feeds are saved with filenames based on the original feed titles and can be accessed at `https://yourusername.github.io/rss-buddy/` or used directly as feed URLs in any RSS reader.
