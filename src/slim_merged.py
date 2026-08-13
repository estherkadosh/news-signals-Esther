# 1- slim_merged.py
"""
slim_merged.py
writes a lightweight merged file for the deployed app: only the fields the app
needs (keys + link), dropping the heavy article body. much smaller for github.
"""

import json

# 1- config
IN = "raw_data/merged.jsonl"
OUT = "raw_data/merged_slim.jsonl"

# final- run
def main():
    n = 0
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for line in open(IN, encoding="utf-8"):
            r = json.loads(line)
            slim = {"ticker": r["ticker"], "date": r["date"], "source": r["source"],
                    "title": r["title"], "link": r.get("link", "")}  # drop body text
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} rows -> {OUT}")

if __name__ == "__main__":
    main()