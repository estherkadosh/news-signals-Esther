# 1- app.py
"""
app.py
news-driven equity signals dashboard.
ranks all tickers long/short, most to least recommended, with professional
dark charts, recent events, a data-confidence score, source links, and a
limitations panel. run: streamlit run app.py
"""

import json
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="News-Driven Equity Signals", layout="wide")
plt.style.use("dark_background")  # professional dark charts

# 1- config
SIGNALS = "raw_data/signals.csv"
SENT = "raw_data/sentiment.jsonl"
EVENTS = "raw_data/events.jsonl"
MERGED = "raw_data/merged.jsonl"
COLS = 4

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
    merged = pd.DataFrame(json.loads(l) for l in open(MERGED, encoding="utf-8"))
    keys = ["ticker", "date", "source", "title"]
    df = sent.merge(ev[keys + ["events"]], on=keys, how="left")
    df = df.merge(merged[keys + ["link"]], on=keys, how="left")  # bring links in
    return df

@st.cache_data
def load_prices(ticker, start, end):
    try:
        px = yf.Ticker(ticker).history(start=start, end=end)
        px.index = px.index.tz_localize(None)
        return px
    except Exception:
        return pd.DataFrame()

# 3- score one ticker
def score_ticker(g, method):
    g = g.sort_values("date")
    if method == "last day":
        return g.iloc[-1]["polarity"]
    if method == "7-day mean":
        return g.tail(7)["polarity"].mean()
    last = g["date"].max()
    age = (last - g["date"]).dt.days
    w = 0.5 ** (age / 3.0)  # decay, half-life ~3 days
    return np.average(g["polarity"], weights=w)

# 4- data-confidence (not statistical significance - see limitations)
def confidence(g):
    """
    1-proxy for trust in the signal: more articles + more days + consistent sign = higher.
    2-returns a 0-100 score and a short label.
    """
    n_art = g["n_articles"].sum()
    n_days = len(g)
    consistency = abs(g["polarity"].mean()) / (g["polarity"].std() + 0.5)  # sign stability
    raw = min(n_art, 60) / 60 * 50 + min(n_days, 20) / 20 * 30 + min(consistency, 1) * 20
    score = int(min(raw, 100))
    label = "high" if score >= 66 else "medium" if score >= 40 else "low"
    return score, label

# 5- build ranking
@st.cache_data
def build_ranking(method, min_articles, min_sources):
    sig = load_signals()
    rows = []
    for ticker, g in sig.groupby("ticker"):
        total = int(g["n_articles"].sum())
        if total < min_articles:
            continue
        avg_sources = g["n_sources"].mean() if "n_sources" in g else 1  # coverage breadth
        if avg_sources < min_sources:  # coverage filter - signal works on covered names
            continue
        recent = g.sort_values("date").tail(5)
        rec_ev = []
        for e in recent["events"].dropna():
            rec_ev += [x for x in str(e).split(",") if x]
        # if "confidence" in g and g["confidence"].max() > 0:  # use real confidence column
        #     conf = int(min(g["confidence"].mean() / g["confidence"].max() * 100, 100))
        # else:
        #     conf = 50
        # conf_label = "high" if conf >= 66 else "medium" if conf >= 40 else "low"
        nonzero = (g["polarity"].abs() > 0).mean()  # share of decisive (non-neutral) days
        breadth = min(g["n_sources"].mean() / 3, 1) if "n_sources" in g else 0.5  # source breadth
        conf = int((nonzero * 0.6 + breadth * 0.4) * 100)  # decisive + broad = confident
        conf_label = "high" if conf >= 60 else "medium" if conf >= 35 else "low"

        rows.append({"ticker": ticker, "score": round(score_ticker(g, method), 3),
                     "total_articles": total, "last_date": g["date"].max().strftime("%Y-%m-%d"),
                     "recent_events": ",".join(sorted(set(rec_ev))[:3]) or "—",
                     "avg_sources": round(avg_sources, 1),
                     "conf": conf, "conf_label": conf_label})
    return pd.DataFrame(rows).sort_values("score", ascending=False)

# 6- professional chart
def pro_chart(ticker, tsig):
    px = load_prices(ticker, tsig["date"].min(), tsig["date"].max())
    fig, ax1 = plt.subplots(figsize=(3.8, 2.3))
    fig.patch.set_facecolor("#0e1117")
    ax1.set_facecolor("#0e1117")

    # price line (left axis)
    if not px.empty:
        ax1.plot(px.index, px["Close"], color="white", linewidth=1.1, label="Price")
    ax1.set_ylabel("Price ($)", color="white", fontsize=7)
    ax1.tick_params(axis="y", colors="white", labelsize=6)

    # sentiment bars (right axis)
    ax2 = ax1.twinx()
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in tsig["polarity"]]
    ax2.bar(tsig["date"], tsig["polarity"], width=1.2, alpha=0.8, color=colors)
    ax2.axhline(0, color="gray", linewidth=0.7)  # zero line
    ax2.set_ylim(-1.1, 1.1)
    ax2.set_ylabel("Sentiment", color="white", fontsize=7)
    ax2.tick_params(axis="y", colors="white", labelsize=6)

    # x axis: show month ticks
    ax1.tick_params(axis="x", colors="white", labelsize=6, rotation=0)
    import matplotlib.dates as mdates
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))  # Jan, Feb...

    ax1.set_title(f"{ticker} · Price (white) vs News Sentiment (bars) · 2026",
                  color="white", fontsize=6.5)
    for s in ax1.spines.values(): s.set_color("#333")
    for s in ax2.spines.values(): s.set_color("#333")
    fig.tight_layout(pad=0.3)
    return fig

# 7- drivers with links
def show_drivers(ticker, articles, tsig):
    day = tsig.sort_values("n_articles", ascending=False).iloc[0]["date"].strftime("%Y-%m-%d")
    g = articles[(articles["ticker"] == ticker) & (articles["date"] == day)]
    if g.empty:
        st.caption("no article detail")
        return
    st.caption(f"busiest day {day} · {len(g)} articles · mean {g['polarity'].mean():+.2f}")
    for _, r in g.sort_values("polarity", ascending=False).head(3).iterrows():
        link = r.get("link", "")
        title = f"[{r['title'][:65]}]({link})" if isinstance(link, str) and link.startswith("http") else r["title"][:65]
        st.markdown(f":green[+{r['polarity']:.2f}] [{r['source']}] {title}")
    for _, r in g.sort_values("polarity").head(3).iterrows():
        link = r.get("link", "")
        title = f"[{r['title'][:65]}]({link})" if isinstance(link, str) and link.startswith("http") else r["title"][:65]
        st.markdown(f":red[{r['polarity']:.2f}] [{r['source']}] {title}")

# 8- render grid
def render_grid(rank_df, signals, articles, n_show):
    rows = rank_df.head(n_show).to_dict("records")
    for i in range(0, len(rows), COLS):
        cols = st.columns(COLS)
        for col, row in zip(cols, rows[i:i+COLS]):
            with col:
                tsig = signals[signals["ticker"] == row["ticker"]].sort_values("date")
                color = "green" if row["score"] > 0 else "red"
                rank_i = rows.index(row) + 1
                st.markdown(f"**#{rank_i} · {row['ticker']}**")
                st.markdown(f"Signal score: :{color}[{row['score']:+.2f}]")
                st.caption(f"Last news: {row['last_date']}")
                st.caption(f"Total articles: {row['total_articles']}")
                st.caption(f"Avg sources/day: {row['avg_sources']}")
                st.caption(f"Recent events: {row['recent_events']}")
                st.caption(f"Data confidence: {row['conf']}/100 ({row['conf_label']})")
                st.pyplot(pro_chart(row["ticker"], tsig))
                with st.expander("Why this signal? (top driving news)"):
                    show_drivers(row["ticker"], articles, tsig)

# final- main
st.title("News-Driven Equity Signals · S&P 500 · 2026")
# 9- load saved backtest stats (instant - no yfinance call)
@st.cache_data
def load_stats():
    try:
        return json.load(open("raw_data/stats.json", encoding="utf-8"))
    except Exception:
        return None

# limitations panel - numbers read from saved stats.json
stats = load_stats()
t_all = f"{stats['t_all']:.2f}" if stats else "n/a"
n_days = stats["n_days"] if stats else "n/a"
t_high = f"{stats['t_high']:.2f}" if stats else "n/a"
t_low = f"{stats['t_low']:.2f}" if stats else "n/a"
total_art = f"{stats['total_articles']:,}" if stats else "n/a"
nonzero_art = f"{stats['nonzero_articles']:,}" if stats else "n/a"
ticker_days = f"{stats['ticker_days']:,}" if stats else "n/a"

with st.expander("⚠ limitations & methodology — read before trusting any signal"):
    st.markdown(f"""
<small>
**Data.** {total_art} articles collected from 5 sources (SEC EDGAR, Finviz, StockAnalysis,
Yahoo, NASDAQ). Of these, {nonzero_art} carry non-neutral sentiment; the backtest uses
{ticker_days} ticker-days with ≥2 articles.

**How the signal is weighted.** Three layers: *source weighting* (trust full-body sources like
Yahoo over headline-only Finviz), *strength weighting* (neutral articles count near-zero),
and *confidence weighting* (days with more agreeing sources count more). Each layer raised the
backtest t-stat (0.32 → 0.60 → {t_all}).

**Sentiment model errors.** FinBERT mislabels short or ambiguous headlines.
*Example:* "Why Is MRVL Stock Surging?" was tagged negative though the news is positive.

**Confidence is not statistical significance.** The card confidence reflects data volume and
consistency, not a p-value. *Example:* a ticker with few articles can still show a strong score.

**Thin sample.** The backtest spans ~{n_days} trading days, overall t-stat ≈ {t_all}
(not significant; ~2.0 would be). Rankings are suggestive, not proven.

**Signal works mainly on covered names.** Heavily-covered stocks give t-stat ≈ {t_high};
thinly-covered ones ≈ {t_low}. The signal lives in well-covered names.

**Other caveats.** Sources expose only ~2 months back (recent days over-represented).
Returns are next-day (no look-ahead). The S&P 500 universe is fixed at one snapshot,
so mid-year index changes aren't tracked.
Universe is the S&P 500 at one snapshot, plus MRVL and SPCX added manually
(both newly index-eligible in 2026); prices via Yahoo Finance cover both NYSE and NASDAQ listings.

**Newly-listed stocks.** A ticker appears once it has enough articles, but its price line needs
at least two trading days to draw. *Example:* SPCX (SpaceX) began trading 12 Jun 2026 — only one
trading day so far — so it shows sentiment but no price line yet, and is far too short to backtest.

**Not investment advice.**
</small>
""", unsafe_allow_html=True)
    

#second panel - experiments results:
# methodology panel - the full experiment journey
with st.expander("🔬 methodology — how the signal was built & tested"):
    st.markdown(f"""
<small>
**Two NLP layers.** FinBERT sentiment (per sentence, averaged per article) + a rule-based
event classifier (8 types: earnings, guidance, M&A, capital return, executive, legal, analyst, product).

**Weighting, built in layers (each raised the backtest t-stat):**

1. *Source weighting* — full-body sources (Yahoo, StockAnalysis) get weight 3, headline-only
Finviz gets 1, EDGAR 1. Rationale: a full article carries clearer tone than a bare headline.
Effect: t-stat 0.32 → 0.60.

2. *Strength weighting* — each article weighted by |sentiment|+0.1, so neutral articles count
near-zero without being deleted. Fixes the dilution from many neutral headlines.

3. *Confidence weighting* — ticker-days backed by more agreeing sources and sharper sentiment
count more in the long-short. Rationale: 5 sources agreeing = a real event; 1 source = noise.
Effect: → t-stat {t_all}.

**Experiments run (honest record):**

- *Text cleaning of EDGAR boilerplate* — improved readability but did NOT raise t-stat; the
problem was neutral dilution, not in-text noise.
- *Same-day returns* — gave t-stat 8.66, but that is look-ahead leakage (using news that
prints after the price moved). Rejected; reverted to next-day.
- *2-day horizon, shift(-2)* — gave a NEGATIVE t-stat (≈ -1.5): the signal reverses after two
days. Classic overreaction / mean-reversion — the market over-responds on day 1, corrects on day 2.
Confirms next-day (shift -1) is the right horizon.

**Coverage experiment (key finding).** Splitting ticker-days by news coverage:
heavily-covered stocks give t-stat ≈ {t_high}; thinly-covered ones ≈ {t_low}. The signal is
real for well-covered names and noise for thinly-covered ones — the opposite of a "hype bubble".
Practical takeaway: trust the ranking most when *Avg sources/day* is high.
</small>
""", unsafe_allow_html=True)


signals = load_signals()
articles = load_articles()
c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
method = c1.selectbox("Rank by", ["decay-weighted", "7-day mean", "last day"], index=0)
min_articles = c2.slider("Min articles", 1, 50, 5)
min_sources = c3.slider("Min sources/day", 1.0, 5.0, 1.0, 0.5)  # coverage filter
n_show = c4.slider("Show per list", 4, 100, 20)
search = c5.text_input("🔍 Search ticker", "").strip().upper()  # find one ticker directly

rank = build_ranking(method, min_articles, min_sources)
longs = rank[rank["score"] > 0]
shorts = rank[rank["score"] < 0].sort_values("score")
c4.markdown(f"**{len(rank)} tickers** · :green[{len(longs)} long] / :red[{len(shorts)} short]")

# search result - show one ticker's card directly if searched
if search:
    hit = rank[rank["ticker"] == search]
    if len(hit):
        st.divider()
        st.subheader(f"🔍 Search result: {search}")
        render_grid(hit, signals, articles, 1)
    else:
        st.warning(f"'{search}' not found in current ranking (check spelling, or lower the Min filters).")
    st.divider()

st.divider()
st.header(":green[LONG — buy candidates]  (most to least recommended)")
render_grid(longs, signals, articles, n_show)

st.divider()
st.header(":red[SHORT — sell candidates]  (most to least recommended)")
render_grid(shorts, signals, articles, n_show)