import sys
import os
from typing import TypedDict

# chroma_client.py lives in backend/, one folder up from here (backend/ingestion/),
# so it isn't found automatically — add that folder to Python's import search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chroma_client import get_collection
from feedparser import FeedParserDict
from metadata import build_article
from embed_store import embed_text, build_document

# 0.85 missed a genuine paraphrase of the same story (scored 0.790), so this
# is loosened to 0.75 — Pass 2 (entity verification) catches the false
# positives that a looser threshold lets through
SIMILARITY_THRESHOLD = 0.75


class Candidate(TypedDict):
    id: str
    similarity: float
    title: str


def find_candidates(
    new_embedding: list[float], new_id: str, n_results: int = 5
) -> list[Candidate]:
    collection = get_collection()

    results = collection.query(
        query_embeddings=[new_embedding],
        n_results=n_results,
    )

    ids = results["ids"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    candidates = []
    for match_id, distance, metadata in zip(ids, distances, metadatas):
        # the article's own embedding is already stored, so it always matches
        # itself first, skip it or every article would flag as its own duplicate
        if match_id == new_id:
            continue

        similarity = 1 - distance
        if similarity >= SIMILARITY_THRESHOLD:
            candidates.append(
                {
                    "id": match_id,
                    "similarity": similarity,
                    "title": metadata["title"],
                }
            )

    return candidates


if __name__ == "__main__":
    # positive-case check: does a reworded near-duplicate of a REAL stored
    # article actually get flagged? pull whatever's actually in Chroma right
    # now rather than hardcoding a story, since the feed is live and changes
    # between runs
    collection = get_collection()
    original = collection.get(limit=1, include=["metadatas"])
    original_title = original["metadatas"][0]["title"]

    # build_article() expects a feedparser entry, so fake one for a different
    # "source" covering the same story, same title, a reworded one-line summary
    fake_entry = FeedParserDict(
        {
            "title": original_title,
            "link": "https://example.com/near-duplicate-of-stored-article",
            "published": "Sun, 05 Jul 2026 12:00:00 +0000",
            "summary": f"A different outlet's report on: {original_title}",
        }
    )
    near_duplicate = build_article(fake_entry)
    near_duplicate_embedding = embed_text(build_document(near_duplicate))

    results = find_candidates(near_duplicate_embedding, near_duplicate["id"])

    print(f"Original stored article: {original_title}")
    print(f"New article: {near_duplicate['title']}")
    print(f"Candidates found: {len(results)}")
    for r in results:
        print(f"  {r['similarity']:.3f}  {r['title']}")
