# rss-buddy

Help filtering out and summarizing my RSS feeds.

## Overview

RSS Buddy processes RSS feeds using OpenAI to determine which articles should be shown in full ("processed") and which should be consolidated into an AI-generated digest ("digest"). It then generates an HTML site for browsing the results, reducing noise while ensuring you don't miss important content.

## How It Works

1.  Fetches articles from configured RSS feeds within a specified lookback period (`DAYS_LOOKBACK`).
2.  Checks its internal state (`processed_feeds/processed_state.json`) to see if articles have already been processed.
3.  For **new** articles, it uses an AI model (e.g., GPT-4 via `ai_interface.py`) and user-defined criteria (`USER_PREFERENCE_CRITERIA`) to determine the processing preference ('FULL' or 'SUMMARY').
4.  Maps the AI preference to a `status` ('processed' or 'digest') and stores key article data including a unique ID, title, link, summary, publish date (`date`), processing status (`status`), and processing timestamp (`processed_at`) for all relevant articles in the state file.
5.  Generates an HTML site (in the `docs/` directory via `generate_pages.py`) for browsing using Jinja2 templates:
    *   An `index.html` page lists all tracked feeds.
    *   Each feed gets its own HTML page (`feed_*.html`).
    *   On a feed's page, `processed` articles are displayed individually.
    *   All `digest` articles for that feed within the lookback period are passed to the AI (`ai_interface.generate_consolidated_summary`) to generate a single, consolidated summary which is displayed in a distinct section.

## Features

- Processes multiple RSS feeds.
- Tracks already processed articles and their processing status (`processed`/`digest`) to avoid reprocessing and redundant AI calls.
- Uses OpenAI to classify **new** articles based on user criteria.
- Consolidates less important articles (`digest`) into a single AI-generated summary per feed.
- Generates a static HTML website (`docs/` directory) for easy browsing and hosting (e.g., GitHub Pages).
- Supports automated execution with GitHub Actions.
- Configurable lookback window (`DAYS_LOOKBACK`) for processing and display.
- Robust date parsing with multiple fallback mechanisms.
- Maintains state and cleans up entries older than the lookback period automatically.

## Configuration

RSS Buddy requires the following environment variables, which can be set in a `.env` file or directly in your shell:

| Environment Variable       | Description                                                |
| -------------------------- | ---------------------------------------------------------- |
| `OPENAI_API_KEY`           | Your OpenAI API key                                        |
| `RSS_FEEDS`                | List of RSS feed URLs (newline or comma-separated)         |
| `USER_PREFERENCE_CRITERIA` | Criteria for AI classification (\'FULL\' or \'SUMMARY\')    |
| `DAYS_LOOKBACK`            | Number of days to look back for processing and display     |
| `AI_MODEL`                 | OpenAI model to use (e.g., `gpt-4`, `gpt-3.5-turbo`)    |
| `SUMMARY_MAX_TOKENS`       | Maximum token length for generated digest summaries        |
| `OUTPUT_DIR`               | **Optional**: Directory to store state (`processed_state.json`). Defaults to `processed_feeds`. |

### Example Configuration

```env
# OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# RSS Feeds to process (one per line or comma-separated)
RSS_FEEDS=\"https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml\nhttps://www.wired.com/feed/rss\nhttps://feeds.arstechnica.com/arstechnica/index\"

# User preference criteria (Instruct AI when to return FULL vs SUMMARY)
USER_PREFERENCE_CRITERIA=\"When determining if an article should be shown in full or summarized, consider these factors:
- Technical deep dives in machine learning, AI, and quantum computing should be shown in FULL
- Breaking news about major tech companies should be shown in FULL
- General technology news can be SUMMARIZED
- Scientific breakthroughs should be shown in FULL
- Political news should be SUMMARIZED unless it relates directly to technology policy
- Entertainment news should be SUMMARIZED\"

# Number of days to look back for articles
DAYS_LOOKBACK=7

# OpenAI model to use
AI_MODEL=gpt-4

# Maximum token length for summaries
SUMMARY_MAX_TOKENS=150

# Optional: Directory for state file
# OUTPUT_DIR=my_rss_state
```

## Usage

### Installing the Package

You can install the package locally. This is useful for development or running the tool directly from your environment.

```bash
# Install for use (runtime dependencies only)
pip install .

# Install in editable mode with development dependencies
pip install -e .[dev]
```

This makes the `rss-buddy` command available in your environment.

### Command-Line Options

There are three main ways to run RSS Buddy:

1.  **Using the installed `rss-buddy` command:** (Recommended after installation)

    ```bash
    # Requires environment variables to be set (.env file or exported)
    rss-buddy
    ```
    This command executes the main feed processing workflow defined in `src/rss_buddy/main.py`. Note: This typically only processes feeds and updates the state file. HTML generation usually requires a separate step or flag (see below).

2.  **Using `run_rss_buddy.py` with explicit parameters:**

    ```bash
    ./run_rss_buddy.py --api-key YOUR_API_KEY --feeds \"URL1,URL2\" \
                      --days-lookback 7 --model \"gpt-4\" --max-tokens 150 \
                      --criteria \"Your criteria\" [--output-dir processed_feeds] [--generate-pages]
    ```

    *   `--output-dir`: Specifies where the `processed_state.json` file is stored (defaults to `processed_feeds`).
    *   `--generate-pages`: If included, runs the main feed processing *and then* runs the HTML generation step (`generate_pages.generate_pages`), reading state from `--output-dir` and writing HTML/JSON to the `docs/` directory.

3.  **Using the `rss-buddy.sh` convenience script:**

    ```bash
    # First set up your .env file or export required environment variables
    ./rss-buddy.sh [--pages]
    ```

    *   This script reads parameters from environment variables (falling back from command-line args if provided). See script for details.
    *   Without `--pages`, it likely only runs the feed processing step.
    *   `--pages`: Runs the main processing script and then triggers HTML generation (to `docs/`).

## Output Format

When run with the `--generate-pages` flag (or `./rss-buddy.sh --pages`, or implicitly when using the `rss-buddy` command if page generation is enabled in its logic - *check script*), the script generates a static HTML website in the `docs/` directory, suitable for deployment (e.g., via GitHub Pages).

The `docs/` directory contains:

1.  **`index.html`**: The main entry point, listing all processed feeds with links to their individual pages.
2.  **`feed_*.html`**: An individual HTML page for each processed RSS feed. The filename (`*`) is a sanitized version of the feed\'s title. Each page contains:
    *   A link to the original RSS feed URL.
    *   Articles classified as `processed` displayed individually (title, link, summary, publish date).
    *   A single `AI Digest` section containing an AI-generated summary of all articles classified as `digest` within the lookback period.
3.  **`feeds.json`**: A JSON file containing metadata about each generated feed page (title, original URL, `filename`, counts).
4.  **`metadata.json`**: A JSON file with metadata about the generation process (timestamp, counts).
5.  **`processed_state.json`**: A copy of the state file used for the generation.

## Advanced Features

### Robust Date Handling

- Multiple fallback mechanisms for various date formats (standard parsing, timezone normalization, `ignoretz`, fuzzy matching, regex extraction).
- Timezone-aware comparisons (all dates converted to UTC internally).
- Handles common timezone abbreviations (PDT, EST, CEST, etc.).

### Smart State Management & Processing

- Uses AI only for newly discovered articles within the lookback window.
- Persists article processing status (`processed` / `digest`) in the state file (`processed_feeds/processed_state.json` by default).
- Automatically cleans up entries older than `DAYS_LOOKBACK` from the state file on save.
- Ensures the final HTML output reflects all relevant articles (processed and digest) within the `DAYS_LOOKBACK` period from the run date.

This optimizes AI usage while maintaining a comprehensive and up-to-date view of relevant content.

## Development

### Project Structure

- `src/rss_buddy/` - Main package
  - `main.py`: Orchestrates the *feed processing and state saving* workflow. Called by the `rss-buddy` entry point.
  - `models.py`: Defines core data structures (e.g., `Article`, `FeedDisplayData`). (Key `Article` fields: `id`, `title`, `link`, `summary`, `published_date`, `processed_date`, `status`)
  - `feed_processor.py`: Fetches feeds, determines status ('processed'/'digest') for new items using `AIInterface`, and instructs `StateManager` to update state.
  - `state_manager.py`: Manages loading, saving, and querying the processing state (`processed_state.json`). (State is stored as nested dictionaries: `feeds -> {feed_url} -> entry_data -> {entry_id} -> {article_details}`)
  - `ai_interface.py`: Handles interactions with the OpenAI API. (Key methods: `evaluate_article_preference`, `generate_consolidated_summary`)
  - `generate_pages.py`: Generates the static HTML site (`docs/`) from the state using Jinja2. (Main function: `generate_pages()`)
  - `templates/`: Contains the Jinja2 HTML templates (`base.html`, `index.html.j2`, `feed.html.j2`).
- `processed_feeds/` - Default directory for storing `processed_state.json`.
- `docs/` - Default output directory for the generated HTML site.
- `pyproject.toml`: Defines project metadata, dependencies, build system, and tool configurations (like Ruff).
- `run_rss_buddy.py`: Legacy command-line runner script (might still be useful for specific parameter passing).
- `run_tests.py`: Test suite runner.
- `rss-buddy.sh`: Convenience shell script for execution using environment variables.
- `lint.py`: Linting script (wraps Ruff commands).

### Running Tests

```bash
python run_tests.py [-v] [--skip-lint] [--lint-only] [--lint-paths PATH1 PATH2...]
```

The test suite includes unit tests covering individual components (state management, AI interface, feed processing, date handling, etc.) and integration tests (`tests/test_integration.py`) verifying the core workflows (State I/O, Feed Processing -> State Update, State -> HTML Generation) using mocked external dependencies (AI, network).

By default, running tests will also run the linter. Use the `--skip-lint` option to skip linting, or `--lint-only` to run only the linter.

### Linting and Formatting

The project uses Ruff for fast linting and code formatting.

Linting and formatting are automatically run when executing tests using `python run_tests.py`, but you can also run them separately using the `lint.py` script:

```bash
python lint.py [--paths PATH1 PATH2...]
```

This script will first format the specified files using `ruff format` and then lint them using `ruff check --fix`.

Alternatively, you can run only the linter via the test script:

```bash
python run_tests.py --lint-only [--lint-paths PATH1 PATH2...]
```

Ruff settings are configured in `pyproject.toml`.

The linter/formatter and tests are automatically run on GitHub via CI workflows (`.github/workflows/tests.yml`).

## GitHub Pages Integration

The GitHub Actions workflow (`.github/workflows/process-rss.yml`) is configured to:

1.  Run `./rss-buddy.sh --pages` on a schedule or manually.
2.  This processes feeds (updating state in `processed_feeds/`) and generates the HTML site (in `docs/`).
3.  Upload the contents of the `docs/` directory as a GitHub Pages artifact.
4.  Deploy the artifact to GitHub Pages.

The generated site will be available at `https://<your-username>.github.io/<repository-name>/` (or similar, depending on your Pages setup).
