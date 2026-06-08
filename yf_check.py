# yahoo finance news API is very limited, but let's see what it returns for a ticker's news:
# # yf_check.py
# one-off: see what yfinance returns for a ticker's news.
import yfinance as yf
import json

t = yf.Ticker("AAPL")
news = t.news
print("items:", len(news))
if news:
    print(json.dumps(news[0], indent=2, default=str)[:1500])  # structure of first item