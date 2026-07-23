# 1- merge.py
"""
merge.py
merges all five source folders into one unified jsonl table.
fields: ticker, date, source, title, text, link. dedupes on (ticker, title).
"""

import json
import os
import glob

# 1- config
SOURCES = {
    "edgar": "raw_data/edgar_filings",
    "finviz": "raw_data/finviz_news",
    "stockanalysis": "raw_data/stockanalysis_news",
    "yahoo": "raw_data/yahoo_news",
    "nasdaq": "raw_data/nasdaq_news",
    "gdelt": "raw_data/gdelt_news",
}
OUT = "raw_data/merged.jsonl"  # unified table

# 2- build text field
def build_text(rec):
    """
    1-edgar carries a full body; others carry title (+ summary).
    2-returns title + summary/body as one text blob for analysis.
    """
    title = rec.get("title", "").strip()
    extra = rec.get("body", "") or rec.get("summary", "")
    return (title + " " + extra).strip()

# 3- read one source
def read_source(name, folder):
    """
    1-reads every ticker jsonl in the folder.
    2-yields a unified record per line.
    """
    for path in glob.glob(os.path.join(folder, "*.jsonl")):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = build_text(rec)
            for bad, good in [("â€™", "'"), ("â€œ", '"'), ("â€\x9d", '"'), ("â€“", "-"), ("â€”", "-"), ("Â", "")]:
                text = text.replace(bad, good)  # fix common mojibake from edgar
            yield {
                "ticker": rec.get("ticker", ""),
                "date": rec.get("date", ""),
                "source": name,
                "title": rec.get("title", ""),
                "text": text,
                "link": rec.get("link", rec.get("url", "")),
            }

# final- run
def main():
    seen = set()  # dedup key per ticker
    kept = 0
    dropped = 0
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for name, folder in SOURCES.items():
            for rec in read_source(name, folder):
                key = (rec["ticker"], rec["title"] or rec["text"][:100])  # use text when no title
                if key in seen:  # skip duplicate for same ticker
                    dropped += 1
                    continue
                seen.add(key)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1
            print(f"  {name} done")

    print(f"kept {kept}, dropped {dropped} dups -> {OUT}")

if __name__ == "__main__":
    main()