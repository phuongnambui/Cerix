import sys
import os
from typing import TypedDict

# chroma_client.py lives in backend/, one folder up from here (backend/ingestion/),
# so it isn't found automatically — add that folder to Python's import search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chroma_client import get_collection

SIMILARITY_THRESHOLD = 0.85


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
