# 1- make_qwen_full.py
"""
make_qwen_full.py
builds the full qwen input: every article, not just covered ticker-days.
for the final run where qwen replaces finbert across the whole dataset.
"""

import json

# 1- config
MERGED = "raw_data/merged_clean.jsonl"
OUT = "raw_data/qwen_input_full.jsonl"

# final- run
def main():
    n = 0
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for line in open(MERGED, encoding="utf-8"):
            rec = json.loads(line)
            out = {"ticker": rec["ticker"], "date": rec["date"], "source": rec["source"],
                   "title": rec["title"], "text": rec["text"][:600]}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} articles -> {OUT}")

if __name__ == "__main__":
    main()