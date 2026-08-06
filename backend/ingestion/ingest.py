import sys
import os
import json
import hashlib

# chroma_client.py lives in backend/, and classify.py in backend/classification/ —
# neither is found automatically from here, so add both to the import search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "classification")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent")))

import feedparser
from chroma_client import get_collection
from metadata import Article, build_article, FEED_URL
from embed_store import embed_text, build_document, store_article
from find_candidates import find_candidates
from verify_duplicate import is_confirmed_duplicate
from classify import classify, CATEGORY_EMOJI
from verify import verify_article


def make_thread_id(article_id: str) -> str:
    # a thread groups every source covering one event. Derived from the FIRST
    # article's id so re-running the pipeline always produces the same
    # thread_id for the same thread (deterministic > random here)
    return hashlib.sha256(f"thread:{article_id}".encode()).hexdigest()[:16]


def merge_into_existing(existing_id: str, new_article: Article) -> None:
    """The new article is a confirmed duplicate: instead of storing it as its
    own record, fold it into the existing article's metadata as extra evidence
    (more sources covering a story = stronger importance signal later)."""
    collection = get_collection()
    existing = collection.get(ids=[existing_id], include=["metadatas"])
    metadata = existing["metadatas"][0]

    # first confirmed duplicate promotes the article into a "thread"
    if "thread_id" not in metadata:
        metadata["thread_id"] = make_thread_id(existing_id)

    # default 1, not 0: the existing article itself is already one source
    metadata["source_count"] = metadata.get("source_count", 1) + 1

    # two or more sources reporting the same event = corroborated. The
    # rumored-only guard matters twice over: it stops a later merge from
    # silently DOWNGRADING an already-confirmed article back to corroborated,
    # and it makes verification run exactly once — at the flip moment.
    previous_state = metadata.get("confidence_state", "rumored")
    if metadata["source_count"] >= 2 and previous_state == "rumored":
        metadata["confidence_state"] = "corroborated"

        # the moment of corroboration is the trigger for agent verification:
        # can this be upgraded to confirmed (first-party source that actually
        # supports the claim)? The claim = title + why we classified it that
        # way; the url is the ORIGINAL article's own link.
        claim = f"{metadata['title']}. {metadata.get('reasoning', '')}".strip()
        try:
            verdict = verify_article(metadata["link"], claim)
            if verdict.is_first_party and verdict.supports_claim:
                metadata["confidence_state"] = "confirmed"
            # not confirmed is NOT a failure — the article simply stays
            # corroborated until something better comes along
        except Exception as e:
            # same graceful degradation as classify(): a network/API error
            # must not crash the merge — corroborated is already correct
            print(f"  WARNING: verification failed for '{metadata['title']}': {e}")

    # Chroma metadata values must be str/int/float/bool — no lists — so the
    # URL list lives as a JSON string: parse on read, append, serialize on write
    source_urls = json.loads(metadata.get("source_urls", "[]"))
    if not source_urls:
        source_urls.append(metadata["link"])  # seed with the original's own URL
    source_urls.append(new_article["link"])
    metadata["source_urls"] = json.dumps(source_urls)

    # update() overwrites the metadata of an existing id in place —
    # embedding and document stay untouched
    collection.update(ids=[existing_id], metadatas=[metadata])
    print(f"  merged into existing article {existing_id} "
          f"(source_count={metadata['source_count']}, "
          f"confidence={metadata.get('confidence_state', '?')})")


def ingest_article(article: Article) -> None:
    collection = get_collection()

    # exact re-fetch guard: RSS returns the same items every run, so the same
    # URL (= same id) comes back constantly — skip before doing any model work
    if collection.get(ids=[article["id"]])["ids"]:
        print(f"  already stored, skipping: {article['title']}")
        return

    document = build_document(article)
    embedding = embed_text(document)

    # Pass 1: embedding similarity — "is anything stored ABOUT the same thing?"
    candidates = find_candidates(embedding, article["id"])

    # candidates come back nearest-first, so the first one that passes the
    # entity check is the best match — merge there and stop
    for candidate in candidates:
        stored = collection.get(ids=[candidate["id"]], include=["documents"])
        stored_document = stored["documents"][0]

        # Pass 2: entity overlap — "is it the same EVENT, not just same topic?"
        if is_confirmed_duplicate(document, stored_document):
            print(f"Duplicate confirmed (sim={candidate['similarity']:.3f}): "
                  f"{article['title']}")
            merge_into_existing(candidate["id"], article)
            return

    # no candidate survived both passes: it's genuinely new — classify it.
    # Duplicates never reach this point, which is deliberate: a merged article
    # is already tracked under the original's classification, so classifying
    # it again would spend an API call on nothing.
    try:
        result = classify(document)
        categories = result.categories
        score = result.score
        reasoning = result.reasoning
        badges = " ".join(CATEGORY_EMOJI[c] for c in categories)
        print(f"  {badges} {score} [rumored, {article['source_tier']}]  {article['title']}")
    except Exception as e:
        # graceful degradation: one failed API call (rate limit, network,
        # outage) must not kill the rest of the batch — store the article
        # unclassified so ingestion keeps moving; score=0 marks "never
        # classified" (real scores are 1-10) so a backfill pass can find these
        print(f"  WARNING: classification failed for '{article['title']}': {e}")
        categories, score, reasoning = [], 0, ""

    store_article(
        article,
        document,
        embedding,
        extra_metadata={
            # Chroma metadata can't hold lists — JSON string, same pattern
            # as source_urls in merge_into_existing()
            "categories": json.dumps(categories),
            "score": score,
            "reasoning": reasoning,
            # a brand-new article has exactly one source reporting it —
            # nothing corroborates it yet
            "confidence_state": "rumored",
        },
    )


if __name__ == "__main__":
    # full frontpage, not a slice — this is the daily-use entry point now
    feed = feedparser.parse(FEED_URL)
    print(f"Frontpage entries: {len(feed.entries)}")
    for entry in feed.entries:
        article = build_article(entry)
        print(f"Ingesting: {article['title']}")
        ingest_article(article)
