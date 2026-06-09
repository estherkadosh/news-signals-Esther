# 1- decile_test.py
"""
decile_test.py
signal test: each day sort ticker-days into sentiment quintiles,
compare next-day return of top vs bottom. reports the spread.
"""

import pandas as pd

# 1- config
IN = "raw_data/sentiment_returns.csv"  # sentiment + fwd_ret per ticker-day

# 2- load
def load():
    """
    reads the matched sentiment-returns table.
    """
    df = pd.read_csv(IN)
    df["date"] = pd.to_datetime(df["date"])
    return df

# final- run
def main():
    df = load()

    # bucket by daily sentiment sign (top = positive, bottom = negative)
    top = df[df["polarity"] > 0]
    bottom = df[df["polarity"] < 0]
    neutral = df[df["polarity"] == 0]

    print(f"top (pos):    n={len(top):5d}  mean fwd_ret={top['fwd_ret'].mean()*100:.4f}%")
    print(f"neutral:      n={len(neutral):5d}  mean fwd_ret={neutral['fwd_ret'].mean()*100:.4f}%")
    print(f"bottom (neg): n={len(bottom):5d}  mean fwd_ret={bottom['fwd_ret'].mean()*100:.4f}%")

    spread = (top["fwd_ret"].mean() - bottom["fwd_ret"].mean()) * 100
    print(f"\ntop-minus-bottom spread: {spread:.4f}% per day")

    # hit rate: how often positive sentiment day had positive next-day return
    hit = (top["fwd_ret"] > 0).mean() * 100
    print(f"hit rate (pos sentiment -> pos return): {hit:.1f}%")

if __name__ == "__main__":
    main()