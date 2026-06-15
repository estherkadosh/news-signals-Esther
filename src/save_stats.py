# save_stats.py
# runs the backtest once and saves headline numbers for the app to read instantly.
import json
import pandas as pd
import numpy as np
import yfinance as yf

sig = pd.read_csv("raw_data/signals.csv")
sig = sig[sig["n_articles"] >= 2].copy()
sig["date"] = pd.to_datetime(sig["date"])
tickers = sig["ticker"].unique().tolist()
px = yf.download(tickers, start=sig["date"].min(), end=sig["date"].max() + pd.Timedelta(days=3),
                 auto_adjust=True, progress=False)["Close"]
rets = px.pct_change().shift(-1).stack().reset_index()
rets.columns = ["date", "ticker", "fwd_ret"]
rets["date"] = pd.to_datetime(rets["date"])
df = sig.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])

def tstat_of(d):
    sp = []
    for _, g in d.groupby("date"):
        if len(g) < 6:
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(0.8)]
        lo = g[g["polarity"] <= g["polarity"].quantile(0.2)]
        if len(hi) and len(lo):
            hw = np.average(hi["fwd_ret"], weights=hi["confidence"]) if hi["confidence"].sum() else hi["fwd_ret"].mean()
            lw = np.average(lo["fwd_ret"], weights=lo["confidence"]) if lo["confidence"].sum() else lo["fwd_ret"].mean()
            sp.append(hw - lw)
    s = pd.Series(sp)
    return (s.mean() / (s.std() / np.sqrt(len(s))), len(s)) if len(s) > 1 else (0, 0)

cut = df["n_sources"].median()
t_all, n_days = tstat_of(df)
t_high, _ = tstat_of(df[df["n_sources"] > cut])
t_low, _ = tstat_of(df[df["n_sources"] <= cut])


total_articles = sum(1 for _ in open("raw_data/merged.jsonl", encoding="utf-8"))  # all collected
nonzero = sum(1 for l in open("raw_data/sentiment.jsonl", encoding="utf-8") if json.loads(l)["polarity"] != 0)  # with real sentiment

stats = {"t_all": round(t_all, 2), "n_days": n_days,
         "t_high": round(t_high, 2), "t_low": round(t_low, 2),
         "total_articles": total_articles, "nonzero_articles": nonzero,
         "ticker_days": int((sig["n_articles"] >= 2).sum())}
json.dump(stats, open("raw_data/stats.json", "w"))
print("saved:", stats)