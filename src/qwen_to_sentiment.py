# 1- qwen_to_sentiment.py
"""
qwen_to_sentiment.py
converts the qwen output into the sentiment.jsonl format the pipeline expects,
so qwen becomes the primary sentiment engine. backs up the finbert file first.
"""

import json
import os
import shutil

# 1- config
QWEN = "raw_data/qwen_sentiment_full.jsonl"
OUT = "raw_data/sentiment.jsonl"
BACKUP = "raw_data/sentiment_finbert.jsonl"  # keep finbert for comparison

# final- run
def main():
    if os.path.exists(OUT) and not os.path.exists(BACKUP):
        shutil.copy(OUT, BACKUP)  # preserve finbert once
        print(f"backed up finbert -> {BACKUP}")

    n = 0
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for line in open(QWEN, encoding="utf-8"):
            r = json.loads(line)
            rec = {"ticker": r["ticker"], "date": r["date"], "source": r["source"],
                   "title": r["title"], "polarity": r["polarity"],
                   "n_sents": 1}  # qwen scores whole article as one unit
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} articles -> {OUT} (qwen is now primary)")

if __name__ == "__main__":
    main()