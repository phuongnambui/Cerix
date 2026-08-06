import json
import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

# anchored to this file's folder, same pattern as chroma_client.py, so the
# config resolves no matter what directory a script is run from
TIERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_tiers.json")

Tier = Literal["tier_a", "tier_b", "tier_c"]

# any hostname ending in these is tier_a without needing an allowlist entry —
# official/government sources, too many domains to enumerate one by one
TIER_A_SUFFIXES = (".gov", ".europa.eu")


@lru_cache(maxsize=1)
def load_tiers() -> dict[str, list[str]]:
    # lru_cache(maxsize=1) on a zero-arg function = "run once, remember the
    # result": the file is read on the first call, every later call returns
    # the cached dict. get_tier() runs per-article during ingest, so without
    # this we'd hit the disk for every single article.
    with open(TIERS_PATH) as f:
        return json.load(f)


def _hostname(url: str) -> str:
    # urlparse only recognizes the hostname when a scheme ("https://") is
    # present — "blog.google/foo" without one gets parsed entirely as a path.
    # Feed URLs sometimes arrive schemeless, so normalize first.
    if "//" not in url:
        url = "https://" + url
    return (urlparse(url).hostname or "").lower()


def _matches(hostname: str, domain: str) -> bool:
    # label-boundary matching: the hostname either IS the listed domain, or is
    # a subdomain of it (ends with ".<domain>"). The leading dot is what makes
    # this safe — "eng.uber.com".endswith(".uber.com") is True, but
    # "notuber.com".endswith(".uber.com") is False. A naive substring check
    # ("uber.com" in hostname) would accept both.
    return hostname == domain or hostname.endswith("." + domain)


def get_tier(url: str) -> Tier:
    hostname = _hostname(url)
    if not hostname:
        return "tier_c"

    # suffix rules first: official sources outrank everything and shouldn't
    # depend on someone remembering to list every agency domain
    if any(_matches(hostname, suffix.lstrip(".")) or hostname.endswith(suffix)
           for suffix in TIER_A_SUFFIXES):
        return "tier_a"

    tiers = load_tiers()
    if any(_matches(hostname, d) for d in tiers["tier_a"]):
        return "tier_a"
    if any(_matches(hostname, d) for d in tiers["tier_b"]):
        return "tier_b"
    return "tier_c"


if __name__ == "__main__":
    cases = [
        # (url, expected tier, what it proves)
        ("https://openai.com/blog/gpt-5", "tier_a", "exact tier_a match with path"),
        ("https://techcrunch.com/2026/08/06/some-story/?utm_source=hn", "tier_b", "tier_b with path + query string"),
        ("https://myrandomblog.dev/post/1", "tier_c", "unlisted domain falls to tier_c"),
        ("https://www.nasa.gov/news/artemis-update", "tier_a", ".gov suffix rule"),
        ("https://ec.europa.eu/commission/press", "tier_a", ".europa.eu suffix rule"),
        ("blog.google/products/gemini", "tier_a", "schemeless URL still matches"),
        ("https://eng.uber.com/some-post", "tier_c", "subdomain of unlisted domain -> tier_c"),
        ("https://research.openai.com/paper", "tier_a", "subdomain of listed domain inherits tier"),
        ("https://notopenai.com/fake", "tier_c", "substring lookalike does NOT match tier_a"),
        ("https://example.com/why-openai.com-matters", "tier_c", "listed domain in the PATH does not match"),
    ]
    failures = 0
    for url, expected, proves in cases:
        got = get_tier(url)
        status = "ok " if got == expected else "FAIL"
        if got != expected:
            failures += 1
        print(f"{status} {got:7} (expected {expected})  {proves}")
    print(f"\n{len(cases) - failures}/{len(cases)} passed")
