# 1- sentiment.py
"""
sentiment.py
scores each merged article with finbert-tone: splits to sentences,
scores each, and saves a per-article mean polarity (+1 pos, -1 neg, 0 neu).
resumable: skips articles already scored.
"""

import json
import os
import nltk
from transformers import pipeline

# 1- config
# IN = "raw_data/merged.jsonl"  # unified table
IN = "raw_data/merged_clean.jsonl"  # cleaned table
OUT = "raw_data/sentiment.jsonl"  # per-article scores
MODEL = "yiyanghkust/finbert-tone"
POLARITY = {"Positive": 1, "Negative": -1, "Neutral": 0}

# 2- setup
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
clf = pipeline("text-classification", model=MODEL, truncation=True, max_length=512)

# 3- usable sentences
def get_sentences(text):
    """
    1-splits text into sentences.
    2-keeps only real sentences (length filter drops boilerplate / table junk).
    """
    out = []
    for s in nltk.sent_tokenize(text):
        s = s.strip()
        if len(s) >= 30 and " " in s:  # skip short / non-sentence lines
            out.append(s)
    return out

# 4- score one article
def score_article(text):
    """
    1-scores every usable sentence.
    2-returns mean polarity and sentence count, or (0, 0) if none.
    """
    sents = get_sentences(text)
    if not sents:
        return 0.0, 0
    total = 0
    for r in clf(sents):
        total += POLARITY.get(r["label"], 0)
    return total / len(sents), len(sents)

# 5- already done
def done_keys():
    """
    reads existing output and returns keys already scored (for resume).
    """
    keys = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            r = json.loads(line)
            keys.add((r["ticker"], r["source"], r["title"], r["date"]))
    return keys

# final- run
def main():
    done = done_keys()
    n = 0
    with open(OUT, "a", encoding="utf-8", buffering=1) as f:  # append for resume
        for line in open(IN, encoding="utf-8"):
            rec = json.loads(line)
            key = (rec["ticker"], rec["source"], rec["title"], rec["date"])
            if key in done:  # skip already scored
                continue
            polarity, n_sents = score_article(rec["text"])
            out = {"ticker": rec["ticker"], "date": rec["date"], "source": rec["source"],
                   "title": rec["title"], "polarity": round(polarity, 4), "n_sents": n_sents}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
            if n % 500 == 0:  # progress every 500
                print(f"  scored {n}")
    print(f"done. scored {n} new articles -> {OUT}")

if __name__ == "__main__":
    main()