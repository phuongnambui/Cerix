import certifi
import os
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import feedparser
import hashlib

FEED_URL = "https://hnrss.org/frontpage"
SOURCE_NAME = "Hacker News"
SOURCE_TIER = "B"  # placeholder until tier logic is built


def make_id(link: str) -> str:
    # turns the URL into a short fixed length id, so every article has a stable unique key
    return hashlib.sha256(link.encode()).hexdigest()[:16]


def build_article(entry) -> dict:
    return {
        "id": make_id(entry.link),
        "title": entry.title,
        "link": entry.link,
        "published": entry.get("published"),
        "summary": entry.get("summary", ""),
        "source_name": SOURCE_NAME,
        "source_tier": SOURCE_TIER,
        "category": None,      # filled in later by classification layer
        "confidence": None,    # filled in later by confidence system
    }


if __name__ == "__main__":
    feed = feedparser.parse(FEED_URL)
    articles = [build_article(e) for e in feed.entries[:5]]

    for a in articles:
        print(a)
        print()