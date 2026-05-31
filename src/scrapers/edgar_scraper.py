# 1- edgar_scraper.py
"""
edgar_scraper.py
fetches all 2026 8-K filings (official event reports) for a list of tickers
from sec edgar, and saves each ticker's filings + body text to its own jsonl file.
resumable: tickers already downloaded are skipped.
"""

import requests
import time
import json
import os

# 1- config
HEADERS = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}  # required by sec
RATE = 0.2  # =5 requests/sec
OUT_DIR = "raw_data/edgar_filings"  # output folder
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM",
           "V", "WMT", "JNJ", "PG", "MA", "HD", "KO", "PEP", "COST", "MRK",
           "ABBV", "CRM", "NFLX", "AMD", "INTC", "CSCO", "ORCL"]  # sample 25

# 2- load ticker->cik map once
def load_cik_map():
    """
    fetches the full ticker->cik list from sec a single time.
    returns a dict of ticker -> 10-digit cik for fast lookup.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return {e["ticker"]: str(e["cik_str"]).zfill(10) for e in r.json().values()}

# 3- fetch filings
def get_filings(cik):
    """
    this fetches the recent filings list for a company by its CIK.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

# 4- build filing records
def extract_8k(data, cik, ticker):
    """
    1-pulls all 8-K filings from the recent block.
    2-keeps only 2026 filings (the project window).
    3-builds a record per filing including a direct url to the filing.
    """
    recent = data["filings"]["recent"]
    forms = recent["form"]
    dates = recent["filingDate"]
    accessions = recent["accessionNumber"]  # unique id per filing
    docs = recent["primaryDocument"]        # main file name

    records = []
    cik_int = int(cik)  # without leading zeros - for url path
    for form, date, acc, doc in zip(forms, dates, accessions, docs):
        if form == "8-K" and date >= "2026-01-01":  # 2026 only - project window
            acc_nodash = acc.replace("-", "")  # without dashes - for url path
            url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"
            records.append({
                "ticker": ticker,
                "cik": cik,
                "form": form,
                "date": date,
                "accession": acc,
                "url": url,
            })
    return records

# 5- strip boilerplate
def clean_boilerplate(text):
    """
    1-drops common sec legal lines that repeat in every filing and carry no signal.
    2-returns only the lines with real content.
    """
    junk = [
        "securities and exchange commission", "washington, d.c.",
        "pursuant to section", "former name or former address",
        "emerging growth company", "check the appropriate box",
        "written communications", "soliciting material",
        "pre-commencement", "title of each class", "trading symbol",
        "name of each exchange", "i.r.s. employer", "commission file number",
        "state or other jurisdiction", "inline xbrl", "signature",
        "duly authorized", "/s/",
    ]
    lines = []
    for line in text.split("\n"):
        low = line.strip().lower()
        if low and not any(j in low for j in junk):  # keep real-content lines only
            lines.append(line.strip())
    return "\n".join(lines)

# 6- fetch filing body text
def fetch_body(url):
    """
    1-downloads the filing html from the given url.
    2-extracts clean readable text out of it (drops tags, menus).
    3-strips boilerplate and returns the text, or none if extraction failed.
    """
    import trafilatura
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    text = trafilatura.extract(r.text)  # html -> clean text
    if not text:
        return None
    return clean_boilerplate(text)

# 7- process one ticker
def process_ticker(ticker, cik):
    """
    1-fetches the ticker's 2026 8-K filings and their body text.
    2-writes them to the ticker's own jsonl file (skips empty bodies).
    3-returns how many filings were saved.
    """
    data = get_filings(cik)
    time.sleep(RATE)
    records = extract_8k(data, cik, ticker)

    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")
    saved = 0
    with open(path, "w", encoding="utf-8", buffering=1) as f:  # line-buffered
        for rec in records:
            text = fetch_body(rec["url"])
            time.sleep(RATE)  # politeness between downloads
            if not text:  # skip filings with no extractable text
                continue
            rec["body"] = text
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            saved += 1
    return saved

# final- run
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cik_map = load_cik_map()
    time.sleep(RATE)

    for i, ticker in enumerate(TICKERS):
        path = os.path.join(OUT_DIR, f"{ticker}.jsonl")
        if os.path.exists(path):  # resume - skip already-downloaded tickers
            print(f"  {i+1}/{len(TICKERS)}  {ticker}  already done, skipped")
            continue
        cik = cik_map.get(ticker)
        if not cik:  # ticker not found in sec map
            print(f"  {i+1}/{len(TICKERS)}  {ticker}  no cik, skipped")
            continue
        saved = process_ticker(ticker, cik)
        print(f"  {i+1}/{len(TICKERS)}  {ticker}  saved {saved} filings")

    print("done.")

if __name__ == "__main__":
    main()