# 1- stockanalysis_scraper.py
"""
stockanalysis_scraper.py
fetches recent 2026 news (title + summary + date) for the s&p 500 from stockanalysis.com,
and saves each ticker to its own jsonl file. resumable: done tickers are skipped.
"""

import requests
import json
import os
import sys
import time
from datetime import datetime
from lxml import html

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # make src/ importable
from sp500 import get_tickers

# 1- config
HEADERS = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}  # polite identification
OUT_DIR = "raw_data/stockanalysis_news"  # output folder
# RATE = 1.0  # 1 sec between tickers - be gentle
RATE = 3.0  # 3 sec between tickers - stockanalysis is rate-sensitive

# 2- fetch news items
def get_news(ticker):
    """
    1-downloads the stockanalysis quote page for the ticker.
    2-on 429 (too many requests) waits and retries up to 3 times.
    3-parses each news item into title, summary, link, date_title.
    """
    url = f"https://stockanalysis.com/stocks/{ticker}/"
    for attempt in range(3):
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 429:  # rate-limited - back off and retry
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        break
    else:
        raise RuntimeError("429 after retries")

    tree = html.fromstring(r.text)
    items = []
    for node in tree.xpath('//div[contains(@class,"grid-cols-news")]'):
        title_el = node.xpath('.//h3/a')  # headline anchor
        if not title_el:
            continue
        title = title_el[0].text_content().strip()
        link = title_el[0].get("href")
        summary_el = node.xpath('.//p')  # summary text
        summary = summary_el[0].text_content().strip() if summary_el else ""
        date_el = node.xpath('.//div[@title]')  # full date in title attr
        date_raw = date_el[0].get("title") if date_el else ""
        items.append({"title": title, "summary": summary, "link": link, "date_raw": date_raw})
    return items

# 3- normalize date
def parse_date(date_raw):
    """
    1-stockanalysis gives a full date like 'Jun 8, 2026, 5:01 AM EDT'.
    2-takes the date part only and returns iso (yyyy-mm-dd), or none.
    """
    try:
        part = date_raw.split(",")[0] + "," + date_raw.split(",")[1]  # 'Jun 8, 2026'
        return datetime.strptime(part.strip(), "%b %d, %Y").date().isoformat()
    except Exception:
        return None

# 4- save one ticker
def save_news(ticker):
    """
    1-fetches the ticker news and normalizes dates.
    2-appends only items not already saved (dedup by link).
    3-returns how many new items were added.
    """
    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")

    seen = set()  # links already saved
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            seen.add(json.loads(line).get("link"))

    items = get_news(ticker)
    saved = 0
    with open(path, "a", encoding="utf-8", buffering=1) as f:  # append
        for it in items:
            iso = parse_date(it["date_raw"])
            if not iso or iso < "2026-01-01":  # 2026 only
                continue
            if it["link"] in seen:  # skip already saved
                continue
            rec = {"ticker": ticker, "date": iso, "title": it["title"],
                   "summary": it["summary"], "link": it["link"]}
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