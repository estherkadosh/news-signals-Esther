# 1- sp500.py
"""
sp500.py
fetches the current s&p 500 ticker list from wikipedia and caches it to disk.
other scrapers import get_tickers() to loop over the universe.
"""

import os
import json
import pandas as pd

# 1- config
CACHE = "raw_data/sp500_tickers.json"  # cached ticker list

# 2- get tickers
def get_tickers():
    """
    1-returns the cached s&p 500 ticker list if it exists.
    2-otherwise scrapes wikipedia, caches, and returns it.
    """
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))

    import requests
    from io import StringIO
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}  # wikipedia blocks anonymous requests
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    tables = pd.read_html(StringIO(r.text))  # first table holds the constituents
    tickers = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()  # BRK.B -> BRK-B

    os.makedirs("raw_data", exist_ok=True)
    json.dump(tickers, open(CACHE, "w", encoding="utf-8"))
    return tickers

# final- run
def main():
    tickers = get_tickers()
    print(f"{len(tickers)} tickers, first 5: {tickers[:5]}")

if __name__ == "__main__":
    main()