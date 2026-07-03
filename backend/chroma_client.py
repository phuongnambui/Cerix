# chroma_client.py

import chromadb
from dotenv import load_dotenv
import os

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_data")

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(name="stories", metadata={"description": "A collection of short stories"})

print(collection.count())