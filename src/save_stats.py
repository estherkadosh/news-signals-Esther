# save_stats.py
# runs the backtest once and saves headline numbers for the app to read instantly.
# now also saves: sharpe, hit rate, and the raw-mean baseline t-stat (t_raw),
# so every current-state number in the app is automatic.
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

def spreads_of(d):
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
    return pd.Series(sp)

def stats_of(d):
    s = spreads_of(d)
    if len(s) < 2:
        return 0.0, 0.0, 0.0, 0
    t = s.mean() / (s.std() / np.sqrt(len(s)))
    sh = (s.mean() / s.std()) * np.sqrt(252)
    hit = (s > 0).mean() * 100
    return round(t, 2), round(sh, 2), round(hit, 1), len(s)

cut = df["n_sources"].median()
t_all, sharpe, hit, n_days = stats_of(df)
t_high, _, _, _ = stats_of(df[df["n_sources"] > cut])
t_low, _, _, _ = stats_of(df[df["n_sources"] <= cut])

# raw-mean baseline (no weighting), for the weighting-progression line
raw = pd.DataFrame(json.loads(l) for l in open("raw_data/sentiment.jsonl", encoding="utf-8"))
raw["date"] = pd.to_datetime(raw["date"])
raw_g = raw.groupby(["ticker", "date"]).agg(polarity=("polarity", "mean"),
                                            n=("polarity", "size")).reset_index()
raw_g = raw_g[raw_g["n"] >= 2]
raw_m = raw_g.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])
raw_sp = []
for _, g in raw_m.groupby("date"):
    if len(g) < 6:
        continue
    hi = g[g["polarity"] >= g["polarity"].quantile(0.8)]
    lo = g[g["polarity"] <= g["polarity"].quantile(0.2)]
    if len(hi) and len(lo):
        raw_sp.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
raw_s = pd.Series(raw_sp)
t_raw = round(raw_s.mean() / (raw_s.std() / np.sqrt(len(raw_s))), 2) if len(raw_s) > 1 else 0.0

total_articles = sum(1 for _ in open("raw_data/merged.jsonl", encoding="utf-8"))  # all collected
nonzero = sum(1 for l in open("raw_data/sentiment.jsonl", encoding="utf-8") if json.loads(l)["polarity"] != 0)

# next-day stats for the long side, to phrase a concrete per-card line
hi_days = df[df["polarity"] >= df["polarity"].quantile(0.8)]
up_rate = (hi_days["fwd_ret"] > 0).mean()
avg_move = hi_days["fwd_ret"].abs().mean()

stats = {"t_all": t_all, "t_raw": t_raw, "sharpe": sharpe, "hit": hit, "n_days": n_days,
         "t_high": t_high, "t_low": t_low,
         "total_articles": total_articles, "nonzero_articles": nonzero,
         "ticker_days": int((sig["n_articles"] >= 2).sum()),
         "up_rate": round(up_rate * 100, 0),
         "avg_move": round(avg_move * 100, 2)}
json.dump(stats, open("raw_data/stats.json", "w"))
print("saved:", stats)