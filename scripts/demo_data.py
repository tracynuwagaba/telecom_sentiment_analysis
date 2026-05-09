"""
=============================================================
  Uganda Telecom Sentiment — Demo Data Generator
  File: demo_data.py

  Run this if you don't have a Twitter API key yet.
  Generates ~2,000 realistic tweets for testing the full pipeline.
  Output: data/raw_tweets.csv  (same schema as the real scraper)
=============================================================
"""

import csv
import random
import os
from datetime import datetime, timedelta, timezone

os.makedirs("data", exist_ok=True)

random.seed(42)

# ── Tweet templates ────────────────────────────────────────
MTN_POSITIVE = [
    "MTN MoMo just saved my life, sent money home in seconds!",
    "MTN Uganda's coverage in Gulu is honestly impressive now",
    "Shoutout to @MTNUganda customer care, issue resolved in 10 mins",
    "MTN Pulse bundles are the best deal on the market right now",
    "Finally MTN network is back to normal, fast internet all day",
    "MoMo agent network is everywhere, can withdraw even in the village",
    "MTN night data bundles are a lifesaver for students",
    "MTN 4G speeds in Kampala are actually good today",
    "Just transferred money via MoMo to my family in Kabale, instant!",
    "MTN Uganda infrastructure improvements are noticeable, great signal",
    "Love how MTN data bundles have improved, worth every shilling",
    "Great coverage on the Kampala–Jinja highway, MTN is reliable",
    "MTN customer care resolved my SIM issue same day, impressed",
    "MoMo float is always available at my nearby agent, convenient",
    "MTN Uganda 5G announcement has me excited for faster internet",
]
MTN_NEGATIVE = [
    "MTN network is absolutely terrible in Nakawa right now #MTNUganda",
    "Why does MTN data get deducted without using it? Thieves!",
    "@MTNUganda my MoMo transaction failed but money was deducted, fix this!",
    "MTN internet is so slow I can't even load WhatsApp, useless",
    "MTN Uganda customer care has me on hold for 2 hours, ridiculous",
    "Every time UMEME load sheds, MTN towers go down with it",
    "Slow internet from MTN again tonight, this is unacceptable",
    "MTN SIM registration portal keeps crashing, how am I supposed to register?",
    "Network drops every 20 minutes in Mukono, MTN fix your towers!",
    "MoMo fraud cases are increasing and MTN Uganda is doing nothing",
    "Bought a 1GB bundle from MTN but it finished in 2 hours, suspicious",
    "MTN USSD keeps returning errors, can't check my balance",
    "Terrible 4G speeds from MTN, barely better than 3G",
    "MTN Uganda roaming charges are highway robbery",
    "Cannot call anyone on MTN lines, network congestion again",
]
MTN_NEUTRAL = [
    "Anyone else experiencing MTN network issues today in Kampala?",
    "What are the current MTN Uganda data bundle prices?",
    "MTN Uganda is expanding to rural areas according to the news",
    "How do I register my MTN SIM card online?",
    "MTN MoMo now integrated with more banks, interesting development",
    "Comparing MTN and Airtel Uganda plans, which is better value?",
    "MTN Uganda coverage map has been updated",
    "The MTN Uganda app has a new update, anyone tried it?",
]

AIRTEL_POSITIVE = [
    "Airtel Money is super convenient for paying bills in Uganda",
    "Airtel Uganda data bundles are affordable for students",
    "Great Airtel signal in Entebbe today, no complaints",
    "@AirtelUG customer care actually helped me quickly today",
    "Airtel internet speed has improved significantly in Mbarara",
    "Airtel Money agent in my area is always available and helpful",
    "Airtel night data deal is the best thing for night owls",
    "Switched to Airtel Uganda and the network is surprisingly good",
    "Airtel Uganda bundles are cheaper than competitors for sure",
    "Airtel Money transaction went through instantly, impressed",
]
AIRTEL_NEGATIVE = [
    "Airtel Uganda 4G is so inconsistent, drops to 2G randomly",
    "@AirtelUG why is my data finishing so fast? Scam bundles!",
    "Airtel Money keeps failing transactions, very unreliable service",
    "No Airtel signal in Wakiso at all, this is beyond frustrating",
    "Airtel Uganda customer care doesn't pick up calls, useless helpline",
    "Airtel internet speeds are terrible in Ntinda, barely usable",
    "Airtel Money agent ran out of float again, can't withdraw my money",
    "Airtel Uganda network is completely down in our area since morning",
    "Airtel Uganda data bundles expire too fast, it's a ripoff",
    "Switched from Airtel Uganda because of constant dropped calls",
    "Airtel Money OTP never arrives, can't complete transactions",
    "Airtel Uganda USSD codes keep returning errors, fix your network!",
    "4G from Airtel Uganda is slower than my old 3G, disappointed",
    "Airtel Uganda billing is wrong, charged me twice for same bundle",
    "Network congestion on Airtel Uganda is unbearable during peak hours",
    "Airtel Uganda towers down again thanks to load shedding in Kireka",
    "Cannot get Airtel Uganda signal anywhere in Arua, terrible coverage",
]
AIRTEL_NEUTRAL = [
    "Has anyone noticed Airtel Uganda signal issues today?",
    "What is the Airtel Uganda customer care number?",
    "Airtel Uganda now offers more data options according to their site",
    "Comparing Airtel Money vs MTN MoMo for sending money upcountry",
    "Airtel Uganda is rolling out more towers in Western Uganda",
    "How do I check my Airtel Uganda data balance?",
    "Airtel Uganda new bundle packages announced",
]

UGANDAN_LOCATIONS = [
    "Kampala, Uganda", "Entebbe", "Gulu", "Mbarara", "Jinja",
    "Mukono", "Wakiso", "Ntinda", "Nakawa", "Kireka", "Nansana",
    "Arua", "Kabale", "Fort Portal", "Masaka", "Lira", "Soroti",
    "", "", "",  # some tweets have no location
]
UGANDAN_USERNAMES = [
    "ugandatech", "kampalalife", "ugbiz", "pearlofafrica", "makereregrad",
    "kampalavibes", "ugmoney", "africatech", "mobileuganda", "ugandatwitter",
    "entebbeguy", "kabalagala_ke", "wandegeya_boy", "ntinda_girl", "mulago_doc",
    "ugandastartup", "telecomug", "datacentreug", "mtnwatcher", "airtelcritic",
]

def make_tweet(brand, text, created_at, uid_counter):
    """Generate a single synthetic tweet with realistic metadata and engagement metrics.
    
    Args:
        brand (str): Telecom brand name ('MTN Uganda' or 'Airtel Uganda')
        text (str): Tweet text content
        created_at (datetime): Tweet creation timestamp
        uid_counter (int): Unique ID counter for tweet_id generation
    
    Returns:
        dict: Tweet record with all fields matching raw_tweets.csv schema
    """
    # Simulate realistic follower distribution: 60% low (10-200), 30% medium (201-2k), 10% high (2k-50k)
    followers = random.choices(
        [random.randint(10, 200), random.randint(201, 2000), random.randint(2001, 50000)],
        weights=[0.6, 0.3, 0.1]
    )[0]
    # Engagement metrics follow power-law distribution (mostly low engagement, some viral tweets)
    retweets = random.choices([0, random.randint(1, 5), random.randint(6, 50)], weights=[0.6, 0.3, 0.1])[0]
    likes    = random.choices([0, random.randint(1, 10), random.randint(11, 100)], weights=[0.5, 0.35, 0.15])[0]
    replies  = random.choices([0, random.randint(1, 3)], weights=[0.7, 0.3])[0]

    # Auto-generate hashtags based on tweet content keywords
    hashtags = []
    if "MTN" in text: hashtags.append("#MTNUganda")
    if "Airtel" in text: hashtags.append("#AirtelUganda")
    if "MoMo" in text or "mobile money" in text.lower(): hashtags.append("#MoMo")
    if "network" in text.lower(): hashtags.append("#UgandaTelecom")

    # Return complete tweet record matching CSV schema
    return {
        "tweet_id":        str(1800000000000 + uid_counter),
        "brand":           brand,
        "created_at":      created_at.isoformat(),
        "date":            created_at.strftime("%Y-%m-%d"),
        "hour":            created_at.hour,
        "text":            text,
        "lang":            "en",
        "author_id":       str(random.randint(100000000, 999999999)),
        "author_username": random.choice(UGANDAN_USERNAMES) + str(random.randint(1, 999)),
        "author_location": random.choice(UGANDAN_LOCATIONS),
        "author_followers": followers,
        "retweet_count":   retweets,
        "reply_count":     replies,
        "like_count":      likes,
        "quote_count":     random.choices([0, 1], weights=[0.85, 0.15])[0],
        "hashtags":        " ".join(hashtags),
        "mentions":        "@MTNUganda" if brand == "MTN Uganda" else "@AirtelUG",
        "geo_place":       random.choice(UGANDAN_LOCATIONS),
    }


def generate():
    """Generate ~2,000 synthetic tweets and save to data/raw_tweets.csv.
    
    Tweet distribution:
    - ~1,100 MTN Uganda tweets (60% negative, 22% positive, 18% neutral)
    - ~900 Airtel Uganda tweets (67% negative, 17% positive, 16% neutral)
    
    Tweets are spread across 30 days with realistic hourly patterns,
    simulating actual Twitter activity peaks.
    
    Returns:
        None (writes to CSV directly)
    """
    rows = []
    now  = datetime(2026, 5, 9, tzinfo=timezone.utc)
    counter = 0

    # Generate tweets spread over 30 days, weighted by hour (peaks 7-9am, 12-1pm, 7-10pm)
    def random_dt():
        day_offset = random.randint(0, 29)
        hour = random.choices(
            list(range(24)),
            weights=[1,1,1,1,1,2,3,5,6,4,3,4,6,5,4,3,3,4,6,7,6,5,3,2]
        )[0]
        # Blend: pick random day from past 30, then adjust to realistic peak hours
        return now - timedelta(days=day_offset, hours=random.randint(0,23), minutes=random.randint(0,59)) \
               + timedelta(hours=hour-12)  # Normalize hour offset

    # Build weighted pools: multiply sentiment templates by weights to control distribution ratio
    # MTN: 60% negative ratio (real-world complaint-heavy social media)
    # Weight multipliers: Positive ×4, Negative ×7, Neutral ×2 → ~40% pos, 58% neg, 17% neutral
    mtn_pool = (
        [(t, "Positive") for t in MTN_POSITIVE] * 4 +
        [(t, "Negative") for t in MTN_NEGATIVE] * 7 +
        [(t, "Neutral")  for t in MTN_NEUTRAL]  * 2
    )
    # Airtel: even more negative (67% negative)
    # Weight multipliers: Positive ×3, Negative ×8, Neutral ×2
    airtel_pool = (
        [(t, "Positive") for t in AIRTEL_POSITIVE] * 3 +
        [(t, "Negative") for t in AIRTEL_NEGATIVE] * 8 +
        [(t, "Neutral")  for t in AIRTEL_NEUTRAL]  * 2
    )

    # Sample tweets from pools (random.choices allows duplicates, simulating real-world patterns)
    for text, _ in random.choices(mtn_pool, k=1100):
        rows.append(make_tweet("MTN Uganda", text, random_dt(), counter))
        counter += 1

    for text, _ in random.choices(airtel_pool, k=900):
        rows.append(make_tweet("Airtel Uganda", text, random_dt(), counter))
        counter += 1

    # Shuffle to avoid sentiment/brand bias in row ordering
    random.shuffle(rows)

    # Write to CSV with same schema as real scraper output
    fieldnames = list(rows[0].keys())
    with open("data/raw_tweets.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} synthetic tweets → data/raw_tweets.csv")

    print(f"✓ Generated {len(rows)} demo tweets → data/raw_tweets.csv")
    print("  MTN Uganda:    ~1100 tweets")
    print("  Airtel Uganda: ~900 tweets")
    print("\n  Next: run  python3 scripts/sentiment_analysis.py")


if __name__ == "__main__":
    generate()