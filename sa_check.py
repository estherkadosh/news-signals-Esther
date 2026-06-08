# checking the struction of the data from stock analysis:
# sa_check.py
# one-off: dump the first news item's html to see its structure.
from lxml import html

t = open("sa_test.html", encoding="utf-8").read()
tree = html.fromstring(t)

# the news grid items carry the grid-cols-news class
items = tree.xpath('//div[contains(@class,"grid-cols-news")]')
print("news items found:", len(items))

if items:
    from lxml import etree
    print(etree.tostring(items[0], pretty_print=True, encoding="unicode")[:2000])