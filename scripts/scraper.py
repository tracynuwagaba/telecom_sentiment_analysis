"""
Twitter/X Scraper for Uganda Telecom Sentiment Analysis

This module scrapes recent tweets related to MTN Uganda and Airtel Uganda
using the Twitter API v2. It collects tweet data including text, metadata,
and engagement metrics, then saves the results to a CSV file for sentiment analysis.

Requirements:
- Twitter/X API v2 Bearer Token (Free or Basic tier)
- Python packages: tweepy, requests (via tweepy)

Setup:
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create a Project + App -> copy your Bearer Token
3. Set environment variable: export TWITTER_BEARER_TOKEN="your_token_here"

Usage:
    python scraper.py

Output:
- Raw tweet data saved to data/raw_tweets.csv
- Logs saved to logs/scraper.log
"""

import os
import csv
import time
import json
import logging
from datetime import datetime, timedelta, timezone
import tweepy

# Configuration settings
BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")  # Twitter API Bearer Token from environment

OUTPUT_FILE = "data/raw_tweets.csv"  # Output CSV file path
LOG_FILE    = "logs/scraper.log"     # Log file path

# Search queries for different telecom brands
SEARCH_QUERIES = [
    # MTN Uganda related tweets
    '("MTN Uganda" OR "@MTNUganda" OR "#MTNUganda" OR "MTN MoMo" OR "MTNMoMo Uganda") lang:en -is:retweet',

    # Airtel Uganda related tweets
    '("Airtel Uganda" OR "@AirtelUG" OR "#AirtelUganda" OR "Airtel Money Uganda") lang:en -is:retweet'
]

# API limits and parameters
MAX_RESULTS_PER_QUERY = 100  # Max tweets per API request (10-100, depends on tier)
MAX_PAGES_PER_QUERY   = 10   # Max pages to fetch per query
DAYS_BACK             = 7    # Days of historical data to scrape (tier dependent)

# Ensure output directories exist
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger(__name__)

# Twitter API fields to request in the search
TWEET_FIELDS = [
    "id", "text", "created_at", "author_id", "public_metrics",
    "lang", "geo", "context_annotations", "entities"
]
USER_FIELDS = ["username", "name", "location", "public_metrics"]
EXPANSIONS = ["author_id", "geo.place_id"]  # Expand user and place data
PLACE_FIELDS = ["full_name", "country", "country_code", "place_type"]


def scrape_all():
    """
    Main scraping function that collects tweets for all configured search queries.

    This function:
    - Validates the Bearer Token
    - Initializes the Tweepy client
    - Searches for tweets using each query in SEARCH_QUERIES
    - Processes and deduplicates tweet data
    - Saves results to CSV file

    Returns:
        None

    Raises:
        SystemExit: If no Bearer Token is provided
    """
    if not BEARER_TOKEN:
        log.error("No Bearer Token set. Run: export TWITTER_BEARER_TOKEN='your_token'")
        return
    
    client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)
    log.info("Tweepy client initialized.")

    all_rows = []  # List to store all tweet data
    seen_ids = set()  # Set to deduplicate tweets across queries

    # Calculate start time for historical data (current time minus DAYS_BACK days)
    # Start from midnight UTC today
    from_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Tweepy requires start_time in UTC; API tier determines max historical depth
    import datetime as dt
    start_time = from_date - dt.timedelta(days=DAYS_BACK)

    for query in SEARCH_QUERIES:
        log.info(f"Searching: {query[:80]}...")
        pages_fetched = 0

        # Determine brand tag from query string
        brand = "MTN Uganda" if "MTN Uganda" in query or "@MTNUganda" in query else "AirtelUganda"

        try:
            # Create paginator to handle pagination automatically (max MAX_PAGES_PER_QUERY pages)
            paginator = tweepy.Paginator(
                client.search_recent_tweets,
                query=query,
                tweet_fields=TWEET_FIELDS,
                user_fields=USER_FIELDS,
                expansions=EXPANSIONS,
                place_fields=PLACE_FIELDS,
                start_time=start_time,
                max_results=MAX_RESULTS_PER_QUERY
            )

            for response in paginator:
                if response.data is None:
                    break

                # Build user lookup from includes (expanded author metadata like followers)
                users = {}
                if response.includes and "users" in response.includes:
                    for u in response.includes["users"]:
                        users[u.id] = u

                # Build places lookup from includes (expanded geographic place data)
                places = {}
                if response.includes and "places" in response.includes:
                    for p in response.includes["places"]:
                        places[p.id] = p
                
                # Process each tweet from this page's response
                for tweet in response.data:
                    if tweet.id in seen_ids:
                        continue  # Skip duplicate tweets
                    seen_ids.add(tweet.id)

                    # Extract author information from expanded user data via lookup
                    author = users.get(tweet.author_id)
                    author_username = author.username if author else ""
                    author_location = author.location if author else ""
                    author_followers = author.public_metrics["followers_count"] if author and author.public_metrics else 0

                    # Extract engagement metrics (likes, retweets, replies, quotes)
                    metrics = tweet.public_metrics or {}

                    # Resolve geo location from place ID if available
                    geo_place = ""
                    if tweet.geo and tweet.geo.get("place_id"):
                        place = places.get(tweet.geo["place_id"])
                        if place:
                            geo_place = place.full_name

                    # Parse hashtags from tweet entities (structured data)
                    hashtags = ""
                    if tweet.entities and tweet.entities.get("hashtags"):
                        hashtags = " ".join([f"#{h['tag']}" for h in tweet.entities["hashtags"]])
                    
                    # Parse @mentions from tweet entities
                    mentions = ""
                    if tweet.entities and tweet.entities.get("mentions"):
                        mentions = " ".join([f"@{m['username']}" for m in tweet.entities["mentions"]])
                    
                    # Build complete tweet record matching raw_tweets.csv schema
                    all_rows.append({
                        "tweet_id": str(tweet.id),
                        "brand": brand,
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                        "date": tweet.created_at.strftime("%Y-%m-%d") if tweet.created_at else "",
                        "hour": tweet.created_at.hour if tweet.created_at else "",
                        "text": tweet.text.replace("\n", " ").replace("\r", " "),
                        "lang": tweet.lang or "",
                        "author_id": str(tweet.author_id),
                        "author_username": author_username,
                        "author_location": author_location,
                        "author_followers": author_followers,
                        "retweet_count": metrics.get("retweet_count", 0),
                        "reply_count": metrics.get("reply_count", 0),
                        "like_count": metrics.get("like_count", 0),
                        "quote_count": metrics.get("quote_count", 0),
                        "hashtags": hashtags,
                        "mentions": mentions,
                        "geo_place": geo_place
                    })

                # Update page counter and log progress
                pages_fetched += 1
                log.info(f" Page {pages_fetched}: {len(response.data)} tweets (total so far: {len(all_rows)})")

                # Check if we've reached the max pages for this query
                if pages_fetched >= MAX_PAGES_PER_QUERY:
                    log.info(" Max pages reached for this query.")
                    break

                time.sleep(1)  # Be polite to the API

        except tweepy.TooManyRequests:
            # API rate limit exceeded; Tweepy handles auto-wait if wait_on_rate_limit=True
            log.warning("Rate limit hit - Tweepy will auto-wait on next call.")

        except tweepy.Forbidden as e:
            # 403 error typically means Bearer Token is invalid or tier doesn't support this endpoint
            log.error(f"403 Forbidden - check your API access tier. {e}")
            break

        except Exception as e:
            # Catch other API errors (network issues, malformed responses, etc.)
            log.error(f"Error on query: {e}")

    # Write all collected tweets to CSV with schema matching field order
    if all_rows:
        fieldnames = list(all_rows[0].keys())
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        log.info(f"\n✓ Saved {len(all_rows)} tweets -> {OUTPUT_FILE}")
    else:
        # No data collected; likely API key or network issue
        log.warning("No tweets collected. Check your token and query parameters.")


if __name__ == "__main__":
    # Run the scraper when script is executed directly
    scrape_all()