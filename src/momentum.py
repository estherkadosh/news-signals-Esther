# 1- momentum.py
"""
momentum.py
tests whether news sentiment improves a momentum strategy.
baseline: long top momentum quintile, short bottom, hold one day.
filtered: drop longs with negative recent sentiment and shorts with positive.
runs three lookback windows and compares.
"""

import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
SIGNALS = "raw_data/signals.csv"
LOOKBACKS = [5, 21, 63]  # week, month, quarter
DECILE = 0.2
SENT_WINDOW = 5  # trading days of sentiment used as the filter
MIN_ARTICLES = 2  # ignore thin ticker-days

# 2- load sentiment
def load_signals():
    """
    per-ticker-day polarity, thin days dropped.
    """
    df = pd.read_csv(SIGNALS)
    df = df[df["n_articles"] >= MIN_ARTICLES].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df[["ticker", "date", "polarity"]]

# 3- prices and momentum
def load_prices(tickers, start, end):
    """
    1-downloads adjusted closes for the whole universe.
    2-returns a wide frame indexed by date.
    """
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    return px.dropna(axis=1, how="all")

def build_panel(px, lookback):
    """
    1-momentum = trailing return over the lookback window.
    2-fwd_ret = next-day return, the thing being predicted.
    3-returns a long frame of ticker, date, momentum, fwd_ret.
    """
    mom = px.pct_change(lookback)
    fwd = px.pct_change().shift(-1)
    m = mom.stack().reset_index()
    m.columns = ["date", "ticker", "momentum"]
    f = fwd.stack().reset_index()
    f.columns = ["date", "ticker", "fwd_ret"]
    out = m.merge(f, on=["date", "ticker"], how="inner").dropna()
    out["date"] = pd.to_datetime(out["date"])
    return out

# 4- rolling sentiment per ticker-day
def rolling_sent(sig, panel):
    """
    1-for each ticker-day, averages sentiment over the trailing window.
    2-merges it onto the price panel; missing = no news.
    """
    s = sig.sort_values("date").copy()
    s["roll"] = (s.groupby("ticker")["polarity"]
                   .transform(lambda x: x.rolling(SENT_WINDOW, min_periods=1).mean()))
    return panel.merge(s[["ticker", "date", "roll"]], on=["ticker", "date"], how="left")

# 5- backtest one variant
def run(df, label, use_filter):
    """
    1-each day sorts by momentum into top/bottom quintiles.
    2-if filtering, drops longs with negative sentiment and shorts with positive.
    3-prints t-stat, sharpe, hit rate for the daily long-short spread.
    """
    spreads = []
    for _, g in df.groupby("date"):
        if len(g) < 20:  # need a real cross-section
            continue
        hi = g[g["momentum"] >= g["momentum"].quantile(1 - DECILE)]
        lo = g[g["momentum"] <= g["momentum"].quantile(DECILE)]
        if use_filter:
            hi = hi[~(hi["roll"] < 0)]  # keep positive/unknown sentiment on longs
            lo = lo[~(lo["roll"] > 0)]  # keep negative/unknown sentiment on shorts
        if len(hi) >= 3 and len(lo) >= 3:
            spreads.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
    s = pd.Series(spreads)
    if len(s) < 2:
        print(f"{label:28s} not enough days")
        return
    t = s.mean() / (s.std() / np.sqrt(len(s)))
    sh = (s.mean() / s.std()) * np.sqrt(252)
    print(f"{label:28s} days={len(s):4d}  spread={s.mean()*100:+.4f}%  "
          f"t-stat={t:+.2f}  sharpe={sh:+.2f}  hit={(s>0).mean()*100:.1f}%")

# final- run
def main():
    sig = load_signals()
    tickers = sorted(sig["ticker"].unique())
    start = sig["date"].min() - pd.Timedelta(days=120)  # room for the longest lookback
    end = sig["date"].max() + pd.Timedelta(days=3)
    px = load_prices(tickers, start, end)

    for lb in LOOKBACKS:
        panel = build_panel(px, lb)
        panel = panel[panel["date"] >= sig["date"].min()]  # score only the sentiment era
        merged = rolling_sent(sig, panel)
        cov = merged["roll"].notna().mean() * 100
        print(f"\n--- lookback {lb} days  (sentiment covers {cov:.1f}% of rows) ---")
        run(merged, f"momentum {lb}d alone", use_filter=False)
        run(merged, f"momentum {lb}d + news filter", use_filter=True)

if __name__ == "__main__":
    main()