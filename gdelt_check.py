# gdelt_check.py
# one-off: see what gdelt returns for one company over a long window.
import requests
import json

# url = "https://api.gdeltproject.org/api/v2/doc/doc"
# params = {
#     "query": '"Apple Inc" sourcelang:english',
#     "mode": "artlist",
#     "maxrecords": 10,
#     "startdatetime": "20240101000000",
#     "enddatetime": "20240201000000",
#     "format": "json",
# }
# headers = {"User-Agent": "Esther Kadosh esther.kadosh@mail.huji.ac.il"}  # gdelt blocks anonymous
# r = requests.get(url, params=params, headers=headers, timeout=30)
# print("status:", r.status_code)
# print("raw:", r.text[:800])  # look before parsing


# gdelt_check.py
# one-off: minimal gdelt probe.

url = "https://api.gdeltproject.org/api/v2/doc/doc?query=apple&mode=artlist&maxrecords=5&format=json"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"}
r = requests.get(url, headers=headers, timeout=30)
print("status:", r.status_code)
print("raw:", r.text[:600])