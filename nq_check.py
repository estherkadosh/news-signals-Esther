# nq_check.py
# one-off: check nasdaq's internal news api for a ticker.
import requests
import json

url = "https://api.nasdaq.com/api/news/topic/articlebysymbol?q=AAPL|stocks&offset=0&limit=10"
headers = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}
r = requests.get(url, headers=headers, timeout=30)
print("status:", r.status_code)
print(json.dumps(r.json(), indent=2, default=str)[:1500])