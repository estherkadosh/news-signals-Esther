# 1- edgar_scraper.py
"""
edgar_scraper.py
fetches all 8-K filings (official event reports) for a ticker from sec edgar,
and saves them to a jsonl file on disk (one filing per line: date + url).
"""

import requests
import time
import json
import os

# 1- config
HEADERS = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}  # required by sec
RATE = 0.2  # =5 requests/sec
OUT_DIR = "raw_data/edgar_filings"  # output folder

# 2- ticker -> cik
def get_cik(ticker):
    """
    this:
    1-converts ticker (e.g. AAPL) to the CIK number sec uses to identify a company.
    2-fetches the full ticker->company list from sec and searches for the wanted ticker.
    3-raises an error if not found.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    for e in r.json().values():
        if e["ticker"] == ticker.upper():
            return str(e["cik_str"]).zfill(10)  # 10 digits, padded
    raise ValueError(f"{ticker} not found")

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
    2-builds a record per filing including a direct url to the filing index.
    """
    recent = data["filings"]["recent"]
    forms = recent["form"]
    dates = recent["filingDate"]
    accessions = recent["accessionNumber"]  # unique id per filing
    docs = recent["primaryDocument"]        # main file name

    records = []
    cik_int = int(cik)  # without leading zeros - for url path uses
    for form, date, acc, doc in zip(forms, dates, accessions, docs):
        if form == "8-K" and date >= "2026-01-01":  # 2026 only - project window
            acc_nodash = acc.replace("-", "")  # without dashes - for url path uses
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

# 5- save jsonl
def save_jsonl(records, ticker):
    """
    writes each record as one json line. line-buffered so nothing is lost on crash.
    """
    os.makedirs(OUT_DIR, exist_ok=True)  # create folder if missing
    path = os.path.join(OUT_DIR, f"{ticker}.jsonl")
    with open(path, "w", encoding="utf-8", buffering=1) as f:  # buffering=1 = line-buffered
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path

# 6- strip boilerplate
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

# 7- fetch filing body text
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

# 8- save bodies
def save_bodies(records, ticker):
    """
    1-goes over each filing record and downloads its body text.
    2-saves all bodies to one jsonl file (record fields + the text).
    3-rate-limited between requests to respect sec limits.
    """
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{ticker}_bodies.jsonl")
    with open(path, "w", encoding="utf-8", buffering=1) as f:
        for i, rec in enumerate(records):
            text = fetch_body(rec["url"])
            time.sleep(RATE)  # politeness between downloads
            if not text:  # skip filings with no extractable text
                print(f"  {i+1}/{len(records)}  {rec['date']}  empty, skipped")
                continue
            rec["body"] = text  # attach text to the record
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {i+1}/{len(records)}  {rec['date']}  chars={len(text)}")
    return path

# final- run
def main():
    ticker = "AAPL"
    cik = get_cik(ticker)
    time.sleep(RATE)

    data = get_filings(cik)
    records = extract_8k(data, cik, ticker)
    save_jsonl(records, ticker)

    # downloading bodies for the filings
    print(f"{ticker} ({data.get('name', '?')}) cik={cik}  filings={len(records)}")
    path = save_bodies(records, ticker)
    print(f"saved bodies -> {path}")

if __name__ == "__main__":
    main()