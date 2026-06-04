# 1- finviz_scraper.py
"""
finviz_scraper.py
fetches recent 2026 news headlines for a list of tickers from finviz,
fills in each headline's date, and saves each ticker to its own jsonl file.
resumable: tickers already downloaded are skipped.
"""

import requests
import json
import os
import time
from datetime import datetime
from lxml import html

# 1- config
HEADERS = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}  # polite identification
OUT_DIR = "raw_data/finviz_news"  # output folder
RATE = 1.0  # 1 sec between tickers - finviz is commercial, be gentle
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM",
           "V", "WMT", "JNJ", "PG", "MA", "HD", "KO", "PEP", "COST", "MRK",
           "ABBV", "CRM", "NFLX", "AMD", "INTC", "CSCO", "ORCL"]  # sample 25

# 2- fetch headlines
def get_headlines(ticker):
    """
    1-downloads the finviz quote page for the ticker.
    2-parses the news table into rows of (date_text, title, link).
    3-returns the rows as a list.
    """
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    tree = html.fromstring(r.text)

    rows = []
    for row in tree.xpath('//table[contains(@class,"fullview-news-outer")]//tr'):
        cells = row.xpath('.//td')
        if len(cells) < 2:
            continue
        date_text = cells[0].text_content().strip()  # date or time only
        link_el = cells[1].xpath('.//a')[0]           # headline anchor
        title = link_el.text_content().strip()
        link = link_el.get("href")
        rows.append((date_text, title, link))
    return rows

# 3- normalize dates
def parse_date(date_text, last_date):
    """
    1-finviz gives a full date only on the first headline of each day.
    2-rows with time-only inherit the last seen date.
    3-returns the iso date (yyyy-mm-dd) and the updated last_date.
    """
    parts = date_text.split()
    head = parts[0]  # either a date token or a time token
    if head == "Today":
        d = datetime.now().date()
    elif "-" in head:  # full date like Jun-03-26
        d = datetime.strptime(head, "%b-%d-%y").date()
    else:  # time only - reuse last seen date
        d = last_date
    return d.isoformat() if d else None, d

# 4- save one ticker
def save_headlines(ticker):
    """
    1-fetches the ticker headlines and normalizes their dates.
    2-keeps only 2026 headlines (project window).
    3-writes each as one json line to the ticker's file. returns count saved.
    """
    rows = get_headlines(ticker)
    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")

    last_date = None
    saved = 0
    with open(path, "w", encoding="utf-8", buffering=1) as f:  # line-buffered
        for date_text, title, link in rows:
            iso, last_date = parse_date(date_text, last_date)
            if not iso or iso < "2026-01-01":  # 2026 only
                continue
            rec = {"ticker": ticker, "date": iso, "title": title, "link": link}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            saved += 1
    return saved

# final- run
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for i, ticker in enumerate(TICKERS):
        path = os.path.join(OUT_DIR, f"{ticker}.jsonl")
        if os.path.exists(path):  # resume - skip already-downloaded tickers
            print(f"  {i+1}/{len(TICKERS)}  {ticker}  already done, skipped")
            continue
        try:
            saved = save_headlines(ticker)
            print(f"  {i+1}/{len(TICKERS)}  {ticker}  saved {saved} headlines")
        except Exception as e:  # don't let one bad ticker kill the whole run
            print(f"  {i+1}/{len(TICKERS)}  {ticker}  error: {e}")
        time.sleep(RATE)  # politeness between tickers

    print("done.")

if __name__ == "__main__":
    main()