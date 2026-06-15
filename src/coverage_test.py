# 1- coverage_test.py
"""
coverage_test.py
two diagnostics for the demo, using the EXACT backtest logic (reads signals.csv,
confidence-weighted long-short), so numbers match backtest.py perfectly:
A- effect of weighting schemes (raw signals vs production signals).
B- where the signal lives: high vs low coverage.
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf

# 1- config (identical to backtest.py)
SIGNALS = "raw_data/signals.csv"   # production signals (source x strength weighted)
SENT = "raw_data/sentiment.jsonl"  # raw per-article, for the 'raw' baseline
MIN_ARTICLES = 2
DECILE = 0.2

# 2- fetch returns (identical to backtest.py)
def fetch_returns(tickers, start, end):
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    rets = px.pct_change().shift(-1).stack().reset_index()
    rets.columns = ["date", "ticker", "fwd_ret"]
    rets["date"] = pd.to_datetime(rets["date"])
    return rets

# 3- the exact backtest from backtest.py, as a function
def run_backtest(df, use_confidence):
    """
    df has polarity, fwd_ret, and (optionally) confidence per ticker-day.
    long top quintile, short bottom, confidence-weighted if available.
    returns t-stat, sharpe, hit, days - identical math to backtest.py.
    """
    daily_spread = []
    for date, g in df.groupby("date"):
        if len(g) < 10:
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
        lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
        if len(hi) and len(lo):
            if use_confidence and "confidence" in hi and hi["confidence"].sum():
                hi_ret = np.average(hi["fwd_ret"], weights=hi["confidence"])
                lo_ret = np.average(lo["fwd_ret"], weights=lo["confidence"])
            else:
                hi_ret = hi["fwd_ret"].mean()
                lo_ret = lo["fwd_ret"].mean()
            daily_spread.append(hi_ret - lo_ret)
    s = pd.Series(daily_spread)
    if len(s) < 2:
        return None
    tstat = s.mean() / (s.std() / np.sqrt(len(s)))
    sharpe = (s.mean() / s.std()) * np.sqrt(252)
    return {"t": round(tstat, 2), "sharpe": round(sharpe, 2),
            "hit": round((s > 0).mean() * 100, 1), "days": len(s)}

# 4- build a raw-mean baseline table from sentiment.jsonl
def raw_signals():
    """
    plain per-ticker-day mean polarity (no weighting), >=2 articles.
    this is the 'before any weighting' baseline.
    """
    df = pd.DataFrame(json.loads(l) for l in open(SENT, encoding="utf-8"))
    df = df[df["n_sents"] > 0]
    g = df.groupby(["ticker", "date"]).agg(
        polarity=("polarity", "mean"), n_articles=("polarity", "size"),
        n_sources=("source", "nunique")).reset_index()
    g = g[g["n_articles"] >= MIN_ARTICLES]
    g["date"] = pd.to_datetime(g["date"])
    return g

# 5- load production signals (already weighted, from build_signals)
def prod_signals():
    df = pd.read_csv(SIGNALS)
    df = df[df["n_articles"] >= MIN_ARTICLES].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df

# final- run
def main():
    prod = prod_signals()
    raw = raw_signals()
    tickers = prod["ticker"].unique().tolist()
    rets = fetch_returns(tickers, prod["date"].min(), prod["date"].max() + pd.Timedelta(days=3))

    # A- raw baseline vs production (with confidence weighting)
    print("=" * 64)
    print("A- raw mean signal vs full production signal")
    print("=" * 64)
    print(f"{'scheme':22s}{'t-stat':>8}{'sharpe':>8}{'hit%':>8}{'days':>7}")

    raw_m = raw.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])
    res = run_backtest(raw_m, use_confidence=False)
    if res: print(f"{'raw mean (no weights)':22s}{res['t']:>8}{res['sharpe']:>8}{res['hit']:>8}{res['days']:>7}")

    prod_m = prod.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])
    res = run_backtest(prod_m, use_confidence=False)
    if res: print(f"{'+ source/strength wt':22s}{res['t']:>8}{res['sharpe']:>8}{res['hit']:>8}{res['days']:>7}")

    res = run_backtest(prod_m, use_confidence=True)
    if res: print(f"{'+ confidence wt (FULL)':22s}{res['t']:>8}{res['sharpe']:>8}{res['hit']:>8}{res['days']:>7}")

    # B- coverage split on full production signal
    print("\n" + "=" * 64)
    print("B- where the signal lives: high vs low coverage (full signal)")
    print("=" * 64)
    cutoff = prod_m["n_sources"].median()
    print(f"median sources/day = {cutoff}")
    print(f"{'group':16s}{'t-stat':>8}{'sharpe':>8}{'hit%':>8}{'days':>7}")
    for label, sub in [("ALL", prod_m), ("HIGH coverage", prod_m[prod_m["n_sources"] > cutoff]),
                       ("LOW coverage", prod_m[prod_m["n_sources"] <= cutoff])]:
        res = run_backtest(sub, use_confidence=True)
        if res:
            print(f"{label:16s}{res['t']:>8}{res['sharpe']:>8}{res['hit']:>8}{res['days']:>7}")

if __name__ == "__main__":
    main()