# 1- clean.py
"""
clean.py
source-specific text cleaning, applied after merge, before sentiment.
keeps every article - only strips in-text noise. writes merged_clean.jsonl.
"""

import json
import re

# 1- config
IN = "raw_data/merged.jsonl"
OUT = "raw_data/merged_clean.jsonl"

# 2- edgar cleaner
def clean_edgar(text):
    """
    1-drops xbrl id blobs, table pipes, and lines without real words.
    2-keeps only sentence-like lines with letters and spaces.
    """
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s == "|":
            continue
        if re.match(r"^[\d\s|.\-]+$", s):  # pure numbers / pipes / dashes
            continue
        if "false000" in s or re.match(r"^\d{8,}", s):  # xbrl id blob
            continue
        s = s.replace("|", " ").strip()  # drop leftover table pipes
        if len(s) >= 3 and re.search(r"[a-zA-Z]", s):  # must contain letters
            lines.append(s)
    return "\n".join(lines)

# 3- stockanalysis cleaner
def clean_sa(text):
    """
    removes the fixed wire-service dateline prefix.
    """
    return re.sub(r"^[A-Z\s,.]+--\(BUSINESS WIRE\)-+\$?\S*", "", text).strip()

# 4- route by source
def clean(rec):
    """
    applies the right cleaner per source; others pass through unchanged.
    """
    text = rec.get("text", "")
    src = rec.get("source", "")
    if src == "edgar":
        return clean_edgar(text)
    if src == "stockanalysis":
        return clean_sa(text)
    return text

# final- run
def main():
    n = 0
    with open(OUT, "w", encoding="utf-8", buffering=1) as f:
        for line in open(IN, encoding="utf-8"):
            rec = json.loads(line)
            rec["text"] = clean(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"cleaned {n} articles -> {OUT}")

if __name__ == "__main__":
    main()