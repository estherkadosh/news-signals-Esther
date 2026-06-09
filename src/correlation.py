# 1- correlation.py
"""
correlation.py
tests whether daily sentiment predicts returns.
fetches prices, aligns next-day return to each day's sentiment, reports correlation.
"""

import pandas as pd
import yfinance as yf
from scipy.stats import pearsonr, spearmanr

# 1- config
IN = "raw_data/daily_sentiment.csv"  # per-ticker per-day polarity
MIN_ARTICLES = 2  # ignore thin days

# 2- load sentiment
def load_sentiment():
    """
    reads daily sentiment, keeps days with enough articles.
    """
    df = pd.read_csv(IN)
    df = df[df["n_articles"] >= MIN_ARTICLES]
    df["date"] = pd.to_datetime(df["date"])
    return df

# 3- fetch prices for tickers
def fetch_prices(tickers, start, end):
    """
    1-downloads adjusted close for all tickers in one batch.
    2-returns a long df of ticker, date, next-day return.
    """
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    rets = data.pct_change().shift(-1)  # next-day return aligned to today
    rets = rets.stack().reset_index()
    rets.columns = ["date", "ticker", "fwd_ret"]
    return rets

# final- run
def main():
    sent = load_sentiment()
    tickers = sent["ticker"].unique().tolist()
    start, end = sent["date"].min(), sent["date"].max() + pd.Timedelta(days=3)

    prices = fetch_prices(tickers, start, end)
    prices["date"] = pd.to_datetime(prices["date"])

    # join sentiment to next-day return
    m = sent.merge(prices, on=["ticker", "date"], how="inner").dropna(subset=["fwd_ret"])

    p_r, p_p = pearsonr(m["polarity"], m["fwd_ret"])
    s_r, s_p = spearmanr(m["polarity"], m["fwd_ret"])

    print(f"matched {len(m)} ticker-days")
    print(f"pearson  r={p_r:.4f}  p={p_p:.4g}")
    print(f"spearman r={s_r:.4f}  p={s_p:.4g}")

    m.to_csv("raw_data/sentiment_returns.csv", index=False)
    print("saved -> raw_data/sentiment_returns.csv")

if __name__ == "__main__":
    main()