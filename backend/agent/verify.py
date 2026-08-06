import os
import sys

# source_tiers.py lives in backend/config/, a sibling of this folder (backend/agent/)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config")))

from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic
import trafilatura

from source_tiers import get_tier

load_dotenv()

MODEL = "claude-opus-5"

# cap what we feed back to the model — articles can be huge, and verification
# only needs enough text to judge the claim, not the whole comment section
MAX_CONTENT_CHARS = 8000


class VerificationResult(BaseModel):
    # confirmed = is_first_party AND supports_claim — computed by the caller,
    # not stored here, so this model stays a pure record of what was observed
    is_first_party: bool
    supports_claim: bool
    reasoning: str


# The tool the model sees. Note the url parameter exists so the model's request
# looks normal to it — but our code NEVER honors it (see verify_article).
FETCH_TOOL = {
    "name": "fetch_article",
    "description": (
        "Fetch the full text of the article being verified. Always call this "
        "before making any verification judgment — never judge a claim from "
        "the URL or your prior knowledge alone."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the article to fetch",
            }
        },
        "required": ["url"],
    },
}

SYSTEM_PROMPT = """\
You are Cerix's source verification engine. You are given a CLAIM (a news
story's headline/summary) and the URL + tier of the source reporting it.
Your job is to fetch the article and answer two independent questions:

is_first_party — is this source the ORIGIN of the claim, not a reporter of
it? First-party means: the organization/person the claim is about speaking
for themselves (a company's own blog announcing its own product, an author's
own post about their own work, a paper by its own researchers, an official
filing). Third-party means: journalists, analysts, or researchers writing
ABOUT someone else's actions — however reputable. A security firm's writeup
of a vulnerability in another company's product is third-party.

supports_claim — does the fetched article's content actually support the
claim as stated? The claim must be substantiated by the text, not just
topically related to it.

Always fetch the article first with the fetch_article tool. After reading
the content, give your verdict with brief reasoning. If the fetched content
is empty or clearly not the article, say so and answer false on both.
"""

client = anthropic.Anthropic()


def fetch_text(url: str) -> str:
    # trafilatura downloads the page and strips it to readable article text
    # (no nav bars, ads, comment threads). Raises ValueError on any failure
    # so the caller has one error type to handle.
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        raise ValueError(f"could not download {url}")
    text = trafilatura.extract(downloaded)
    if not text:
        raise ValueError(f"downloaded {url} but could not extract article text")
    return text[:MAX_CONTENT_CHARS]


def verify_article(url: str, claim: str) -> VerificationResult:
    tier = get_tier(url)
    messages = [
        {
            "role": "user",
            "content": (
                f"CLAIM: {claim}\n"
                f"SOURCE URL: {url}\n"
                f"SOURCE TIER: {tier}\n\n"
                "Verify this claim against its source."
            ),
        }
    ]

    first = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[FETCH_TOOL],
        messages=messages,
    )

    tool_use = next((b for b in first.content if b.type == "tool_use"), None)

    if tool_use is None:
        # The model decided not to fetch. Without fetched evidence there IS no
        # verification — so fail closed with a deterministic result instead of
        # asking the model to justify an evidence-free verdict. An unverified
        # article simply stays rumored/corroborated; nothing is lost.
        return VerificationResult(
            is_first_party=False,
            supports_claim=False,
            reasoning="unverified: model did not fetch the article, no evidence to judge",
        )

    # ── security boundary ──────────────────────────────────────────────────
    # We fetch the pre-approved url from OUR function parameter, never the url
    # in the model's tool_use input. The model's input is untrusted output: if
    # the article text (or anything else in context) manipulated the model into
    # requesting a different url, honoring it would turn this verifier into an
    # attacker-steerable HTTP client (SSRF / data exfiltration primitive).
    requested = tool_use.input.get("url")
    if requested != url:
        print(f"  WARNING: model requested '{requested}' — ignoring, fetching pre-approved url")

    try:
        content = fetch_text(url)
    except Exception as e:
        # fetches fail all the time (404, timeout, paywall, bot-blocking) —
        # that's an "unverifiable", not a crash. Fail closed.
        return VerificationResult(
            is_first_party=False,
            supports_claim=False,
            reasoning=f"unverified: fetch failed ({e})",
        )

    # continue the conversation: echo the assistant turn back UNCHANGED
    # (it carries thinking + tool_use blocks the API requires intact),
    # then answer the tool call with the fetched text
    messages.append({"role": "assistant", "content": first.content})
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": content,
                }
            ],
        }
    )

    final = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[FETCH_TOOL],
        messages=messages,
        output_format=VerificationResult,
    )

    if final.parsed_output is None:
        # e.g. the model tried to call the tool again instead of concluding
        return VerificationResult(
            is_first_party=False,
            supports_claim=False,
            reasoning="unverified: model did not produce a final verdict",
        )
    return final.parsed_output


if __name__ == "__main__":
    # real URLs from recent ingest runs
    cases = [
        # tier_a, first-party, claim should hold
        (
            "https://blog.google/company-news/inside-google/message-ceo/next-chapter-ai-momentum",
            "Demis Hassabis is moving from CEO to Chair of Google DeepMind, and Jeff Dean is departing Google.",
        ),
        # tier_c but first-party (company announcing its own product), claim should hold
        (
            "https://zed.dev/deltadb",
            "Zed announced DeltaDB, a new database technology built by the Zed team.",
        ),
        # third-party source: security firm writing about ANOTHER company's product —
        # expect is_first_party=False even if the content supports the claim
        (
            "https://www.promptarmor.com/resources/atlassian-rovo-exfiltrates-data",
            "Atlassian's Rovo AI assistant can be induced to exfiltrate data, bypassing security controls.",
        ),
    ]

    for url, claim in cases:
        print(f"URL:   {url}")
        print(f"CLAIM: {claim}")
        result = verify_article(url, claim)
        confirmed = result.is_first_party and result.supports_claim
        print(f"  first_party={result.is_first_party}  supports_claim={result.supports_claim}  -> confirmed={confirmed}")
        print(f"  reasoning: {result.reasoning}")
        print()
