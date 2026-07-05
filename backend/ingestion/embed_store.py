import sys
import os

# chroma_client.py lives in backend/, one folder up from here (backend/ingestion/),
# so it isn't found automatically, add that folder to Python's import search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sentence_transformers import SentenceTransformer
from metadata import Article, build_article
from chroma_client import get_collection
import feedparser
import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

FEED_URL = "https://hnrss.org/frontpage"

model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    # turns text into a list of numbers (a vector) that captures its meaning
    return model.encode(text).tolist()


def store_articles(articles: list[Article]) -> None:
    collection = get_collection()

    ids = [a["id"] for a in articles]
    documents = [f"{a['title']} {a['summary']}" for a in articles]
    embeddings = [embed_text(doc) for doc in documents]
    metadatas = [
        {
            "title": a["title"],
            "link": a["link"],
            "published": a["published"] or "",
            "source_name": a["source_name"],
            "source_tier": a["source_tier"],
        }
        for a in articles
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    print(f"Stored {len(ids)} articles in Chroma.")


if __name__ == "__main__":
    feed = feedparser.parse(FEED_URL)
    articles = [build_article(e) for e in feed.entries[:5]]
    store_articles(articles)