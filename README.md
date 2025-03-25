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

## Project Structure

This project uses two branches for different purposes:

- **main**: Contains the source code and all scripts
- **output**: Contains only the processed feeds and state data

The main codebase consists of these key files:
- `rss_processor.py`: The main script that processes RSS feeds and creates filtered outputs
- `state_manager.py`: Manages the state tracking to avoid reprocessing articles
- `generate_pages.py`: Creates HTML pages for browsing the feeds
- `rss-buddy.sh`: A convenience shell script to run the processor

This separation keeps the repository clean and makes it easier to browse either the code or the generated feeds.

## Features

- Processes multiple RSS feeds
- Tracks already processed articles to avoid duplication
- Uses OpenAI to identify important articles to show in full
- Consolidates less important articles into a single digest
- Creates streamlined RSS feeds that can be read by any RSS reader
- Designed for automated execution with tools like GitHub Actions
- Can generate a GitHub Pages site to browse processed feeds

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
| `RSS_FEEDS`             | Comma-separated list of RSS feed URLs         | See example below        |
| `USER_PREFERENCE_CRITERIA` | Criteria for determining article preferences | See example below        |
| `DAYS_LOOKBACK`         | Number of days to look back for articles      | 7                        |
| `AI_MODEL`              | OpenAI model to use                           | gpt-4                    |
| `SUMMARY_MAX_TOKENS`    | Maximum token length for summaries           | 150                      |

### Example Configuration

```env
# OpenAI API Key (required)
OPENAI_API_KEY=your-openai-api-key-here

# RSS Feeds to process (comma-separated)
RSS_FEEDS=https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml,https://www.wired.com/feed/rss

# User preference criteria for determining which articles to show in full
USER_PREFERENCE_CRITERIA=When determining if an article should be shown in full or summarized, consider these factors:
- Technical deep dives in machine learning, AI, and quantum computing should be shown in FULL
- Breaking news about major tech companies should be shown in FULL
- General technology news can be SUMMARIZED
- Scientific breakthroughs should be shown in FULL
- Political news should be SUMMARIZED unless it relates directly to technology policy
- Entertainment news should be SUMMARIZED

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

### Using the Shell Script (Recommended)

The easiest way to run RSS Buddy is with the provided shell script:

```
./rss-buddy.sh YOUR_OPENAI_API_KEY
```

Or if you have your API key set as an environment variable or in a `.env` file:

```
./rss-buddy.sh
```

To generate GitHub Pages output:

```
./rss-buddy.sh YOUR_OPENAI_API_KEY --pages
```

The script will:
- Load environment variables from `.env` file if it exists
- Create a virtual environment if needed
- Install dependencies
- Run the RSS processor
- Optionally generate GitHub Pages files

### Manual Setup

If you prefer to set up manually:

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set your configuration using environment variables or a `.env` file

3. Run the script:
   ```
   python rss_processor.py
   ```

## State Tracking

RSS Buddy tracks processed articles in a state file (`processed_state.json`) to avoid reprocessing the same content. This:

- Reduces OpenAI API usage and costs
- Makes the tool ideal for scheduled runs (e.g., via GitHub Actions)
- Ensures only new articles are processed each time

The state file is stored in the `output` branch and is automatically maintained between runs.

## GitHub Actions and Pages Setup

You can automate RSS Buddy with GitHub Actions and publish the results with GitHub Pages:

1. Fork or clone this repository
2. Store your OpenAI API key as a repository secret named `OPENAI_API_KEY`
3. Set other configuration variables in repository secrets or directly in the workflow file
4. Enable GitHub Actions in your repository
5. Enable GitHub Pages in your repository settings, selecting the "GitHub Actions" as the source
6. The included workflow will:
   - Run every 12 hours (configurable)
   - Process your RSS feeds
   - Store outputs in the `output` branch
   - Generate HTML pages for browsing the feeds
   - Deploy to GitHub Pages
   - Maintain state between runs

To manually trigger the workflow, go to the Actions tab in your repository and click "Run workflow".

## Output

Processed RSS feeds are saved to the `output` branch with filenames based on the original feed titles. These XML files can be imported into any RSS reader.

If you're using GitHub Pages, you can access your processed feeds through a web interface at `https://yourusername.github.io/rss-buddy/`.

## Customization

You can customize RSS Buddy by changing the configuration variables in your `.env` file or environment variables:

- Change `DAYS_LOOKBACK` to adjust how far back to look for articles
- Modify `AI_MODEL` to use a different OpenAI model
- Adjust `SUMMARY_MAX_TOKENS` to control summary length
- Customize `USER_PREFERENCE_CRITERIA` to better match your reading preferences
