# News-Driven Equity Signals · S&P 500

Live app: https://esther-news-signals.streamlit.app/

An NLP pipeline that scrapes financial news for the S&P 500, scores sentiment with
an LLM (Qwen3-4B), tags events, and backtests a next-day long-short signal.

## Findings
- Final signal: **t-stat 2.17, Sharpe 2.78** over 153 trading days (statistically significant).
- Weighting in layers: raw 1.36 → source/strength 1.99 → confidence 2.17.
- **Prompt matters more than model size:** with a numeric price-impact prompt, Qwen3 (t-stat 2.19)
  beat FinBERT (1.41); with a plain-label prompt, FinBERT won. Same model, different prompt.
- Honest rejected experiments: same-day returns (look-ahead leakage), 2-day horizon (mean-reversion).

## Pipeline
5 sources (SEC EDGAR, Finviz, StockAnalysis, Yahoo, NASDAQ) → merge → clean →
Qwen3 sentiment + rule-based events → confidence-weighted signal → backtest → Streamlit dashboard.

## Run locally