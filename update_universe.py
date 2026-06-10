# update_universe.py
# fetches a fresh s&p 500 list, compares to ours, prints what's missing.
import json
import requests
import pandas as pd
from io import StringIO

CACHE = "raw_data/sp500_tickers.json"
old = json.load(open(CACHE, encoding="utf-8"))

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
headers = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}
r = requests.get(url, headers=headers)
r.raise_for_status()
fresh = pd.read_html(StringIO(r.text))[0]["Symbol"].str.replace(".", "-", regex=False).tolist()

missing = [t for t in fresh if t not in old]
print("old:", len(old), "fresh:", len(fresh))
print("missing count:", len(missing))
print("missing:", missing)

# add MRVL explicitly in case it's not even in wikipedia's table yet
extra = ["MRVL"]
to_add = sorted(set(missing + [e for e in extra if e not in old]))
print("to add:", to_add)

# save updated list
merged = old + [t for t in to_add if t not in old]
json.dump(merged, open(CACHE, "w", encoding="utf-8"))
print("new total:", len(merged))