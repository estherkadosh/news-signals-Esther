# date_check.py
import glob, json, os
from collections import Counter

for folder in glob.glob("raw_data/*/"):
    name = os.path.basename(folder.rstrip("/"))
    months = Counter()
    for f in glob.glob(folder + "*.jsonl"):
        for line in open(f, encoding="utf-8"):
            d = json.loads(line).get("date", "")
            if d:
                months[d[:7]] += 1
    print(name, dict(sorted(months.items())))