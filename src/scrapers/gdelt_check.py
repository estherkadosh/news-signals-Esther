# gdelt_check.py
# one-off: see what gdelt returns for one company over a long window.
import requests
import json

url = "https://api.gdeltproject.org/api/v2/doc/doc"
params = {
    "query": '"Apple Inc" sourcelang:english',
    "mode": "artlist",
    "maxrecords": 10,
    "startdatetime": "20240101000000",
    "enddatetime": "20240201000000",
    "format": "json",
}
r = requests.get(url, params=params, timeout=30)
print("status:", r.status_code)
print(json.dumps(r.json(), indent=2)[:1500])