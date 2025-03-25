"""
Configuration file for RSS Buddy
"""

# Example RSS feeds from popular tech and news sites
# Replace these with your preferred feeds
RSS_FEEDS = [
    # Tech News
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",  # NYT Technology
    "https://www.wired.com/feed/rss",  # Wired
    "https://feeds.arstechnica.com/arstechnica/index",  # Ars Technica
    "https://www.theverge.com/rss/index.xml",  # The Verge
    
    # Science News
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",  # NYT Science
    "https://feeds.nature.com/nature/rss/current",  # Nature
    
    # General News
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",  # NYT Home Page
]

# Preference criteria for OpenAI to consider
# This is used to customize the system prompt for preference determination
USER_PREFERENCE_CRITERIA = """
When determining if an article should be shown in full or summarized, consider these factors:
- Technical deep dives in machine learning, AI, and quantum computing should be shown in FULL
- Breaking news about major tech companies should be shown in FULL
- General technology news can be SUMMARIZED
- Scientific breakthroughs should be shown in FULL
- Political news should be SUMMARIZED unless it relates directly to technology policy
- Entertainment news should be SUMMARIZED
"""

# Number of days to look back for articles
DAYS_LOOKBACK = 7

# OpenAI model to use
AI_MODEL = "gpt-4"

# Maximum token length for summaries
SUMMARY_MAX_TOKENS = 150 