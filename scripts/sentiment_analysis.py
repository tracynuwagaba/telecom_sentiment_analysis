"""
=============================================================
  Uganda Telecom Sentiment — Analysis Pipeline
  File: sentiment_analysis.py
 
  Reads:  data/raw_tweets.csv   (from demo_data.py)
  Writes: data/tweets_analysed.csv
          data/uganda_telecom_tweets.xlsx  (multi-sheet)
=============================================================
  Scoring method: VADER (Valence Aware Dictionary and sEntiment Reasoner)
  — Works well for social media text (handles caps, punctuation, slang)
  — compound score:  >= 0.05  → Positive
                     <= -0.05 → Negative
                     else     → Neutral
=============================================================
"""
 
import re
import csv
import logging
import os
from datetime import datetime
 
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── Config ────────────────────────────────────────────────
INPUT_FILE   = "data/raw_tweets.csv"
ANALYSED_CSV = "data/tweets_analysed.csv"
FINAL_OUTPUT_XLSX = "data/uganda_telecom_tweets.xlsx"
LOG_FILE     = "logs/analysis.log"
 
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Topic keyword taxonomy ────────────────────────────────
TOPIC_RULES = {
    "Network & Coverage":    r"\b(network|coverage|signal|tower|offline|outage|down|dropped|4g|5g|3g|roaming)\b",
    "Internet & Data":       r"\b(internet|data|bundle|mb|gb|speed|slow|browsing|wifi|hotspot|unlimited|night data)\b",
    "Mobile Money":          r"\b(momo|mobile money|airtel money|send money|withdraw|deposit|agent|float|transaction|transfer|mm)\b",
    "Customer Care":         r"\b(customer care|support|helpline|complaint|service|agent|respond|useless|fix|resolve|toll.free)\b",
    "Billing & Tariffs":     r"\b(bill|charge|deduct|tariff|price|expensive|cheap|value|subscription|credit|balance|cost)\b",
    "Call Quality":          r"\b(call|voice|drop|echo|noise|busy|line|ring|dial|hear|cannot call)\b",
    "SIM & Registration":    r"\b(sim|registration|nira|register|kyc|activate|block|replace|port|number)\b",
    "Promotions & Offers":   r"\b(promo|offer|deal|bonus|free|discount|pulse|bundle|flash|reward|loyalty)\b",
    "Infrastructure":        r"\b(tower|fiber|cable|load.?shed|umeme|power|electricity|infrastructure|expand)\b",
    "App & USSD":            r"\b(app|ussd|mymtn|myairtel|\*100|\*185|code|download|update|crash|login)\b",
    "Fraud & Security":      r"\b(fraud|scam|hack|phish|otp|verify|fake|steal|unauthori[sz]ed|suspicious)\b",
}

# Telecom-specific sentiment boosters (VADER may under-score these)
CUSTOM_LEXICON_BOOSTS = {
    # negative telecom slang
    "no network": -1.5,
    "network issues": -1.2,
    "data deducted": -1.4,
    "stolen data": -1.8,
    "momo fraud": -2.0,
    "airtel money failed": -1.6,
    "customer care useless": -1.8,
    "terrible service": -1.6,
    "load shedding": -0.8,
    # positive telecom
    "good network": 1.4,
    "fast internet": 1.3,
    "love momo": 1.5,
    "best network": 1.6,
    "easy transfer": 1.2,
    "reliable": 1.0,
}

def clean_text(text: str) -> str:
    """Light cleaning — keep slang/caps for VADER, remove URLs and @."""
    text = re.sub(r"http\S+|www\.\S+", "", text)          # remove URLs
    text = re.sub(r"@\w+", "", text)                       # remove @mentions
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_topics(text: str) -> str:
    """Identify telecom-related topics referenced in a tweet.

    Matches the lowercased text against predefined topic regex rules.
    Returns a semicolon-separated label list or "General" when no topics match.
    """
    text_lower = text.lower()
    matched = [topic for topic, pattern in TOPIC_RULES.items()
               if re.search(pattern, text_lower)]
    return "; ".join(matched) if matched else "General"

def apply_custom_boosts(text: str, base_score: float) -> float:
    """Adjust the VADER compound score for telecom-specific keyword sentiment.

    This compensates for domain-specific phrases that VADER may under-score.
    The adjustments are scaled down so they modify but do not override the base score.
    """
    text_lower = text.lower()
    boost = 0.0
    for phrase, val in CUSTOM_LEXICON_BOOSTS.items():
        if phrase in text_lower:
            boost += val * 0.1   # scale so we don't override VADER completely
    boosted = base_score + boost
    return max(-1.0, min(1.0, boosted))  # clamp to [-1, 1]

def classify_sentiment(compound: float) -> str:
    """Convert a VADER compound score into a sentiment category.

    Uses standard VADER thresholds:
      - compound >= 0.05 => Positive
      - compound <= -0.05 => Negative
      - otherwise => Neutral
    """
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    return "Neutral"

def sentiment_strength(compound: float) -> str:
    """More granular label for Tableau drill-down."""
    if compound >= 0.5:   return "Strongly Positive"
    if compound >= 0.05:  return "Mildly Positive"
    if compound <= -0.5:  return "Strongly Negative"
    if compound <= -0.05: return "Mildly Negative"
    return "Neutral"

def analyse():
    """Main sentiment analysis pipeline.
    
    Steps:
    1. Load raw tweets from CSV
    2. Clean text and compute VADER sentiment scores
    3. Apply domain-specific sentiment adjustments for telecom terms
    4. Classify into Positive/Negative/Neutral and assign strength labels
    5. Extract topics using regex keyword taxonomy
    6. Enrich with temporal and engagement features
    7. Write analyzed tweets to CSV
    8. Build multi-sheet Excel workbook for Tableau visualization
    
    Output files:
    - data/tweets_analysed.csv: Complete record per tweet
    - data/uganda_telecom_tweets.xlsx: 8-sheet workbook with aggregations
    """
    # ─── STEP 1: LOAD RAW TWEETS ───────────────────────
    if not os.path.exists(INPUT_FILE):
        log.error(f"{INPUT_FILE} not found. Run demo_data.py first.")
        return
 
    # Load with string dtype to preserve leading zeros and tweet IDs
    df = pd.read_csv(INPUT_FILE, dtype=str)
    log.info(f"Loaded {len(df)} raw tweets.")
 
    # ─── STEP 2: SENTIMENT SCORING ──────────────────────
    # VADER (Valence Aware Dictionary and sEntiment Reasoner) is optimized for social media
    # Handles contractions, emoji, caps, punctuation that other lexicons miss
    analyser = SentimentIntensityAnalyzer()
 
    records = []
    for _, row in df.iterrows():
        # Extract and clean tweet text
        raw_text   = str(row.get("text", ""))
        clean      = clean_text(raw_text)  # Remove URLs, @mentions but keep slang/caps for VADER

        # Compute VADER scores, then boost with telecom domain lexicon
        # VADER returns: pos, neg, neu (proportions), compound (normalized -1 to 1)
        scores     = analyser.polarity_scores(clean)
        compound   = apply_custom_boosts(clean, scores["compound"])  # Fine-tune for telecom terms
        sentiment  = classify_sentiment(compound)  # Map to Positive/Negative/Neutral
        strength   = sentiment_strength(compound)  # Map to Strongly/Mildly/Neutral
        topics     = get_topics(clean)  # Extract topic categories via regex
 
        # Extract date fields; convert ISO timestamp to temporal features for Tableau
        created_at = row.get("created_at", "")
        date_str   = row.get("date", "")
        hour       = row.get("hour", "")
 
        # Compute week number, month-year label, and day-of-week for time-series analysis
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))  # Parse ISO 8601
            week_num   = dt.isocalendar()[1]  # ISO week number (1-53)
            month_name = dt.strftime("%B %Y")  # e.g., "May 2026"
            day_of_week = dt.strftime("%A")    # e.g., "Monday"
        except Exception:
            # Handle missing/malformed timestamps gracefully
            week_num   = ""
            month_name = ""
            day_of_week = ""
 
        # Build complete record with original fields + enriched sentiment/temporal/topic data
        records.append({
            # Original fields from raw CSV
            "tweet_id":          row.get("tweet_id", ""),
            "brand":             row.get("brand", ""),
            "created_at":        created_at,
            "date":              date_str,
            "hour":              hour,
            "day_of_week":       day_of_week,
            "week_number":       week_num,
            "month_year":        month_name,
            "text_original":     raw_text,
            "text_clean":        clean,
            "lang":              row.get("lang", ""),
            "author_username":   row.get("author_username", ""),
            "author_location":   row.get("author_location", ""),
            "author_followers":  row.get("author_followers", 0),
            "retweet_count":     row.get("retweet_count", 0),
            "reply_count":       row.get("reply_count", 0),
            "like_count":        row.get("like_count", 0),
            "quote_count":       row.get("quote_count", 0),
            "hashtags":          row.get("hashtags", ""),
            "mentions":          row.get("mentions", ""),
            "geo_place":         row.get("geo_place", ""),
            # Sentiment scores: VADER component scores + final compound
            "vader_pos":         round(scores["pos"], 4),      # Proportion of positive sentiment
            "vader_neg":         round(scores["neg"], 4),      # Proportion of negative sentiment
            "vader_neu":         round(scores["neu"], 4),      # Proportion of neutral words
            "vader_compound":    round(scores["compound"], 4), # Original VADER compound
            "compound_adjusted": round(compound, 4),           # Adjusted with telecom boosts
            "sentiment":         sentiment,                    # Category: Positive/Negative/Neutral
            "sentiment_strength":strength,                    # Granular: Strongly/Mildly Positive/Negative/Neutral
            "topics":            topics,                       # Semicolon-separated topic list
            # Engagement score: weighted sum for Tableau KPI calculations
            # Retweets (3x) and replies (2x) weight heavier than likes, showing amplification
            "engagement_score":  (
                int(row.get("retweet_count", 0) or 0) * 3 +
                int(row.get("like_count", 0) or 0) +
                int(row.get("reply_count", 0) or 0) * 2 +
                int(row.get("quote_count", 0) or 0) * 2
            ),
        })
 
    # ─── STEP 3: SAVE ANALYZED TWEETS ───────────────────
    df_out = pd.DataFrame(records)
    df_out.to_csv(ANALYSED_CSV, index=False, encoding="utf-8")
    log.info(f"✓ Saved analysed CSV → {ANALYSED_CSV}")
 
    # ─── STEP 4: BUILD TABLEAU WORKBOOK ─────────────────
    # Create multi-sheet Excel with aggregated views for dashboard
    build_final_workbook(df_out)

def build_final_workbook(df: pd.DataFrame):
    """Create a multi-sheet Excel workbook optimised for Tableau.

    Each worksheet contains a clean, flat table derived from the analysed
    data, ready for use as a standalone data source or in relationships.
    """
    log.info("Building final workbook...")
 
    with pd.ExcelWriter(FINAL_OUTPUT_XLSX, engine="xlsxwriter") as writer:
        wb = writer.book
 
        # ─── Excel Formatting ───────────────────────────
        # Header format: dark background, white text, centered, wrapped
        hdr_fmt = wb.add_format({
            "bold": True, "bg_color": "#1F2D3D", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
        })
        # Brand and sentiment color schemes for visual distinction in Tableau
        mtn_fmt    = wb.add_format({"bg_color": "#FFF3CD"})      # MTN: yellow
        airtel_fmt = wb.add_format({"bg_color": "#FDECEA"})      # Airtel: light red
        pos_fmt    = wb.add_format({"bg_color": "#D4EDDA", "font_color": "#155724"})  # Positive: green
        neg_fmt    = wb.add_format({"bg_color": "#F8D7DA", "font_color": "#721C24"})  # Negative: red
        neu_fmt    = wb.add_format({"bg_color": "#E2E3E5", "font_color": "#383D41"})  # Neutral: gray
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 1 — MAIN: Complete dataset with all columns
        # Use: Ad-hoc analysis, drill-down in Tableau, data validation
        # ═════════════════════════════════════════════════════════════════════════════
        sheet_cols = [
            "tweet_id","brand","date","hour","day_of_week","week_number","month_year",
            "text_clean","lang","author_username","author_location","author_followers",
            "retweet_count","reply_count","like_count","quote_count",
            "vader_compound","compound_adjusted","sentiment","sentiment_strength",
            "topics","engagement_score","hashtags","geo_place",
        ]
        df_master = df[sheet_cols].copy()
        df_master.to_excel(writer, sheet_name="Main", index=False)
        ws = writer.sheets["Main"]
        ws.set_row(0, 30, hdr_fmt)  # Header row height
        # Set column widths for readability
        ws.set_column("A:A", 18)  # tweet_id
        ws.set_column("B:B", 16)  # brand
        ws.set_column("C:C", 12)  # date
        ws.set_column("H:H", 50)  # text (wide for content)
        ws.set_column("S:S", 14)  # sentiment
        ws.set_column("U:U", 35)  # topics (wide)
        ws.freeze_panes(1, 0)      # Freeze header row
        log.info(f"  Sheet Main: {len(df_master)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 2 — DAILY TRENDS: Sentiment distribution by day and brand
        # Tableau visualization: Line/area chart for sentiment evolution
        # KPIs: pct_positive, pct_negative, net_sentiment (positive - negative)
        # ═════════════════════════════════════════════════════════════════════════════
        # Count tweets by sentiment per brand per day
        df_daily = (
            df.groupby(["brand", "date", "sentiment"])
              .agg(tweet_count=("tweet_id", "count"), avg_compound=("compound_adjusted", "mean"))
              .reset_index()
        )
        # Pivot to get sentiment counts as separate columns for percentage calculation
        pivot = df.groupby(["brand", "date", "sentiment"])["tweet_id"].count().unstack(fill_value=0).reset_index()
        # Ensure all sentiment columns exist even if count is 0
        for col in ["Positive", "Negative", "Neutral"]:
            if col not in pivot.columns:
                pivot[col] = 0
        # Calculate percentages and net sentiment score
        pivot["total"]         = pivot["Positive"] + pivot["Negative"] + pivot["Neutral"]
        pivot["pct_positive"]  = (pivot["Positive"] / pivot["total"] * 100).round(1)  # KPI
        pivot["pct_negative"]  = (pivot["Negative"] / pivot["total"] * 100).round(1)  # KPI
        pivot["net_sentiment"]  = pivot["pct_positive"] - pivot["pct_negative"]      # KPI
 
        pivot.to_excel(writer, sheet_name="Daily_Trends", index=False)
        ws2 = writer.sheets["Daily_Trends"]
        ws2.set_row(0, 28, hdr_fmt)
        ws2.set_column("A:B", 16)  # Brand and date columns
        ws2.freeze_panes(1, 0)     # Freeze header
        log.info(f"  Sheet Daily_Trends: {len(pivot)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 3 — TOPICS: Sentiment breakdown by topic category
        # Tableau visualization: Bar chart (topics by sentiment per brand)
        # Use for: Issue tracking, prioritizing improvement areas
        # ═════════════════════════════════════════════════════════════════════════════
        # Explode each tweet's semicolon-separated topics into individual rows for aggregation
        topic_rows = []
        for _, row in df.iterrows():
            for topic in str(row["topics"]).split(";"):
                topic = topic.strip()
                if topic:  # Skip empty strings
                    topic_rows.append({
                        "brand":      row["brand"],
                        "topic":      topic,
                        "sentiment":  row["sentiment"],
                        "compound":   row["compound_adjusted"],
                        "engagement": row["engagement_score"],
                        "date":       row["date"],
                    })
        df_topics = pd.DataFrame(topic_rows)
        # Aggregate: count tweets, average sentiment, and total engagement per topic/brand/sentiment combo
        topic_summary = (
            df_topics.groupby(["brand", "topic", "sentiment"])
                     .agg(tweet_count=("compound", "count"),            # Volume
                          avg_compound=("compound", "mean"),            # Average severity
                          total_engagement=("engagement", "sum"))       # Impact
                     .reset_index()
                     .sort_values(["brand", "tweet_count"], ascending=[True, False])  # Sort by brand, then volume
        )
        topic_summary.to_excel(writer, sheet_name="Topics", index=False)
        ws3 = writer.sheets["Topics"]
        ws3.set_row(0, 28, hdr_fmt)
        ws3.set_column("B:B", 24)  # Topic column (wide)
        ws3.freeze_panes(1, 0)     # Freeze header
        log.info(f"  Sheet Topics: {len(topic_summary)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 4 — MOBILE MONEY: Service-specific sentiment for MoMo vs Airtel Money
        # Tableau visualization: Time series comparison (MTN MoMo vs Airtel Money)
        # Use for: Service quality benchmarking, tracking mobile money NPS
        # ═════════════════════════════════════════════════════════════════════════════
        # Filter to Mobile Money topic tweets only
        df_momo = df[df["topics"].str.contains("Mobile Money", na=False)].copy()
        # Map brand to service name for clearer visualization
        df_momo["momo_service"] = df_momo["brand"].map({
            "MTN Uganda":    "MTN MoMo",
            "Airtel Uganda": "Airtel Money",
        })
        # Aggregate by service, date, and sentiment
        momo_summary = (
            df_momo.groupby(["momo_service", "date", "sentiment"])
                   .agg(tweet_count=("tweet_id", "count"),              # Volume of mentions
                        avg_compound=("compound_adjusted", "mean"),     # Average sentiment
                        total_engagement=("engagement_score", "sum"))   # Community engagement
                   .reset_index()
        )
        momo_summary.to_excel(writer, sheet_name="MobileMoney", index=False)
        ws4 = writer.sheets["MobileMoney"]
        ws4.set_row(0, 28, hdr_fmt)
        ws4.freeze_panes(1, 0)  # Freeze header row for easy scrolling
        log.info(f"  Sheet MobileMoney: {len(momo_summary)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 5 — INTERNET & DATA: Sentiment for data/connectivity issues and speeds
        # Tableau visualization: KPI cards + trend lines (MTN vs Airtel)
        # Use for: Data quality benchmarking, identifying service outages
        # ═════════════════════════════════════════════════════════════════════════════
        # Filter tweets mentioning Internet & Data topics
        df_net = df[df["topics"].str.contains("Internet & Data", na=False)].copy()
        # Aggregate by brand, date, and sentiment for time-series analysis
        net_summary = (
            df_net.groupby(["brand", "date", "sentiment"])
                  .agg(tweet_count=("tweet_id", "count"),              # Volume
                       avg_compound=("compound_adjusted", "mean"))     # Avg sentiment strength
                  .reset_index()
        )
        net_summary.to_excel(writer, sheet_name="Internet", index=False)
        ws5 = writer.sheets["Internet"]
        ws5.set_row(0, 28, hdr_fmt)
        ws5.freeze_panes(1, 0)  # Freeze header row
        log.info(f"  Sheet Internet: {len(net_summary)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 6 — HOURLY HEATMAP: Sentiment activity by day of week and hour
        # Tableau visualization: Highlight table (hour × day_of_week heatmap)
        # Use for: Identifying peak issue hours, staffing call centers appropriately
        # ═════════════════════════════════════════════════════════════════════════════
        # Convert hour to numeric, handling missing/invalid values
        df["hour_int"] = pd.to_numeric(df["hour"], errors="coerce").fillna(0).astype(int)
        # Group by hour and day_of_week to find when issues are most discussed
        hourly = (
            df.groupby(["brand", "day_of_week", "hour_int", "sentiment"])
              .agg(tweet_count=("tweet_id", "count"))  # Count tweets per bucket
              .reset_index()
        )
        # Enforce proper day ordering (Mon-Sun) instead of alphabetical
        day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        hourly["day_of_week"] = pd.Categorical(hourly["day_of_week"], categories=day_order, ordered=True)
        hourly = hourly.sort_values(["brand","day_of_week","hour_int"])  # Sort for proper display
        hourly.to_excel(writer, sheet_name="Weekday_Hour", index=False)
        ws6 = writer.sheets["Weekday_Hour"]
        ws6.set_row(0, 28, hdr_fmt)
        ws6.freeze_panes(1, 0)  # Freeze header for readability
        log.info(f"  Sheet Weekday_Hour: {len(hourly)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 7 — TOP COMPLAINTS: Issues sorted by complaint frequency and severity
        # Tableau visualization: Horizontal bar chart (top complaints by brand)
        # Use for: Prioritizing customer service improvements, targeting root causes
        # ═════════════════════════════════════════════════════════════════════════════
        # Extract only negative sentiment tweets
        df_neg = df[df["sentiment"] == "Negative"].copy()
        # Explode complaints into individual rows (one row per topic per complaint tweet)
        complaint_rows = []
        for _, row in df_neg.iterrows():
            for topic in str(row["topics"]).split(";"):
                topic = topic.strip()
                if topic:  # Skip empty/None topics
                    complaint_rows.append({
                        "brand":      row["brand"],
                        "topic":      topic,
                        "date":       row["date"],
                        "compound":   row["compound_adjusted"],  # Severity score
                        "engagement": row["engagement_score"],    # How much this complaint spread
                    })
        # Build DataFrame safely (handle case where no complaints exist)
        df_complaints = pd.DataFrame(complaint_rows) if complaint_rows else pd.DataFrame(
            columns=["brand","topic","date","compound","engagement"]
        )
        # Aggregate: count complaints, calculate avg severity, and total reach per topic
        complaints_summary = (
            df_complaints.groupby(["brand","topic"])
                         .agg(complaint_count=("compound","count"),        # Frequency
                              avg_severity=("compound","mean"),           # Avg negativity strength
                              total_engagement=("engagement","sum"))      # Total reach/spread
                         .reset_index()
                         .sort_values("complaint_count", ascending=False)  # Most common first
        )
        complaints_summary.to_excel(writer, sheet_name="Complaints", index=False)
        ws7 = writer.sheets["Complaints"]
        ws7.set_row(0, 28, hdr_fmt)
        ws7.set_column("B:B", 24)  # Topic column (wide)
        ws7.freeze_panes(1, 0)     # Freeze header for scrolling
        log.info(f"  Sheet Complaints: {len(complaints_summary)} rows")
 
        # ═════════════════════════════════════════════════════════════════════════════
        # SHEET 8 — KPI SUMMARY: Executive dashboard metrics by brand
        # Tableau visualization: KPI cards, gauge charts, trend indicators
        # Use for: Executive reporting, brand comparison, trend monitoring
        # ═════════════════════════════════════════════════════════════════════════════
        kpi_rows = []
        # Compute aggregated metrics per brand
        for brand in df["brand"].unique():
            bdf = df[df["brand"] == brand]  # Filter to brand
            total = len(bdf)
            if total == 0:
                continue
            # Count sentiment distribution
            pos = len(bdf[bdf["sentiment"] == "Positive"])
            neg = len(bdf[bdf["sentiment"] == "Negative"])
            neu = len(bdf[bdf["sentiment"] == "Neutral"])
            kpi_rows.append({
                "brand":               brand,
                # Volume metrics
                "total_tweets":        total,
                "positive_count":      pos,
                "negative_count":      neg,
                "neutral_count":       neu,
                # Percentage breakdowns
                "pct_positive":        round(pos / total * 100, 1),
                "pct_negative":        round(neg / total * 100, 1),
                "pct_neutral":         round(neu / total * 100, 1),
                # Sentiment strength metrics
                "avg_compound":        round(bdf["compound_adjusted"].mean(), 4),  # Avg sentiment
                "net_sentiment_score": round((pos - neg) / total * 100, 1),        # Net KPI
                # Engagement metrics (reach/virality)
                "total_engagement":    int(bdf["engagement_score"].sum()),
                "avg_engagement":      round(bdf["engagement_score"].mean(), 1),
                "unique_authors":      bdf["author_username"].nunique(),           # Reach
                # Service-specific metrics
                "momo_pct_positive":   round(
                    len(bdf[(bdf["topics"].str.contains("Mobile Money", na=False)) & (bdf["sentiment"]=="Positive")]) /
                    max(len(bdf[bdf["topics"].str.contains("Mobile Money", na=False)]), 1) * 100, 1
                ),
                "internet_pct_positive": round(
                    len(bdf[(bdf["topics"].str.contains("Internet & Data", na=False)) & (bdf["sentiment"]=="Positive")]) /
                    max(len(bdf[bdf["topics"].str.contains("Internet & Data", na=False)]), 1) * 100, 1
                ),
            })
        pd.DataFrame(kpi_rows).to_excel(writer, sheet_name="KPI_Summary", index=False)
        ws8 = writer.sheets["KPI_Summary"]
        ws8.set_row(0, 28, hdr_fmt)
        ws8.set_column("A:A", 16)  # Brand column
        ws8.freeze_panes(1, 0)     # Freeze header
        log.info(f"  Sheet KPI_Summary: {len(kpi_rows)} rows")
 
    log.info(f"\n✓ Tableau workbook saved → {FINAL_OUTPUT_XLSX}")
    log.info("  Connect Tableau to each sheet as a separate data source.")
    log.info("\n=== Analysis Complete ===")
    log.info("  Output files:")
    log.info(f"    • {ANALYSED_CSV} (all tweets with sentiment)")
    log.info(f"    • {FINAL_OUTPUT_XLSX} (8 sheets for Tableau)")
    log.info("  Next: Open Excel file and create Tableau dashboards.")


if __name__ == "__main__":
    # Main execution entry point
    analyse()