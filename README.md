# News-Driven Equity Signals - S&P 500

**Live app:** https://esther-news-signals.streamlit.app/
**Author:** Esther Kadosh - Course 55724 (Data Science Practicum, Prof. Ronen Feldman, HUJI) - August 2026

An end-to-end NLP pipeline that scrapes financial news for the whole S&P 500, scores each
article's sentiment with an LLM (Qwen3-4B), tags event types, aggregates to a per-ticker-day
signal, and backtests a next-day long-short strategy. Results are served through a live
Streamlit dashboard.

---

## Key findings

- **Final signal is statistically significant:** t-stat ≈ 2.2, Sharpe ≈ 2.8, hit rate ≈ 58%
  over ~150 trading days (131k articles, Jan 2024 – Jul 2026).
- **Weighting in layers** each raised the t-stat: raw mean → + source/strength weighting →
  + confidence weighting.
- **Prompt matters more than model size:** on the same 131k articles, a *plain-label* prompt made
  FinBERT win (1.30 vs 0.71), but a *numeric price-impact* prompt made Qwen3 win decisively and
  significantly (2.19 vs 1.41). Same model — only the prompt changed. Qwen3 is now the primary engine.
- **Coverage:** the signal is strongest on well-covered names; with the stronger LLM sentiment it
  also holds on thinly-covered ones.
- **Honest rejected experiments:** same-day returns (t-stat 8.66 = look-ahead leakage, rejected);
  2-day horizon (negative t-stat = overreaction / mean-reversion).
- **Bonus thesis:** news sentiment used as a *momentum filter* turns a losing momentum strategy
  into a winning one (21-day blend, monotone improvement across lookbacks).

---

## Pipeline overview

```
5 scrapers ─► merge ─► clean ─► Qwen3 sentiment (Kaggle GPU) ─► events ─►
build_signals ─► backtest / coverage / momentum ─► save_stats ─► Streamlit app
```

Sources: SEC EDGAR (8-K filings), Finviz, StockAnalysis, Yahoo Finance, NASDAQ.
Two NLP layers: Qwen3-4B sentiment (−1..+1 price-impact score) + rule-based event tags (8 types).

---

## Repository structure

```
app.py                     Streamlit dashboard (reads raw_data/*)
requirements.txt           Python dependencies
src/
  sp500.py                 scrapes the S&P 500 constituent list
  scrapers/
    edgar_scraper.py       SEC EDGAR 8-K filings (deep history)
    finviz_scraper.py      Finviz headlines
    stockanalysis_scraper.py
    yahoo_scraper.py       via yfinance
    nasdaq_scraper.py      NASDAQ internal news API
  merge.py                 unify 5 sources -> merged.jsonl (dedup, mojibake fix)
  clean.py                 source-specific text cleaning -> merged_clean.jsonl
  make_qwen_full.py        build the Qwen input file for the GPU run
  qwen_to_sentiment.py     convert Qwen output into sentiment.jsonl (primary engine)
  sentiment.py             FinBERT sentiment (baseline / comparison)
  events.py                rule-based event classifier -> events.jsonl
  build_signals.py         per-ticker-day signal with source/strength/confidence weighting
  backtest.py              next-day long-short backtest (t-stat, Sharpe, hit)
  coverage_test.py         weighting progression + high/low coverage split
  source_test.py           per-source diagnostic backtest
  compare_models.py        FinBERT vs Qwen head-to-head on the same articles
  momentum.py              momentum + news-filter thesis
  save_stats.py            writes raw_data/stats.json for the app (t-stat, Sharpe, hit...)
  save_momentum.py         writes raw_data/momentum.json for the app
  slim_merged.py           lightweight merged file (links only) for deployment
  explain.py               top driving headlines behind a ticker-day (used by the app)
```

`raw_data/` holds the data and is **not** committed except the small files the deployed app
needs (`signals.csv`, `sentiment.jsonl`, `events.jsonl`, `merged_slim.jsonl`, `stats.json`,
`momentum.json`). Raw scraped folders and the full `merged.jsonl` are gitignored.

---

## Setup

Requires Python 3.12 (Anaconda recommended).

```bash
conda create -n news-signals python=3.12 -y
conda activate news-signals
pip install -r requirements.txt
```

No API keys are required — all five sources are public/free (SEC EDGAR asks for a
descriptive User-Agent, already set in `edgar_scraper.py`). The Qwen3 step runs on a free
Kaggle GPU (see below); no paid API is used.

---

## Run the full pipeline end-to-end

From the project root, with the `news-signals` environment active:

```bash
# 1- scrape all five sources (incremental & resumable)
python src/scrapers/edgar_scraper.py
python src/scrapers/finviz_scraper.py
python src/scrapers/stockanalysis_scraper.py
python src/scrapers/yahoo_scraper.py
python src/scrapers/nasdaq_scraper.py

# 2- merge + clean the text
python src/merge.py
python src/clean.py

# 3- sentiment (LLM) — see the Kaggle step below, then:
python src/qwen_to_sentiment.py     # turns the Qwen output into sentiment.jsonl

# 4- events + signal + slim file for the app
python src/events.py
python src/build_signals.py
python src/slim_merged.py

# 5- stats the app reads
python src/save_stats.py
python src/save_momentum.py
```

To reproduce the analysis figures / numbers:

```bash
python src/backtest.py          # headline t-stat, Sharpe, hit rate
python src/coverage_test.py     # weighting progression + coverage split
python src/source_test.py       # per-source diagnostic
python src/compare_models.py    # FinBERT vs Qwen (needs both sentiment files)
python src/momentum.py          # momentum + news-filter thesis
```

*(A quick FinBERT-only run is possible without a GPU by using `python src/sentiment.py`
in place of the Qwen step; Qwen is the primary engine and gives the significant result.)*

---

## Qwen3 sentiment on Kaggle (GPU step)

Local inference needs a GPU with ≥ ~8GB VRAM; a typical laptop GPU (2GB) cannot run Qwen3.
The sentiment step therefore runs on a free Kaggle T4 (16GB, 30 GPU-hrs/week):

1. Build the input file locally: `python src/make_qwen_full.py`
   → creates `raw_data/qwen_input_full.jsonl` (all articles).
2. On Kaggle: upload that file as a Dataset (e.g. `news-signals-full`).
3. In a Kaggle Notebook: set **Accelerator = GPU T4**, add the dataset as input, and run the
   cells that (a) load `Qwen/Qwen3-4B-Instruct-2507`, (b) score each article with the numeric
   price-impact prompt, (c) write `qwen_sentiment_full.jsonl` with resume/checkpointing.
4. Download `qwen_sentiment_full.jsonl` into `raw_data/`.
5. Back locally: `python src/qwen_to_sentiment.py` converts it into `sentiment.jsonl`
   (the FinBERT file is backed up to `sentiment_finbert.jsonl` for comparison).

The Qwen prompt asks for a single number in −1.0..+1.0 ("how will this news affect the stock's
price"), which outperformed a plain positive/negative/neutral label.

---

## Refresh the data and update the live app

The app is a snapshot; to refresh it on a ~3-day cadence:

```bash
# 1- pull new articles + prepare the Qwen input (does NOT overwrite Qwen sentiment)
python src/scrapers/edgar_scraper.py
python src/scrapers/finviz_scraper.py
python src/scrapers/stockanalysis_scraper.py
python src/scrapers/yahoo_scraper.py
python src/scrapers/nasdaq_scraper.py
python src/merge.py
python src/clean.py
python src/make_qwen_full.py

# 2- run Qwen on Kaggle (see the section above), download qwen_sentiment_full.jsonl to raw_data/

# 3- rebuild everything with the new sentiment
python src/qwen_to_sentiment.py
python src/events.py
python src/build_signals.py
python src/save_stats.py
python src/save_momentum.py
python src/slim_merged.py

# 4- deploy: push to GitHub — Streamlit Cloud redeploys automatically
git add .
git commit -m "data refresh"
git push
```

The app text is fully data-driven: every current-state number (t-stat, Sharpe, hit rate,
coverage, momentum, article counts) is read live from `stats.json` / `momentum.json`, so a
refresh + push updates the dashboard with **no code edits**. (The historical experiment numbers —
the leakage test, the model comparison — are a fixed record and intentionally stay constant.)

Keeping a long run alive on Windows: `powercfg /change standby-timeout-ac 0` (and the `-dc`,
`hibernate-*` variants) prevents sleep during multi-hour scrapes.

---

## Run the app locally

```bash
streamlit run app.py
```

---

## Limitations

Short history (~150 trading days) — significant but still a small sample. The LLM can misread
sarcasm. Sources expose only ~2 months of history (EDGAR reaches back further). Universe is the
S&P 500 at one snapshot plus MRVL and SPCX (added manually); mid-year index changes aren't
tracked. **Not investment advice — a research project.**
