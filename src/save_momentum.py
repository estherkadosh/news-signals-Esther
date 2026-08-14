# 1- save_momentum.py
"""
save_momentum.py
runs the momentum thesis once and saves the three-variant results per lookback
to momentum.json, so the app can show them instantly without recomputing.
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf

# 1- config
SIGNALS = "raw_data/signals.csv"
OUT = "raw_data/momentum.json"
LOOKBACKS = [5, 21, 63]
DECILE = 0.2
BLEND = 0.5
MIN_ARTICLES = 2

# 2- load
def load_signals():
    df = pd.read_csv(SIGNALS)
    df = df[df["n_articles"] >= MIN_ARTICLES].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df[["ticker", "date", "polarity"]]

def build_panel(px, lookback):
    mom = px.pct_change(lookback)
    fwd = px.pct_change().shift(-1)
    m = mom.stack().reset_index(); m.columns = ["date", "ticker", "momentum"]
    f = fwd.stack().reset_index(); f.columns = ["date", "ticker", "fwd_ret"]
    out = m.merge(f, on=["date", "ticker"], how="inner").dropna()
    out["date"] = pd.to_datetime(out["date"])
    return out

# 3- backtest a ranked column
def tstat(df, rank_col, use_filter=False):
    sp = []
    for _, g in df.groupby("date"):
        if len(g) < 15:
            continue
        hi = g[g[rank_col] >= g[rank_col].quantile(1 - DECILE)]
        lo = g[g[rank_col] <= g[rank_col].quantile(DECILE)]
        if use_filter:
            hi = hi[hi["polarity"] >= 0]
            lo = lo[lo["polarity"] <= 0]
        if len(hi) >= 3 and len(lo) >= 3:
            sp.append(hi["fwd_ret"].mean() - lo["fwd_ret"].mean())
    s = pd.Series(sp)
    return round(s.mean() / (s.std() / np.sqrt(len(s))), 2) if len(s) > 1 else 0.0

# final- run
def main():
    sig = load_signals()
    tickers = sorted(sig["ticker"].unique())
    px = yf.download(tickers, start=sig["date"].min() - pd.Timedelta(days=120),
                     end=sig["date"].max() + pd.Timedelta(days=3),
                     auto_adjust=True, progress=False)["Close"].dropna(axis=1, how="all")

    results = {}
    for lb in LOOKBACKS:
        panel = build_panel(px, lb)
        merged = panel.merge(sig, on=["ticker", "date"], how="inner")
        merged["mom_z"] = merged.groupby("date")["momentum"].transform(lambda x: (x - x.mean()) / (x.std() + 1e-9))
        merged["sent_z"] = merged.groupby("date")["polarity"].transform(lambda x: (x - x.mean()) / (x.std() + 1e-9))
        merged["blend"] = (1 - BLEND) * merged["mom_z"] + BLEND * merged["sent_z"]
        results[lb] = {
            "alone": tstat(merged, "momentum"),
            "filter": tstat(merged, "momentum", use_filter=True),
            "blend": tstat(merged, "blend"),
        }
    json.dump(results, open(OUT, "w"))
    print("saved:", results)

if __name__ == "__main__":
    main()