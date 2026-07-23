# gdelt_probe.py
# one-off: show raw status per year request, no silent failures.
import requests
import time

API = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"}

for year in [2024, 2025, 2026]:
    params = {
        "query": '"Apple Inc." (stock OR shares OR earnings OR revenue) sourcelang:english',
        "mode": "artlist",
        "maxrecords": 250,
        "startdatetime": f"{year}0101000000",
        "enddatetime": f"{year}1231235959",
        "format": "json",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=60)
    print(year, "status:", r.status_code, "len:", len(r.text))
    print("  head:", r.text[:200].replace("\n", " "))
    time.sleep(10)  # be extra polite while probing