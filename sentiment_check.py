# sentiment_check.py
# one-off: load finbert and score a few test sentences.
from transformers import pipeline

clf = pipeline("text-classification", model="yiyanghkust/finbert-tone")

tests = [
    "The company reported record quarterly profits, beating all estimates.",
    "Shares plunged after the firm missed earnings and cut guidance.",
    "The board will meet on Tuesday to discuss the agenda.",
]
for t in tests:
    print(clf(t)[0], t[:50])