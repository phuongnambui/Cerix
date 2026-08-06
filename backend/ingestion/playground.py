import sys
import os

# chroma_client.py lives in backend/, one folder up from here (backend/ingestion/),
# so it isn't found automatically — add that folder to Python's import search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sentence_transformers import util
from chroma_client import get_collection
from embed_store import embed_text

# scratch space for trying different headline/summary pairs and seeing how
# similar MiniLM thinks they are — edit the strings below and rerun


def compare(text_a: str, text_b: str) -> None:
    # pure text vs text, no Chroma involved — fastest way to sanity check
    # "would these two count as duplicates?" before wiring anything up
    emb_a = embed_text(text_a)
    emb_b = embed_text(text_b)
    similarity = util.cos_sim(emb_a, emb_b).item()
    print(f"sim={similarity:.3f}")
    print(f"  A: {text_a}")
    print(f"  B: {text_b}")


def compare_to_stored(text: str, n_results: int = 5) -> None:
    # embeds `text` and ranks it against everything currently in Chroma —
    # this is what proved the negative case earlier (unrelated stored
    # articles scoring low) and the positive case (a real duplicate scoring high)
    collection = get_collection()
    embedding = embed_text(text)
    results = collection.query(query_embeddings=[embedding], n_results=n_results)

    print(f"Query: {text}")
    for match_id, distance, metadata in zip(
        results["ids"][0], results["distances"][0], results["metadatas"][0]
    ):
        print(f"  sim={1 - distance:.3f}  {metadata['title']}")


if __name__ == "__main__":
    # edit these and rerun to try your own pairs
    compare(
        "US gas prices hit an average of $4 a gallon again",
        "Gas prices climb back to $4/gallon nationwide",
    )
    print()
    compare_to_stored("US gas prices hit an average of $4 a gallon again")
