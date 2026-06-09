# 1- aggregate.py
"""
aggregate.py
turns per-article sentiment into a per-ticker per-day mean polarity score.
saves a tidy table for plotting and correlation.
"""

import json
import os
import pandas as pd

# 1- config
IN = "raw_data/sentiment.jsonl"  # per-article scores
OUT = "raw_data/daily_sentiment.csv"  # per-ticker per-day

# 2- load scores
def load():
    """
    reads the per-article sentiment jsonl into a dataframe.
    """
    rows = [json.loads(line) for line in open(IN, encoding="utf-8")]
    return pd.DataFrame(rows)

# final- run
def main():
    df = load()
    df = df[df["n_sents"] > 0]  # drop empty articles

    # mean polarity + article count per ticker per day
    daily = (df.groupby(["ticker", "date"])
               .agg(polarity=("polarity", "mean"), n_articles=("polarity", "size"))
               .reset_index())
    daily.to_csv(OUT, index=False)
    print(f"{len(daily)} ticker-days -> {OUT}")
    print(daily.head(10).to_string(index=False))

if __name__ == "__main__":
    main()