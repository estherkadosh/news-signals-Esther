# 1- momentum.py
"""
momentum.py
tests whether news sentiment improves a momentum strategy, on the sentiment era only.
three variants per lookback:
  A- momentum alone (long top quintile, short bottom, hold one day)
  B- momentum + news filter (drop longs with negative sentiment, shorts with positive)
  C- momentum + sentiment blend (rank by a mix of momentum and sentiment)
restricted to ticker-days that actually have news, so the filter can bite.
"""

import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
SIGNALS = "raw_data/signals.csv"
LOOKBACKS = [5, 21, 63]  # week, month, quarter
DECILE = 0.2
BLEND = 0.5  # weight of sentiment vs momentum in variant C
MIN_ARTICLES = 2

# 2- load sentiment
def load_signals():
    """
    per-ticker-day polarity, thin days dropped.
    """
    df = pd.read_csv(SIGNALS)
    df = df[df["n_articles"] >= MIN_ARTICLES].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df[["ticker", "date", "polarity"]]

# 3- prices and panel
def load_prices(tickers, start, end):
    px = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    return px.dropna(axis=1, how="all")

def build_panel(px, lookback):
    """
    momentum = trailing return; fwd_ret = next-day return.
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

# 4- one day's long-short spread
def day_spread(g, rank_col, use_filter=False):
    """
    long top quintile, short bottom, by rank_col. optional news filter.
    """
    hi = g[g[rank_col] >= g[rank_col].quantile(1 - DECILE)]
    lo = g[g[rank_col] <= g[rank_col].quantile(DECILE)]
    if use_filter:
        hi = hi[hi["polarity"] >= 0]  # no bad news on longs
        lo = lo[lo["polarity"] <= 0]  # no good news on shorts
    if len(hi) >= 3 and len(lo) >= 3:
        return hi["fwd_ret"].mean() - lo["fwd_ret"].mean()
    return None

# 5- backtest a variant
def run(df, label, rank_col, use_filter=False):
    sp = []
    for _, g in df.groupby("date"):
        if len(g) < 15:
            continue
        s = day_spread(g, rank_col, use_filter)
        if s is not None:
            sp.append(s)
    s = pd.Series(sp)
    if len(s) < 2:
        print(f"{label:34s} not enough days")
        return
    t = s.mean() / (s.std() / np.sqrt(len(s)))
    sh = (s.mean() / s.std()) * np.sqrt(252)
    print(f"{label:34s} days={len(s):4d}  spread={s.mean()*100:+.4f}%  "
          f"t-stat={t:+.2f}  sharpe={sh:+.2f}  hit={(s>0).mean()*100:.1f}%")

# final- run
def main():
    sig = load_signals()
    tickers = sorted(sig["ticker"].unique())
    start = sig["date"].min() - pd.Timedelta(days=120)
    end = sig["date"].max() + pd.Timedelta(days=3)
    px = load_prices(tickers, start, end)

    for lb in LOOKBACKS:
        panel = build_panel(px, lb)
        # keep only ticker-days that have news (inner merge on sentiment)
        merged = panel.merge(sig, on=["ticker", "date"], how="inner")
        if merged.empty:
            print(f"\n--- lookback {lb}d: no overlap ---")
            continue
        # normalized blend of momentum and sentiment for variant C
        merged["mom_z"] = merged.groupby("date")["momentum"].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-9))
        merged["sent_z"] = merged.groupby("date")["polarity"].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-9))
        merged["blend"] = (1 - BLEND) * merged["mom_z"] + BLEND * merged["sent_z"]

        print(f"\n--- lookback {lb} days  ({len(merged)} ticker-days with news) ---")
        run(merged, f"A momentum {lb}d alone", "momentum")
        run(merged, f"B momentum {lb}d + news filter", "momentum", use_filter=True)
        run(merged, f"C momentum {lb}d + sentiment blend", "blend")

if __name__ == "__main__":
    main()