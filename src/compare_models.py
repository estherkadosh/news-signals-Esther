# 1- compare_models.py
"""
compare_models.py
head-to-head: finbert vs qwen3 on the same covered ticker-days.
rebuilds signals from each sentiment file and runs the identical backtest,
so any t-stat difference comes from the model, not the data.
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
FINBERT = "raw_data/sentiment.jsonl"       # finbert per-article polarity
QWEN = "raw_data/qwen_sentiment.jsonl"     # qwen per-article polarity
EVENTS = "raw_data/events.jsonl"
MIN_ARTICLES = 2
DECILE = 0.2
WEIGHTS = {"yahoo": 3.0, "stockanalysis": 3.0, "nasdaq": 2.0,
           "finviz": 1.0, "edgar": 1.0, "gdelt": 1.0}

# 2- load a sentiment file
def load_sent(path):
    """
    reads per-article polarity into a dataframe with the shared keys.
    """
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    df = pd.DataFrame(rows)
    return df[["ticker", "date", "source", "title", "polarity"]]

# 3- aggregate to ticker-days (same logic as build_signals)
def build(df):
    """
    1-weights each article by source quality x sentiment strength.
    2-aggregates to per-ticker-day polarity + confidence.
    3-keeps days with 2+ articles.
    """
    out = []
    for (tk, dt), g in df.groupby(["ticker", "date"]):
        if len(g) < MIN_ARTICLES:
            continue
        sw = g["source"].map(WEIGHTS).fillna(1.0)
        stw = g["polarity"].abs() + 0.1
        w = sw * stw
        pol = np.average(g["polarity"], weights=w) if w.sum() else 0
        n_src = g["source"].nunique()
        conf = n_src * (0.5 + g["polarity"].abs().mean())
        out.append({"ticker": tk, "date": dt, "polarity": pol,
                    "n_sources": n_src, "confidence": conf})
    d = pd.DataFrame(out)
    d["date"] = pd.to_datetime(d["date"])
    return d

# 4- returns
def load_returns(tickers, start, end):
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    r = px.pct_change().shift(-1).stack().reset_index()
    r.columns = ["date", "ticker", "fwd_ret"]
    r["date"] = pd.to_datetime(r["date"])
    return r

# 5- backtest (identical to backtest.py)
def run(daily, rets, label):
    """
    confidence-weighted long-short on top/bottom quintiles. prints the result line.
    """
    m = daily.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])
    sp = []
    for _, g in m.groupby("date"):
        if len(g) < 10:
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
        lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
        if len(hi) and len(lo):
            hr = np.average(hi["fwd_ret"], weights=hi["confidence"]) if hi["confidence"].sum() else hi["fwd_ret"].mean()
            lr = np.average(lo["fwd_ret"], weights=lo["confidence"]) if lo["confidence"].sum() else lo["fwd_ret"].mean()
            sp.append(hr - lr)
    s = pd.Series(sp)
    if len(s) < 2:
        print(f"{label:12s} not enough days")
        return
    t = s.mean() / (s.std() / np.sqrt(len(s)))
    sh = (s.mean() / s.std()) * np.sqrt(252)
    print(f"{label:12s} days={len(s):4d}  spread={s.mean()*100:+.4f}%  "
          f"t-stat={t:+.2f}  sharpe={sh:+.2f}  hit={(s>0).mean()*100:.1f}%")

# final- run
def main():
    fb = load_sent(FINBERT)
    qw = load_sent(QWEN)

    # restrict finbert to exactly the articles qwen scored, for a fair test
    keys = set(zip(qw["ticker"], qw["date"], qw["source"], qw["title"]))
    fb = fb[[k in keys for k in zip(fb["ticker"], fb["date"], fb["source"], fb["title"])]]
    print(f"finbert articles {len(fb)}, qwen articles {len(qw)}")

    d_fb, d_qw = build(fb), build(qw)
    tickers = sorted(set(d_fb["ticker"]) | set(d_qw["ticker"]))
    start = min(d_fb["date"].min(), d_qw["date"].min())
    end = max(d_fb["date"].max(), d_qw["date"].max()) + pd.Timedelta(days=3)
    rets = load_returns(tickers, start, end)

    print(f"\n{'model':12s}{'result'}")
    run(d_fb, rets, "FinBERT")
    run(d_qw, rets, "Qwen3-4B")

    # agreement rate between the two models
    j = fb.merge(qw, on=["ticker", "date", "source", "title"], suffixes=("_fb", "_qw"))
    agree = (np.sign(j["polarity_fb"]) == np.sign(j["polarity_qw"])).mean()
    print(f"\nsign agreement: {agree*100:.1f}% on {len(j)} shared articles")

if __name__ == "__main__":
    main()