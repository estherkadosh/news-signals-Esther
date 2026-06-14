# 1- inspect_data.py
"""
inspect_data.py
samples raw articles per source to reveal source-specific noise
before writing any cleaning rules. read-only, changes nothing.
"""

import json
import glob
import os

# 1- config
SOURCES = {
    "edgar": "raw_data/edgar_filings",
    "finviz": "raw_data/finviz_news",
    "stockanalysis": "raw_data/stockanalysis_news",
    "yahoo": "raw_data/yahoo_news",
    "nasdaq": "raw_data/nasdaq_news",
}

# 2- sample one source
def sample(folder, k=3):
    """
    returns the first k records found across the folder's files.
    """
    out = []
    for path in glob.glob(os.path.join(folder, "*.jsonl")):
        for line in open(path, encoding="utf-8"):
            out.append(json.loads(line))
            if len(out) >= k:
                return out
    return out

# final- run
def main():
    for name, folder in SOURCES.items():
        print("=" * 70)
        print(name.upper())
        print("=" * 70)
        for rec in sample(folder, 3):
            title = rec.get("title", "")
            text = rec.get("body", "") or rec.get("summary", "")
            print(f"  title  : {title[:90]}")
            print(f"  text   : {text[:200]}")
            print(f"  fields : {list(rec.keys())}")
            print("-" * 40)

if __name__ == "__main__":
    main()