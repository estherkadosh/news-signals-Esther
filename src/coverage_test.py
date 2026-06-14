# 1- coverage_test.py
"""
coverage_test.py
splits ticker-days into high-coverage (many sources) vs low-coverage,
backtests each group separately. tests bubble vs undercovered-alpha.
"""

import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
IN = "raw_data/signals.csv"
DECILE = 0.2

# 2- load + returns
def load_with_returns():
    """
    loads signals, fetches next-day returns, merges them.
    """
    sig = pd.read_csv(IN)
    sig["date"] = pd.to_datetime(sig["date"])
    tickers = sig["ticker"].unique().tolist()
    start, end = sig["date"].min(), sig["date"].max() + pd.Timedelta(days=3)
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    rets = px.pct_change().shift(-1).stack().reset_index()
    rets.columns = ["date", "ticker", "fwd_ret"]
    rets["date"] = pd.to_datetime(rets["date"])
    return sig.merge(rets, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])

# 3- backtest one subset
def run_backtest(df, label):
    """
    daily long-short top/bottom quintile by polarity. prints t-stat for the subset.
    """
    daily = []
    for date, g in df.groupby("date"):
        if len(g) < 6:  # need a few names
            continue
        hi = g[g["polarity"] >= g["polarity"].quantile(1 - DECILE)]
        lo = g[g["polarity"] <= g["polarity"].quantile(DECILE)]
        if len(hi) and len(lo):
            daily.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
    s = pd.Series(daily)
    if len(s) < 2:
        print(f"{label}: not enough days")
        return
    tstat = s.mean() / (s.std() / np.sqrt(len(s)))
    print(f"{label:18s} days={len(s):3d}  spread={s.mean()*100:+.4f}%  "
          f"t-stat={tstat:.2f}  hit={ (s>0).mean()*100:.1f}%")

# final- run
def main():
    df = load_with_returns()

    # split by coverage: median number of sources per ticker-day
    cutoff = df["n_sources"].median()
    high = df[df["n_sources"] > cutoff]   # heavily covered
    low = df[df["n_sources"] <= cutoff]   # lightly covered

    print(f"median sources/day = {cutoff}")
    print(f"high-coverage rows: {len(high)},  low-coverage rows: {len(low)}\n")

    run_backtest(df, "ALL")
    run_backtest(high, "HIGH coverage")
    run_backtest(low, "LOW coverage")

if __name__ == "__main__":
    main()