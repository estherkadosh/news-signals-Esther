# 1- nasdaq_scraper.py
"""
nasdaq_scraper.py
fetches recent 2026 news (title + date + publisher) for the s&p 500 from nasdaq's
internal news api, saving each ticker to its own jsonl. resumable: done tickers skipped.
"""

import requests
import json
import os
import sys
import time
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # make src/ importable
from sp500 import get_tickers

# 1- config
HEADERS = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}  # nasdaq api needs a browser-like UA
OUT_DIR = "raw_data/nasdaq_news"  # output folder
RATE = 1.0  # 1 sec between tickers - be gentle

# 2- fetch news rows
def get_news(ticker):
    """
    1-calls nasdaq's internal article-by-symbol api.
    2-returns the rows list (or empty if none).
    """
    url = f"https://api.nasdaq.com/api/news/topic/articlebysymbol?q={ticker}|stocks&offset=0&limit=20"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return (data.get("data") or {}).get("rows") or []

# 3- normalize date
def parse_date(created):
    """
    1-nasdaq gives a date like 'Jun 8, 2026'.
    2-returns iso (yyyy-mm-dd), or none.
    """
    try:
        return datetime.strptime(created.strip(), "%b %d, %Y").date().isoformat()
    except Exception:
        return None

# 4- save one ticker
def save_news(ticker):
    """
    1-fetches the ticker news rows from nasdaq.
    2-appends only items not already saved (dedup by link).
    3-returns how many new items were added.
    """
    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")

    seen = set()  # links already saved
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            seen.add(json.loads(line).get("link"))

    rows = get_news(ticker)
    saved = 0
    with open(path, "a", encoding="utf-8", buffering=1) as f:  # append
        for row in rows:
            iso = parse_date(row.get("created", ""))
            if not iso or iso < "2026-01-01":  # 2026 only
                continue
            link = row.get("url", "")  # relative path on nasdaq.com
            if link and link.startswith("/"):
                link = "https://www.nasdaq.com" + link
            if link in seen:  # skip already saved
                continue
            rec = {
                "ticker": ticker,
                "date": iso,
                "title": row.get("title", ""),
                "publisher": row.get("publisher", ""),
                "link": link,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            saved += 1
    return saved

# final- run
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tickers = get_tickers()

    for i, ticker in enumerate(tickers):
        try:
            saved = save_news(ticker)
            print(f"  {i+1}/{len(tickers)}  {ticker}  +{saved} new")
        except Exception as e:
            print(f"  {i+1}/{len(tickers)}  {ticker}  error: {e}")
        time.sleep(RATE)

    print("done.")

if __name__ == "__main__":
    main()