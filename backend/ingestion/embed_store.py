import sys
import os
import re

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

# hnrss.org's "summary" is just RSS plumbing (article link, comments link,
# points, comment count), never real article content — these lines match
# that boilerplate so it can be stripped before embedding
BOILERPLATE_LINE = re.compile(r"^\s*(Article URL|Comments URL|Points|# Comments):.*$", re.MULTILINE)


def embed_text(text: str) -> list[float]:
    # turns text into a list of numbers (a vector) that captures its meaning
    return model.encode(text).tolist()


def build_document(article: Article) -> str:
    # embedding raw HN boilerplate drags every article's vector toward
    # "generic HN post shape" and masks real similarity between duplicate
    # stories, so strip HTML tags and the known boilerplate lines first —
    # for HN articles this often leaves nothing, so we fall back to title only
    text = re.sub(r"<[^>]+>", " ", article["summary"])
    text = BOILERPLATE_LINE.sub("", text)
    text = " ".join(text.split())
    return f"{article['title']} {text}".strip()


def store_article(
    article: Article,
    document: str,
    embedding: list[float],
    extra_metadata: dict | None = None,
) -> None:
    # single-article store that reuses an embedding the caller already computed
    # (ingest.py embeds for dedup first — re-embedding here would double the
    # model work) and lets the caller attach extra fields like classification
    collection = get_collection()

    metadata = {
        "title": article["title"],
        "link": article["link"],
        "published": article["published"] or "",
        "source_name": article["source_name"],
        "source_tier": article["source_tier"],
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    collection.add(
        ids=[article["id"]],
        embeddings=[embedding],
        documents=[document],
        metadatas=[metadata],
    )


def store_articles(articles: list[Article]) -> None:
    collection = get_collection()

    ids = [a["id"] for a in articles]
    documents = [build_document(a) for a in articles]
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