# 1- yahoo_scraper.py
"""
yahoo_scraper.py
fetches recent 2026 news (title + summary + date + source) for the s&p 500
from yahoo finance via the yfinance library, saving each ticker to its own jsonl.
resumable: done tickers are skipped.
"""

import json
import os
import sys
import time
from datetime import datetime
import yfinance as yf

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # make src/ importable
from sp500 import get_tickers

# 1- config
OUT_DIR = "raw_data/yahoo_news"  # output folder
RATE = 0.5  # half sec between tickers - be gentle

# 2- normalize date
def parse_date(pub):
    """
    1-yfinance gives an iso timestamp like '2026-06-07T13:42:45Z'.
    2-returns the date part only (yyyy-mm-dd), or none.
    """
    try:
        return datetime.fromisoformat(pub.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return None

# 3- extract one item
def extract(item):
    """
    1-yfinance nests the real fields under 'content'.
    2-pulls title, summary, date, source and a best-effort link.
    3-returns a clean dict, or none if no usable title.
    """
    c = item.get("content", {})
    title = c.get("title")
    if not title:
        return None
    link = ""  # link sits under one of a few possible keys
    for key in ("canonicalUrl", "clickThroughUrl"):
        val = c.get(key)
        if isinstance(val, dict) and val.get("url"):
            link = val["url"]
            break
    return {
        "title": title,
        "summary": c.get("summary", ""),
        "date": parse_date(c.get("pubDate", "")),
        "source": c.get("provider", {}).get("displayName", ""),
        "link": link,
    }

# 4- save one ticker
def save_news(ticker):
    """
    1-fetches the ticker news via yfinance.
    2-keeps only 2026 items (project window).
    3-writes each as one json line. returns count saved.
    """
    news = yf.Ticker(ticker).news
    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")

    saved = 0
    with open(path, "w", encoding="utf-8", buffering=1) as f:  # line-buffered
        for item in news:
            rec = extract(item)
            if not rec or not rec["date"] or rec["date"] < "2026-01-01":  # 2026 only
                continue
            rec["ticker"] = ticker
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            saved += 1
    return saved

# final- run
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tickers = get_tickers()

    for i, ticker in enumerate(tickers):
        path = os.path.join(OUT_DIR, f"{ticker}.jsonl")
        if os.path.exists(path):  # resume - skip done tickers
            print(f"  {i+1}/{len(tickers)}  {ticker}  already done, skipped")
            continue
        try:
            saved = save_news(ticker)
            print(f"  {i+1}/{len(tickers)}  {ticker}  saved {saved} news")
        except Exception as e:  # don't let one bad ticker kill the run
            print(f"  {i+1}/{len(tickers)}  {ticker}  error: {e}")
        time.sleep(RATE)  # politeness between tickers

    print("done.")

if __name__ == "__main__":
    main()