# 1- app.py
"""
app.py
news-driven equity signals dashboard.
ranks all tickers long/short, most to least recommended, with professional
dark charts, recent events, a data-confidence score, source links, tabs
(Long / Short / About), field tooltips, and methodology panels.
run: streamlit run app.py
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
MERGED = "raw_data/merged_slim.jsonl"
COLS = 4

# field explanations shown on hover (help=)
TIP = {
    "score": "Sentiment score from -1 to +1. How positive recent news is for this stock. Not a price prediction - a ranking of relative positivity.",
    "outlook": "Historical base rate: how often top-signal stocks rose the next day, and the typical next-day move size. Same figure for all cards - it describes the strategy, not the single stock.",
    "last": "Date of the most recent article collected for this ticker.",
    "articles": "Total number of news articles collected for this ticker across all 5 sources.",
    "sources": "Average number of distinct sources per news-day. Higher = a real, widely-reported event; 1 = a single outlet, likelier noise.",
    "events": "Event types tagged in recent news (earnings, M&A, guidance, etc.) by the rule-based classifier.",
    "confidence": "Trust score (0-100): how many articles are decisive (non-neutral) plus source breadth. NOT statistical significance.",
}

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

    # x axis: quarterly ticks so a multi-year range stays readable
    ax1.tick_params(axis="x", colors="white", labelsize=6, rotation=0)
    import matplotlib.dates as mdates
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # every 3 months
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))  # Jan '24

    yr_min = tsig["date"].min().year
    yr_max = tsig["date"].max().year
    span = f"{yr_min}" if yr_min == yr_max else f"{yr_min}–{yr_max}"
    ax1.set_title(f"{ticker} · Price (white) vs News Sentiment (bars) · {span}",
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
def render_grid(rank_df, signals, articles, n_show, stats):
    rows = rank_df.head(n_show).to_dict("records")
    for i in range(0, len(rows), COLS):
        cols = st.columns(COLS)
        for col, row in zip(cols, rows[i:i+COLS]):
            with col:
                tsig = signals[signals["ticker"] == row["ticker"]].sort_values("date")
                color = "green" if row["score"] > 0 else "red"
                rank_i = rows.index(row) + 1
                st.markdown(f"**#{rank_i} · {row['ticker']}**")
                st.markdown(f"Signal score: :{color}[{row['score']:+.2f}]", help=TIP["score"])
                lean = "leans up" if row["score"] > 0 else "leans down"
                if stats and "up_rate" in stats:
                    st.caption(f"Outlook: {lean} · ~{stats['up_rate']:.0f}% up next day · typ. ±{stats['avg_move']:.1f}%",
                               help=TIP["outlook"])
                st.caption(f"Last news: {row['last_date']}", help=TIP["last"])
                st.caption(f"Total articles: {row['total_articles']}", help=TIP["articles"])
                st.caption(f"Avg sources/day: {row['avg_sources']}", help=TIP["sources"])
                st.caption(f"Recent events: {row['recent_events']}", help=TIP["events"])
                st.caption(f"Data confidence: {row['conf']}/100 ({row['conf_label']})", help=TIP["confidence"])
                st.pyplot(pro_chart(row["ticker"], tsig))
                with st.expander("Why this signal? (top driving news)"):
                    show_drivers(row["ticker"], articles, tsig)

# 9- load saved backtest stats (instant - no yfinance call)
@st.cache_data
def load_stats():
    try:
        return json.load(open("raw_data/stats.json", encoding="utf-8"))
    except Exception:
        return None

@st.cache_data
def load_momentum():
    try:
        return json.load(open("raw_data/momentum.json", encoding="utf-8"))
    except Exception:
        return None

# final- main
st.title("News-Driven Equity Signals · S&P 500")
st.caption("Scores positive/negative news sentiment for ~500 S&P 500 stocks and ranks them: "
           "the LONG tab by how positive their recent news is, the SHORT tab by how negative.")

stats = load_stats()

def s_num(key, fmt="{:.2f}", default="n/a"):
    """reads a live number from stats.json, formatted; falls back if missing."""
    if stats and key in stats and stats[key] is not None:
        try:
            return fmt.format(stats[key])
        except Exception:
            return str(stats[key])
    return default

t_all = s_num("t_all")
n_days = s_num("n_days", "{:d}")
t_high = s_num("t_high")
t_low = s_num("t_low")
t_raw = s_num("t_raw")            # raw-mean baseline (auto if present)
sharpe = s_num("sharpe")
hit = s_num("hit", "{:.0f}")
total_art = s_num("total_articles", "{:,}")
nonzero_art = s_num("nonzero_articles", "{:,}")
ticker_days = s_num("ticker_days", "{:,}")

signals = load_signals()
articles = load_articles()

# controls (shared across tabs)
c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
method = c1.selectbox("Rank by", ["decay-weighted", "7-day mean", "last day"], index=0,
                      help="How to turn a stock's news history into one score. "
                           "decay-weighted: recent news counts most (half-life ~3 days). "
                           "7-day mean: simple average of the last 7 news-days. "
                           "last day: only the most recent news-day.")
min_articles = c2.slider("Min articles", 1, 50, 5,
                         help="Hide stocks with fewer than this many total articles. "
                              "Higher = only well-covered names, more reliable signal.")
min_sources = c3.slider("Min sources/day", 1.0, 5.0, 1.0, 0.5,
                        help="Hide stocks whose news comes from fewer distinct sources per day. "
                             "Higher = only widely-reported stocks, less noise.")  # coverage filter
n_show = c4.slider("Show per list", 4, 100, 20,
                   help="How many stocks to display in each of the LONG and SHORT tabs.")
search = c5.text_input("🔍 Search ticker", "",
                       help="Type a ticker (e.g. NVDA) to jump straight to its card.").strip().upper()

rank = build_ranking(method, min_articles, min_sources)
longs = rank[rank["score"] > 0]
shorts = rank[rank["score"] < 0].sort_values("score")
st.caption(f"**{len(rank)} tickers** · :green[{len(longs)} long] / :red[{len(shorts)} short]")

# search result - show one ticker's card directly if searched
if search:
    hit = rank[rank["ticker"] == search]
    if len(hit):
        st.divider()
        st.subheader(f"🔍 Search result: {search}")
        render_grid(hit, signals, articles, 1, stats)
        st.divider()
    else:
        st.warning(f"'{search}' not found in current ranking (check spelling, or lower the Min filters).")

# tabs: Long | Short | About
tab_long, tab_short, tab_about = st.tabs(["🟢 LONG", "🔴 SHORT", "ℹ️ About & methodology"])

with tab_long:
    st.header(":green[LONG — buy candidates]  (most to least recommended)")
    render_grid(longs, signals, articles, n_show, stats)

with tab_short:
    st.header(":red[SHORT — sell candidates]  (most to least recommended)")
    render_grid(shorts, signals, articles, n_show, stats)

with tab_about:
    # live headline metrics (auto from stats.json)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Backtest t-stat", t_all, help="Overall long-short t-stat. ~2.0 = statistically significant.")
    m2.metric("Sharpe", sharpe, help="Annualized Sharpe ratio of the daily long-short spread.")
    m3.metric("Hit rate", f"{hit}%" if hit != "n/a" else "n/a", help="Share of days the long-short spread was positive.")
    m4.metric("Trading days", n_days, help="Number of trading days in the backtest.")

    # glossary of card fields
    with st.expander("📖 what each field means", expanded=True):
        st.markdown(f"""
<small>
- **Signal score** — {TIP['score']}
- **Outlook** — {TIP['outlook']}
- **Total articles** — {TIP['articles']}
- **Avg sources/day** — {TIP['sources']}
- **Recent events** — {TIP['events']}
- **Data confidence** — {TIP['confidence']}
- **Chart** — white line is price; green/red bars are daily news sentiment above/below zero.
- **Why this signal?** — the actual headlines that drove the score, with source and link.
</small>
""", unsafe_allow_html=True)

    # limitations panel - numbers read from saved stats.json
    with st.expander("⚠ limitations — read before trusting any signal"):
        st.markdown(f"""
<small>
**Data.** {total_art} articles collected from 5 sources (SEC EDGAR, Finviz, StockAnalysis,
Yahoo, NASDAQ). Of these, {nonzero_art} carry non-neutral sentiment; the backtest uses
{ticker_days} ticker-days with ≥2 articles.

**How the signal is weighted.** Three layers: *source weighting* (trust full-body sources like
Yahoo over headline-only Finviz), *strength weighting* (neutral articles count near-zero),
and *confidence weighting* (days with more agreeing sources count more). The raw signal
(t-stat ≈ {t_raw}) rises to {t_all} after all three layers.

**Sentiment model errors.** The LLM occasionally misreads ambiguous or sarcastic headlines,
though far less than a small model. Every score still traces to a specific article (see "Why this signal?").

**Confidence is not statistical significance.** The card confidence reflects data volume and
consistency, not a p-value. *Example:* a ticker with few articles can still show a strong score.

**Sample size.** The backtest spans ~{n_days} trading days, overall t-stat ≈ {t_all}
(around the ~2.0 significance threshold). Encouraging, but still a short history — treat as suggestive.

**Coverage.** Heavily-covered stocks give t-stat ≈ {t_high}; thinly-covered ones ≈ {t_low}.
With the stronger LLM sentiment the signal now holds across both, not only well-covered names.

**Other caveats.** Sources expose only ~2 months back (recent days over-represented).
Returns are next-day (no look-ahead). Universe is the S&P 500 at one snapshot, plus MRVL and
SPCX added manually (both newly index-eligible in 2026); prices via Yahoo Finance cover both
NYSE and NASDAQ listings; mid-year index changes aren't tracked.

**Newly-listed stocks.** A ticker appears once it has enough articles, but its price line needs
at least two trading days to draw. *Example:* SPCX (SpaceX) began trading 12 Jun 2026 — only one
trading day so far — so it shows sentiment but no price line yet, and is far too short to backtest.

**Not investment advice.**
</small>
""", unsafe_allow_html=True)

    # methodology panel - the full experiment journey
    with st.expander("🔬 methodology — how the signal was built & tested"):
        st.markdown(f"""
<small>
**Two NLP layers.** Qwen3-4B sentiment (LLM scoring each article on a −1..+1 price-impact scale)
+ a rule-based
event classifier (8 types: earnings, guidance, M&A, capital return, executive, legal, analyst, product).

**Weighting, built in layers (each raised the backtest t-stat):**

1. *Source weighting* — full-body sources (Yahoo, StockAnalysis) get weight 3, headline-only
Finviz gets 1, EDGAR 1. Rationale: a full article carries clearer tone than a bare headline.
Effect: t-stat 0.32 → 0.60.

2. *Strength weighting* — each article weighted by |sentiment|+0.1, so neutral articles count
near-zero without being deleted. Fixes the dilution from many neutral headlines.

3. *Confidence weighting* — ticker-days backed by more agreeing sources and sharper sentiment
count more in the long-short. Rationale: 5 sources agreeing = a real event; 1 source = noise.
Raw t-stat ≈ {t_raw} rises to {t_all} with all three layers.

**Experiments run (fixed historical record — these document past tests, not the live numbers):**

- *Text cleaning of EDGAR boilerplate* — improved readability but did NOT raise t-stat; the
problem was neutral dilution, not in-text noise.
- *Same-day returns* — gave t-stat 8.66, but that is look-ahead leakage (using news that
prints after the price moved). Rejected; reverted to next-day.
- *2-day horizon, shift(-2)* — gave a NEGATIVE t-stat (≈ -1.5): the signal reverses after two
days. Classic overreaction / mean-reversion — the market over-responds on day 1, corrects on day 2.
Confirms next-day (shift -1) is the right horizon.
- *FinBERT vs Qwen3-4B (model comparison)* — ran both on the same 131k articles, same backtest.
With a plain label prompt FinBERT won (t-stat 1.30 vs 0.71); but with a numeric price-impact
prompt Qwen3 won decisively and significantly (t-stat 2.19 vs 1.41). Same model, only the prompt
changed — so prompt design mattered more than model size. Qwen3 is now the primary engine.

**Coverage experiment.** Splitting ticker-days by news coverage: heavily-covered stocks give
t-stat ≈ {t_high}; thinly-covered ones ≈ {t_low}. With FinBERT the signal lived only in
well-covered names (thin coverage was noise); the stronger Qwen3 sentiment extended it to
thinly-covered names too — a sign the model, not just the coverage, drives the edge.
</small>
""", unsafe_allow_html=True)

    # momentum thesis panel
    mom = load_momentum()
    if mom:
        with st.expander("📈 bonus thesis — news sentiment as a momentum filter"):
            mrows = ""
            for lb in ["5", "21", "63"]:
                m = mom.get(lb, {})
                mrows += (f"| {lb}-day | {m.get('alone', 0):+.2f} | {m.get('filter', 0):+.2f} | "
                          f"**{m.get('blend', 0):+.2f}** |\n")
            st.markdown(f"""
<small>
Momentum alone (buy recent winners, short recent losers) **loses** on news-covered stocks —
these are heavily-traded names prone to overreaction, so raw momentum reverses. Adding news
sentiment fixes it: filtering out longs with bad news (and shorts with good news), or blending
sentiment into the rank, turns a losing strategy into a winning one. The effect is monotone —
more sentiment, higher t-stat — across every lookback.
</small>

| Lookback | Momentum alone | + News filter | + Sentiment blend |
|---|---|---|---|
{mrows}

<small>*Best: 21-day momentum blended with sentiment (t-stat +0.87, up from −0.67 alone).
Sentiment is the filter that separates real momentum from a bubble.*</small>
""", unsafe_allow_html=True)