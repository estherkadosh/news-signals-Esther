# 1- explain.py
"""
explain.py
for a given ticker+date, returns the top driving articles behind its sentiment signal:
the most positive and most negative headlines, with source and events.
this is the explainability layer for the app.
"""

import json
import pandas as pd

# 1- config
SENT = "raw_data/sentiment.jsonl"  # per-article polarity
EVENTS = "raw_data/events.jsonl"   # per-article event tags

# 2- load merged per-article
def load():
    """
    joins sentiment and events per article into one dataframe.
    """
    sent = pd.DataFrame(json.loads(l) for l in open(SENT, encoding="utf-8"))
    ev = pd.DataFrame(json.loads(l) for l in open(EVENTS, encoding="utf-8"))
    keys = ["ticker", "date", "source", "title"]
    df = sent.merge(ev[keys + ["events"]], on=keys, how="left")
    return df

# 3- explain one ticker-day
def explain(df, ticker, date, k=3):
    """
    returns top-k positive and top-k negative driving articles for ticker on date.
    """
    g = df[(df["ticker"] == ticker) & (df["date"] == date)]
    if g.empty:
        return None
    pos = g.sort_values("polarity", ascending=False).head(k)
    neg = g.sort_values("polarity").head(k)
    return {"ticker": ticker, "date": date, "mean_polarity": round(g["polarity"].mean(), 3),
            "n_articles": len(g), "top_positive": pos.to_dict("records"),
            "top_negative": neg.to_dict("records")}

# final- run
def main():
    df = load()
    # demo: explain AAPL on its ceo-change day
    res = explain(df, "NVDA", "2026-06-03")
    if res:
        print(f"{res['ticker']} {res['date']}  mean_polarity={res['mean_polarity']}  n={res['n_articles']}")
        print("\ntop positive:")
        for r in res["top_positive"]:
            print(f"  +{r['polarity']:.2f} [{r['source']}] {r['title'][:80]}  {r.get('events')}")
        print("\ntop negative:")
        for r in res["top_negative"]:
            print(f"  {r['polarity']:.2f} [{r['source']}] {r['title'][:80]}  {r.get('events')}")

if __name__ == "__main__":
    main()