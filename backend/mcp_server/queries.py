import json
import os
import sys

# chroma_client.py lives in backend/, metadata.py in backend/ingestion/ —
# add both to the import search path (same pattern as the ingestion modules)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ingestion")))

from chroma_client import get_collection
from metadata import make_id

# NOTE: deliberately no MCP imports here. This is a plain query layer: testable
# without an MCP client, and reusable behind a REST endpoint later. The MCP
# server will be a thin wrapper that exposes these functions as tools.


def _public_view(metadata: dict) -> dict:
    # the shape external callers get — internal plumbing (thread_id, reasoning,
    # embeddings, source_tier bookkeeping) stays internal
    return {
        "title": metadata["title"],
        "url": metadata["link"],
        # stored as a JSON string (Chroma metadata can't hold lists) —
        # parse it back into a real list at the boundary
        "categories": json.loads(metadata.get("categories", "[]")),
        "score": metadata.get("score", 0),
        "confidence_state": metadata.get("confidence_state", "rumored"),
    }


def get_top_stories(
    category: str | None = None,
    min_score: int | None = None,
    limit: int = 10,
) -> list[dict]:
    collection = get_collection()

    # the score filter CAN be pushed down into Chroma ($gte works on int
    # metadata). The category filter can't — the slug lives inside a JSON
    # string and Chroma has no substring operator for metadata — so that
    # filter happens in Python after the fetch.
    where = {"score": {"$gte": min_score}} if min_score is not None else None
    result = collection.get(where=where, include=["metadatas"])

    stories = [_public_view(m) for m in result["metadatas"]]

    if category is not None:
        stories = [s for s in stories if category in s["categories"]]

    stories.sort(key=lambda s: s["score"], reverse=True)
    return stories[:limit]


def get_story_confidence(url: str) -> dict | None:
    collection = get_collection()

    # article ids are sha256(link)[:16] (metadata.make_id) — the same trick
    # ingest.py uses for its re-fetch guard — so a URL lookup is a direct id
    # get, no metadata scan needed
    result = collection.get(ids=[make_id(url)], include=["metadatas"])

    if result["ids"]:
        metadata = result["metadatas"][0]
    else:
        # not stored under its own id — but the URL may have arrived as a
        # duplicate and been merged into another article's source_urls
        metadata = None
        everything = collection.get(include=["metadatas"])
        for m in everything["metadatas"]:
            if url in json.loads(m.get("source_urls", "[]")):
                metadata = m
                break
        if metadata is None:
            return None  # Cerix has genuinely never seen this URL

    view = _public_view(metadata)
    view["source_count"] = metadata.get("source_count", 1)
    return view


if __name__ == "__main__":
    print("=== top 5 stories, no filters ===")
    top = get_top_stories(limit=5)
    for s in top:
        print(f"  {s['score']} {s['confidence_state']:12} {s['categories']} {s['title'][:55]}")

    print("\n=== insight stories, min_score=4 ===")
    for s in get_top_stories(category="insight", min_score=4, limit=5):
        print(f"  {s['score']} {s['confidence_state']:12} {s['categories']} {s['title'][:55]}")

    print("\n=== confidence lookup for a known URL ===")
    known_url = top[0]["url"]
    print(f"  looking up: {known_url}")
    print(f"  {get_story_confidence(known_url)}")

    print("\n=== confidence lookup for an unknown URL ===")
    print(f"  {get_story_confidence('https://never-seen-this.example.com/story')}")
