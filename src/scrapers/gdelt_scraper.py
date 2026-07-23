# 1- gdelt_scraper.py
"""
gdelt_scraper.py
fetches historical news headlines for the s&p 500 from the gdelt doc api,
one query per ticker per year, going back several years.
saves each ticker to its own jsonl. incremental: appends only new links.
"""

import requests
import json
import os
import sys
import time
from io import StringIO
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # make src/ importable
from sp500 import get_tickers

# 1- config
API = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"}
OUT_DIR = "raw_data/gdelt_news"  # output folder
NAMES_CACHE = "raw_data/sp500_names.json"  # ticker -> company name
RATE = 15.0  # gdelt asks 5s minimum - well above it to avoid ip blocks
BACKOFF = [60, 180, 600]  # wait 1min, 3min, 10min on repeated blocks
YEARS = [2024, 2025, 2026]  # history window
MAXREC = 250  # api cap per request

# 2- ticker -> company name map
def get_names():
    """
    1-returns the cached ticker->name map if present.
    2-otherwise scrapes wikipedia's constituent table and caches it.
    """
    if os.path.exists(NAMES_CACHE):
        return json.load(open(NAMES_CACHE, encoding="utf-8"))

    import pandas as pd
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    r = requests.get(url, headers={"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"})
    r.raise_for_status()
    tbl = pd.read_html(StringIO(r.text))[0]
    names = {}
    for sym, sec in zip(tbl["Symbol"], tbl["Security"]):
        names[str(sym).replace(".", "-")] = str(sec)
    json.dump(names, open(NAMES_CACHE, "w", encoding="utf-8"))
    return names
# 3- fetch one year for one company
def fetch_year(name, year):
    """
    1-queries gdelt for the company name within one calendar year.
    2-on 429 waits progressively longer (1, 3, 10 min) before retrying.
    3-returns the articles list, or empty after giving up politely.
    """
    params = {
        "query": f'"{name}" (stock OR shares OR earnings OR revenue) sourcelang:english',
        "mode": "artlist",
        "maxrecords": MAXREC,
        "startdatetime": f"{year}0101000000",
        "enddatetime": f"{year}1231235959",
        "format": "json",
    }
    for wait in BACKOFF + [None]:
        r = requests.get(API, params=params, headers=HEADERS, timeout=60)
        if r.status_code == 429:  # blocked - wait longer, then retry
            if wait is None:
                print("    gdelt still blocking, skipping this window")
                return []
            print(f"    429 - waiting {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        try:
            return r.json().get("articles") or []
        except Exception:  # gdelt returns non-json when empty
            return []
    return []

# 4- normalize date
def parse_date(seen):
    """
    1-gdelt gives a stamp like '20260719T004500Z'.
    2-returns iso date (yyyy-mm-dd), or none.
    """
    try:
        return datetime.strptime(seen[:8], "%Y%m%d").date().isoformat()
    except Exception:
        return None

# 5- save one ticker
def save_news(ticker, name):
    """
    1-loops the configured years, querying gdelt for each.
    2-appends only articles not already saved (dedup by url).
    3-returns how many new articles were added.
    """
    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")

    seen = set()  # urls already saved
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            seen.add(json.loads(line).get("link"))

    saved = 0
    with open(path, "a", encoding="utf-8", buffering=1) as f:  # append
        for year in YEARS:
            arts = fetch_year(name, year)
            time.sleep(RATE)  # gdelt rate limit
            for a in arts:
                link = a.get("url", "")
                if not link or link in seen:  # skip duplicates
                    continue
                iso = parse_date(a.get("seendate", ""))
                if not iso:
                    continue
                rec = {"ticker": ticker, "date": iso, "title": a.get("title", "").strip(),
                       "publisher": a.get("domain", ""), "link": link}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                seen.add(link)
                saved += 1
    return saved

# final- run
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tickers = get_tickers()
    names = get_names()

    for i, ticker in enumerate(tickers):
        name = names.get(ticker)
        if not name:  # not in wikipedia table (manually added tickers)
            print(f"  {i+1}/{len(tickers)}  {ticker}  no name, skipped")
            continue
        try:
            saved = save_news(ticker, name)
            print(f"  {i+1}/{len(tickers)}  {ticker}  +{saved} new")
        except Exception as e:  # don't let one bad ticker kill the run
            print(f"  {i+1}/{len(tickers)}  {ticker}  error: {e}")

    print("done.")

if __name__ == "__main__":
    main()