import certifi
import os
import sys
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# source_tiers.py lives in backend/config/, a sibling of this folder
# (backend/ingestion/) — add it to Python's import search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config")))

import feedparser
import hashlib
from typing import Optional, TypedDict
from source_tiers import get_tier

FEED_URL = "https://hnrss.org/frontpage"
SOURCE_NAME = "Hacker News"


class Article(TypedDict):
    id: str
    title: str
    link: str
    published: Optional[str]
    summary: str
    source_name: str
    source_tier: str
    category: Optional[str]
    confidence: Optional[float]


def make_id(link: str) -> str:
    # turns the URL into a short fixed length id, so every article has a stable unique key
    return hashlib.sha256(link.encode()).hexdigest()[:16]


def build_article(entry: feedparser.FeedParserDict) -> Article:
    return {
        "id": make_id(entry.link),
        "title": entry.title,
        "link": entry.link,
        "published": entry.get("published"),
        "summary": entry.get("summary", ""),
        "source_name": SOURCE_NAME,
        # tier comes from the article's OWN url, not the feed's: HN is the
        # aggregator, but the linked domain is the actual source being judged
        "source_tier": get_tier(entry.link),
        "category": None,      # filled in later by classification layer
        "confidence": None,    # filled in later by confidence system
    }


if __name__ == "__main__":
    feed = feedparser.parse(FEED_URL)
    articles = [build_article(e) for e in feed.entries[:5]]

    for a in articles:
        print(a)
        print()