# 1- build_signals.py
"""
build_signals.py
joins per-article sentiment + events into one signals table,
then aggregates to per-ticker per-day: mean polarity, article count, event tags.
this table feeds the backtest and the app.
"""

import json
import pandas as pd
import numpy as np

# 1- config
SENT = "raw_data/sentiment.jsonl"  # per-article polarity
EVENTS = "raw_data/events.jsonl"   # per-article event tags
OUT = "raw_data/signals.csv"       # per-ticker per-day signals

# 2- load jsonl
def load(path):
    """
    reads a jsonl file into a dataframe.
    """
    return pd.DataFrame(json.loads(l) for l in open(path, encoding="utf-8"))

# final- run
def main():
    sent = load(SENT)
    ev = load(EVENTS)

    # join sentiment and events per article (same keys)
    keys = ["ticker", "date", "source", "title"]
    df = sent.merge(ev[keys + ["events"]], on=keys, how="left")
    df = df[df["n_sents"] > 0]  # drop empty
    df["events"] = df["events"].apply(lambda x: x if isinstance(x, list) else [])

    # aggregate per ticker per day
    weights = {"yahoo": 3.0, "stockanalysis": 3.0, "nasdaq": 2.0,
               "finviz": 1.0, "edgar": 0.5}  # trust full-body sources more

    def agg(g):
        all_events = [e for lst in g["events"] for e in lst]
        w = g["source"].map(weights).fillna(1.0)  # source-quality weight
        wmean = np.average(g["polarity"], weights=w) if w.sum() else 0
        n_sources = g["source"].nunique()  # how many distinct sources agree
        sharpness = g["polarity"].abs().mean()  # how decisive the sentiment is
        confidence = n_sources * (0.5 + sharpness)  # more sources + sharper = more confident
        return pd.Series({
            "polarity": wmean,
            "n_articles": len(g),
            "n_sources": n_sources,
            "confidence": round(confidence, 3),
            "events": ",".join(sorted(set(all_events))),
        })

    daily = df.groupby(["ticker", "date"]).apply(agg).reset_index()
    daily.to_csv(OUT, index=False)
    print(f"{len(daily)} ticker-days -> {OUT}")
    print(daily.head(8).to_string(index=False))

if __name__ == "__main__":
    main()