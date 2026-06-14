# 1- backtest.py
"""
backtest.py
daily long-short signal test: long top sentiment decile, short bottom decile,
hold one day. reports mean daily spread, t-stat, sharpe, hit rate.
"""

import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
IN = "raw_data/signals.csv"  # per-ticker per-day signals
MIN_ARTICLES = 2  # ignore thin days
DECILE = 0.2  # top/bottom 20%

# 2- load signals
def load():
    """
    reads signals, keeps days with enough articles.
    """
    df = pd.read_csv(IN)
    df = df[df["n_articles"] >= MIN_ARTICLES].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df

# 3- fetch returns
def fetch_returns(tickers, start, end):
    """
    next-day return per ticker-day from adjusted close.
    """
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    rets = px.pct_change().shift(-1).stack().reset_index()  # next-day return aligned to today
    rets.columns = ["date", "ticker", "fwd_ret"]
    return rets

# final- run
def main():
    sig = load()
    tickers = sig["ticker"].unique().tolist()
    start, end = sig["date"].min(), sig["date"].max() + pd.Timedelta(days=3)

    rets = fetch_returns(tickers, start, end)
    rets["date"] = pd.to_datetime(rets["date"])
    df = sig.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])

    # each day: long top quintile, short bottom quintile by polarity
    # each day: long top quintile, short bottom quintile by polarity
    daily_spread = []
    for date, g in df.groupby("date"):
        if len(g) < 10:  # need enough names that day
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
        lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
        if len(hi) and len(lo):
            # weight each side by confidence (more sources + sharper sentiment)
            hi_ret = np.average(hi["fwd_ret"], weights=hi["confidence"]) if "confidence" in hi and hi["confidence"].sum() else hi["fwd_ret"].mean()
            lo_ret = np.average(lo["fwd_ret"], weights=lo["confidence"]) if "confidence" in lo and lo["confidence"].sum() else lo["fwd_ret"].mean()
            daily_spread.append(hi_ret - lo_ret)

    s = pd.Series(daily_spread)
    mean = s.mean()
    tstat = mean / (s.std() / np.sqrt(len(s)))
    sharpe = (mean / s.std()) * np.sqrt(252)  # annualized
    hit = (s > 0).mean()

    print(f"trading days: {len(s)}")
    print(f"mean daily long-short spread: {mean*100:.4f}%")
    print(f"t-stat: {tstat:.2f}")
    print(f"annualized sharpe: {sharpe:.2f}")
    print(f"hit rate (positive days): {hit*100:.1f}%")
    print(f"cumulative spread: {s.sum()*100:.2f}%")

if __name__ == "__main__":
    main()