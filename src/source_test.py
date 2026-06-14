# 1- source_test.py
"""
source_test.py
diagnostic: backtest using each news source alone, to see which source
carries real predictive signal and which is noise. read-only on signals.
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
SENT = "raw_data/sentiment.jsonl"
DECILE = 0.2
SOURCES = ["finviz", "yahoo", "stockanalysis", "nasdaq", "edgar"]

# 2- load per-article sentiment
def load_sent():
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

# 4- backtest one source
def backtest_source(df_src, rets, label):
    """
    aggregates one source to per-ticker-day mean, backtests long-short.
    """
    daily = (df_src.groupby(["ticker", "date"])["polarity"].mean().reset_index())
    m = daily.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])

    spreads = []
    for date, g in m.groupby("date"):
        if len(g) < 6:
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
        lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
        if len(hi) and len(lo):
            spreads.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
    s = pd.Series(spreads)
    if len(s) < 2:
        print(f"{label:15s} not enough days")
        return
    tstat = s.mean() / (s.std() / np.sqrt(len(s)))
    print(f"{label:15s} rows={len(df_src):6d}  days={len(s):3d}  "
          f"spread={s.mean()*100:+.4f}%  t-stat={tstat:+.2f}  hit={(s>0).mean()*100:.1f}%")

# final- run
def main():
    df = load_sent()
    tickers = df["ticker"].unique().tolist()
    rets = load_returns(tickers, df["date"].min(), df["date"].max() + pd.Timedelta(days=3))

    for src in SOURCES:
        sub = df[df["source"] == src]
        if len(sub):
            backtest_source(sub, rets, src)

if __name__ == "__main__":
    main()