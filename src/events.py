# 1- events.py
"""
events.py
tags each merged article with event types (rule-based keyword matcher).
multi-label: an article can carry several event tags.
"""

import json

# 1- config
IN = "raw_data/merged.jsonl"  # unified table
OUT = "raw_data/events.jsonl"  # per-article event tags

# 2- taxonomy
RULES = {
    "earnings": ["earnings", "quarterly results", "q1", "q2", "q3", "q4", "eps", "revenue", "beat", "miss"],
    "guidance": ["guidance", "outlook", "forecast", "raised", "lowered", "cut estimate"],
    "m_and_a": ["acquire", "acquisition", "merger", "buyout", "takeover", "deal to buy"],
    "capital_return": ["dividend", "buyback", "repurchase", "stock split"],
    "executive": ["ceo", "cfo", "resign", "appoint", "step down", "successor", "names new"],
    "legal_reg": ["lawsuit", "settlement", "investigation", "sec ", "fine", "regulator", "antitrust"],
    "analyst": ["upgrade", "downgrade", "price target", "initiated", "overweight", "underweight"],
    "product": ["launch", "unveil", "release", "new product", "partnership"],
}

# 3- tag one article
def tag(text):
    """
    returns the list of event types whose keywords appear in the text.
    """
    low = text.lower()
    return [ev for ev, kws in RULES.items() if any(k in low for k in kws)]

# final- run
def main():
    n = 0
    counts = {ev: 0 for ev in RULES}
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for line in open(IN, encoding="utf-8"):
            rec = json.loads(line)
            tags = tag(rec["text"])
            out = {"ticker": rec["ticker"], "date": rec["date"], "source": rec["source"],
                   "title": rec["title"], "events": tags}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
            for t in tags:
                counts[t] += 1
            n += 1
    print(f"tagged {n} articles -> {OUT}")
    for ev, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {ev}: {c}")

if __name__ == "__main__":
    main()