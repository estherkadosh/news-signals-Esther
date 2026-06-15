# 1- coverage_test.py
"""
coverage_test.py
two diagnostics for the demo:
A- compares t-stat and sharpe across each weighting scheme we tried.
B- splits high vs low coverage to show where the signal lives.
uses the exact same weights and >=2 article filter as build_signals + backtest,
so the numbers line up with the production pipeline.
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf

# 1- config (same source weights as build_signals.py)
SENT = "raw_data/sentiment.jsonl"
DECILE = 0.2
MIN_ARTICLES = 2  # same filter as backtest.py
SOURCE_W = {"yahoo": 3.0, "stockanalysis": 3.0, "nasdaq": 2.0, "finviz": 1.0, "edgar": 1.0}

# 2- load per-article sentiment
def load():
    """
    reads per-article sentiment with source kept.
    """
    df = pd.DataFrame(json.loads(l) for l in open(SENT, encoding="utf-8"))
    df["date"] = pd.to_datetime(df["date"])
    return df

# 3- next-day returns
def load_returns(tickers, start, end):
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    rets = px.pct_change().shift(-1).stack().reset_index()
    rets.columns = ["date", "ticker", "fwd_ret"]
    rets["date"] = pd.to_datetime(rets["date"])
    return rets

# 4- aggregate per ticker-day under a chosen weighting scheme
def aggregate(df, scheme):
    """
    builds per-ticker-day polarity under one scheme:
    'raw'        = plain mean
    'source'     = source-quality weighted
    'strength'   = source x sentiment-strength weighted (production scheme)
    filters to >=2 articles per ticker-day (same as backtest).
    """
    rows = []
    for (tk, dt), g in df.groupby(["ticker", "date"]):
        if scheme == "raw":
            pol = g["polarity"].mean()
        elif scheme == "source":
            w = g["source"].map(SOURCE_W).fillna(1.0)
            pol = np.average(g["polarity"], weights=w) if w.sum() else 0
        else:  # strength = source x sentiment-strength (matches build_signals)
            sw = g["source"].map(SOURCE_W).fillna(1.0)
            stw = g["polarity"].abs() + 0.1
            w = sw * stw
            pol = np.average(g["polarity"], weights=w) if w.sum() else 0
        rows.append({"ticker": tk, "date": dt, "polarity": pol,
                     "n_articles": len(g), "n_sources": g["source"].nunique()})
    out = pd.DataFrame(rows)
    out = out[out["n_articles"] >= MIN_ARTICLES]  # same filter as backtest
    return out

# 5- backtest a per-ticker-day table
def backtest(daily, rets):
    """
    long-short top/bottom quintile by polarity. returns t-stat, sharpe, hit, days.
    """
    m = daily.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])
    spreads = []
    for _, g in m.groupby("date"):
        if len(g) < 10:
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
        lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
        if len(hi) and len(lo):
            spreads.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
    s = pd.Series(spreads)
    if len(s) < 2:
        return None
    tstat = s.mean() / (s.std() / np.sqrt(len(s)))
    sharpe = (s.mean() / s.std()) * np.sqrt(252)
    return {"t_stat": round(tstat, 2), "sharpe": round(sharpe, 2),
            "hit": round((s > 0).mean() * 100, 1), "days": len(s)}

# 6- coverage split on a per-ticker-day table
def coverage_split(daily, rets):
    """
    splits ticker-days by median sources and backtests each group.
    """
    m = daily.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])
    cutoff = m["n_sources"].median()
    print(f"median sources/day = {cutoff}")
    print(f"{'group':16s}{'t-stat':>8}{'sharpe':>8}{'hit%':>8}{'days':>7}")
    for label, sub in [("ALL", m), ("HIGH coverage", m[m["n_sources"] > cutoff]),
                       ("LOW coverage", m[m["n_sources"] <= cutoff])]:
        spreads = []
        for _, g in sub.groupby("date"):
            if len(g) < 6:
                continue
            hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
            lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
            if len(hi) and len(lo):
                spreads.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
        s = pd.Series(spreads)
        if len(s) >= 2:
            t = s.mean() / (s.std() / np.sqrt(len(s)))
            sh = (s.mean() / s.std()) * np.sqrt(252)
            print(f"{label:16s}{t:>8.2f}{sh:>8.2f}{(s>0).mean()*100:>8.1f}{len(s):>7}")

# final- run
def main():
    df = load()
    tickers = df["ticker"].unique().tolist()
    rets = load_returns(tickers, df["date"].min(), df["date"].max() + pd.Timedelta(days=3))

    # A- weighting schemes
    print("=" * 64)
    print("A- effect of each weighting scheme (next-day, >=2 articles)")
    print("=" * 64)
    print(f"{'scheme':16s}{'t-stat':>8}{'sharpe':>8}{'hit%':>8}{'days':>7}")
    for scheme, label in [("raw", "raw mean"), ("source", "+ source wt"),
                          ("strength", "+ strength wt")]:
        res = backtest(aggregate(df, scheme), rets)
        if res:
            print(f"{label:16s}{res['t_stat']:>8}{res['sharpe']:>8}{res['hit']:>8}{res['days']:>7}")

    # B- coverage split (production scheme)
    print("\n" + "=" * 64)
    print("B- where the signal lives: high vs low coverage (strength scheme)")
    print("=" * 64)
    coverage_split(aggregate(df, "strength"), rets)

if __name__ == "__main__":
    main()