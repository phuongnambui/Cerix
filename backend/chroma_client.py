# chroma_client.py

import chromadb
from chromadb import Collection
from dotenv import load_dotenv
import os

load_dotenv()

# anchored to this file's own folder, not "./chroma_data", so the DB path
# is the same no matter what directory a script is run from
DEFAULT_CHROMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data")
CHROMA_PATH = os.getenv("CHROMA_PATH", DEFAULT_CHROMA_PATH)

client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection() -> Collection:
    return client.get_or_create_collection(
        name="articles",
        # cosine distance is bounded 0-2, so "1 - distance" gives a clean
        # 0-1 similarity score for the dedup threshold in find_candidates.py
        metadata={"description": "Ingested tech news articles", "hnsw:space": "cosine"},
    )


if __name__ == "__main__":
    print(get_collection().count())