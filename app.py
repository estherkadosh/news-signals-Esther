# 1- app.py
"""
app.py
news-driven equity signals dashboard.
compact grid of ranked tickers: long (buy) and short (sell) lists,
each card shows a mini sentiment-vs-price chart + score, expandable for drivers.
run: streamlit run app.py
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="News-Driven Equity Signals", layout="wide")

# 1- config
SIGNALS = "raw_data/signals.csv"
SENT = "raw_data/sentiment.jsonl"
EVENTS = "raw_data/events.jsonl"
COLS = 4  # cards per row

# 2- load data (cached)
@st.cache_data
def load_signals():
    df = pd.read_csv(SIGNALS)
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data
def load_articles():
    sent = pd.DataFrame(json.loads(l) for l in open(SENT, encoding="utf-8"))
    ev = pd.DataFrame(json.loads(l) for l in open(EVENTS, encoding="utf-8"))
    keys = ["ticker", "date", "source", "title"]
    return sent.merge(ev[keys + ["events"]], on=keys, how="left")

@st.cache_data
def load_prices(ticker, start, end):
    try:
        px = yf.Ticker(ticker).history(start=start, end=end)
        px.index = px.index.tz_localize(None)
        return px
    except Exception:
        return pd.DataFrame()

# 3- score one ticker by chosen method
def score_ticker(g, method):
    """
    returns a single 'current sentiment' score per the chosen method.
    """
    g = g.sort_values("date")
    if method == "last day":
        return g.iloc[-1]["polarity"]
    if method == "7-day mean":
        return g.tail(7)["polarity"].mean()
    last = g["date"].max()
    age = (last - g["date"]).dt.days
    w = 0.5 ** (age / 3.0)  # decay, half-life ~3 days
    return np.average(g["polarity"], weights=w)

# 4- build ranking
@st.cache_data
def build_ranking(method, min_articles):
    sig = load_signals()
    rows = []
    for ticker, g in sig.groupby("ticker"):
        if g["n_articles"].sum() < min_articles:
            continue
        rows.append({"ticker": ticker, "score": round(score_ticker(g, method), 3),
                     "total_articles": int(g["n_articles"].sum())})
    return pd.DataFrame(rows).sort_values("score", ascending=False)

# 5- tiny chart
def mini_chart(ticker, tsig):
    px = load_prices(ticker, tsig["date"].min(), tsig["date"].max())
    fig, ax1 = plt.subplots(figsize=(3.2, 1.5))
    if not px.empty:
        ax1.plot(px.index, px["Close"], color="black", linewidth=1.0)
    ax2 = ax1.twinx()
    ax2.bar(tsig["date"], tsig["polarity"], width=1.2, alpha=0.35, color="steelblue")
    ax2.set_ylim(-1.1, 1.1)
    ax1.set_xticks([]); ax1.set_yticks([]); ax2.set_yticks([])  # clean tiny chart
    fig.tight_layout(pad=0.2)
    return fig

# 6- drivers (inside expander)
def show_drivers(ticker, articles, tsig):
    day = tsig.sort_values("n_articles", ascending=False).iloc[0]["date"].strftime("%Y-%m-%d")
    g = articles[(articles["ticker"] == ticker) & (articles["date"] == day)]
    if g.empty:
        st.caption("no article detail")
        return
    st.caption(f"busiest day {day} - {len(g)} articles")
    for _, r in g.sort_values("polarity", ascending=False).head(3).iterrows():
        st.markdown(f":green[+{r['polarity']:.2f}] {r['title'][:70]}")
    for _, r in g.sort_values("polarity").head(3).iterrows():
        st.markdown(f":red[{r['polarity']:.2f}] {r['title'][:70]}")

# 7- render a grid of cards
def render_grid(rank_df, signals, articles, n_show):
    rows = rank_df.head(n_show).to_dict("records")
    for i in range(0, len(rows), COLS):
        cols = st.columns(COLS)
        for col, row in zip(cols, rows[i:i+COLS]):
            with col:
                tsig = signals[signals["ticker"] == row["ticker"]].sort_values("date")
                color = "green" if row["score"] > 0 else "red"
                st.markdown(f"**{row['ticker']}**  :{color}[{row['score']:+.2f}]")
                st.pyplot(mini_chart(row["ticker"], tsig))
                with st.expander("why?"):
                    show_drivers(row["ticker"], articles, tsig)

# 8- sidebar
st.sidebar.header("Ranking settings")
method = st.sidebar.radio("Rank by 'current sentiment':",
                          ["decay-weighted", "7-day mean", "last day"], index=0)
min_articles = st.sidebar.slider("Min total articles per ticker", 1, 50, 5)
n_show = st.sidebar.slider("How many per list", 4, 40, 12)

# final- main
st.title("News-Driven Equity Signals")
st.caption("S&P 500 - 2026 - 5 sources - FinBERT sentiment + events")

signals = load_signals()
articles = load_articles()
rank = build_ranking(method, min_articles)
longs = rank[rank["score"] > 0]
shorts = rank[rank["score"] < 0].sort_values("score")

st.markdown(f"**{len(rank)} tickers ranked** by *{method}* - "
            f":green[{len(longs)} long] / :red[{len(shorts)} short]")

st.header(":green[LONG - buy candidates] (most to least recommended)")
render_grid(longs, signals, articles, n_show)

st.divider()
st.header(":red[SHORT - sell candidates] (most to least recommended)")
render_grid(shorts, signals, articles, n_show)