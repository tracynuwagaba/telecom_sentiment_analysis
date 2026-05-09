# MTN Uganda vs Airtel Uganda — Twitter Sentiment Analysis
## End-to-End Python → Tableau Pipeline

---

## QUICK START

### Option A — With a Twitter/X API Key (real data)
```bash
# 1. Install dependencies
pip install tweepy vaderSentiment pandas xlsxwriter openpyxl

# 2. Set your Bearer Token
export TWITTER_BEARER_TOKEN="your_token_here"

# 3. Scrape tweets (takes 5–15 mins depending on volume)
python3 scripts/scraper.py

# 4. Run sentiment analysis + build final excel file
python3 scripts/sentiment_analysis.py
```

### Option B — No API Key (demo data, instant)
```bash
# 1. Install dependencies
pip install vaderSentiment pandas xlsxwriter openpyxl

# 2. Generate 2,000 realistic demo tweets
python3 scripts/demo_data.py

# 3. Run sentiment analysis + build Tableau file
python3 scripts/sentiment_analysis.py
```

Then open **data/uganda_telecom_tweets.xlsx** in Tableau.

---

## TWITTER API TIERS

| Tier | Cost | Tweets/month | History | Best for |
|------|------|-------------|---------|----------|
| Free | $0 | 1,500 reads | 7 days | Testing |
| Basic | $100/mo | 10,000 reads | 7 days | Prototype |
| Pro | $5,000/mo | 1M reads | Full archive | Enterprise |

Get your key: https://developer.twitter.com/en/portal/dashboard

---

## OUTPUT FILES

| File | Description | Use in Tableau |
|------|-------------|----------------|
| `data/raw_tweets.csv` | Raw scraped tweets | Source data |
| `data/tweets_analysed.csv` | Tweets + VADER scores + topics | Backup/Python viz |
| `data/uganda_telecom_tweets.xlsx` | 8-sheet workbook | **Primary Tableau input** |

## FINAL SHEETS

| Sheet | Content | Recommended chart |
|-------|---------|------------------|
| Main | All 2000 tweets + scores | Filtered lists |
| Daily_Trends | Daily sentiment % per brand | Line chart |
| Topics | Topic × brand × sentiment | Heatmap + bar |
| MobileMoney | MoMo vs Airtel Money | Stacked bar |
| Internet | Internet tweet sentiment | KPI + scatter |
| Weekday_Hour | Tweet volume by hour/day | Highlight table |
| Complaints | Negative topics ranked | Bar chart |
| KPI_Summary | Overall KPI metrics | Big number tiles |

---

## ARCHITECTURE

```
Twitter/X API v2
      │
      ▼
scraper.py          ← Tweepy client, pagination, deduplication
      │
      ▼  raw_tweets.csv
      │
      ▼
sentiment_analysis.py
      ├─ Text cleaning
      ├─ VADER sentiment scoring
      ├─ Custom telecom lexicon boosts
      ├─ Topic classification (11 categories)
      └─ Engagement scoring
      │
      ▼  uganda_telecom_tweets.xlsx (8 sheets)
      │
      ▼
Tableau Desktop / Public
      └─ dashboard
```

---

## TOPIC CATEGORIES

The pipeline classifies each tweet into one or more of:

- Network & Coverage
- Internet & Data
- Mobile Money
- Customer Care
- Billing & Tariffs
- Call Quality
- SIM & Registration
- Promotions & Offers
- Infrastructure
- App & USSD
- Fraud & Security