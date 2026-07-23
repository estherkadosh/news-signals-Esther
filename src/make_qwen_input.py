# 1- make_qwen_input.py
"""
make_qwen_input.py
builds a focused input file for the qwen run on kaggle:
keeps only articles from ticker-days with 2+ distinct sources,
where the signal was shown to work. writes qwen_input.jsonl.
"""

import json
import pandas as pd

# 1- config
SIGNALS = "raw_data/signals.csv"
MERGED = "raw_data/merged_clean.jsonl"
OUT = "raw_data/qwen_input.jsonl"
MIN_SOURCES = 2  # coverage threshold - signal lives here

# 2- covered ticker-days
def covered_days():
    """
    returns the set of (ticker, date) with enough source coverage.
    """
    df = pd.read_csv(SIGNALS)
    df = df[df["n_sources"] >= MIN_SOURCES]
    return set(zip(df["ticker"], df["date"].astype(str)))

# final- run
def main():
    keep = covered_days()
    n_in = n_out = 0
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for line in open(MERGED, encoding="utf-8"):
            rec = json.loads(line)
            n_in += 1
            if (rec["ticker"], rec["date"]) not in keep:  # only covered days
                continue
            out = {"ticker": rec["ticker"], "date": rec["date"], "source": rec["source"],
                   "title": rec["title"], "text": rec["text"][:600]}  # trim for prompt
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
            n_out += 1
    print(f"{n_in} articles in, {n_out} kept -> {OUT}")

if __name__ == "__main__":
    main()