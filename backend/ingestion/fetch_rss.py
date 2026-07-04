import os

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import feedparser

FEED_URL = "https://hnrss.org/frontpage"

feed = feedparser.parse(FEED_URL)

print(f"Feed title: {feed.feed.get('title')}")
print(f"Number of entries: {len(feed.entries)}")
print("---")

for entry in feed.entries[:5]:
    print("Title:", entry.title)
    print("Link:", entry.link)
    print("Published:", entry.get("published"))
    print()