from dataclasses import dataclass, field


@dataclass
class ClassificationCase:
    headline: str
    expected_categories: list[str]
    expected_score_range: tuple[int, int]  # (min, max) inclusive — exact-score
    # matching is too strict for an inherently fuzzy judgment; the band is the contract
    note: str


@dataclass
class VerificationCase:
    url: str
    claim: str
    expected_is_first_party: bool
    expected_supports_claim: bool
    note: str


# ── classification ──────────────────────────────────────────────────────────
# The first five are the few-shot examples from classify.py's SYSTEM_PROMPT,
# verbatim. The model literally has these in its prompt, so they MUST pass —
# they function as a consistency check: if one fails, a prompt edit broke
# something fundamental (categories drifted, output schema misread, etc.).

CLASSIFICATION_CASES = [
    ClassificationCase(
        headline=(
            "OpenAI announces GPT-5, claims major reasoning improvements "
            "over GPT-4, available to all users starting today."
        ),
        expected_categories=["industry_shifting", "cultural_moment", "hot"],
        expected_score_range=(8, 10),
        note="few-shot #1 (in prompt, scored 9): flagship model release, all three news categories",
    ),
    ClassificationCase(
        headline="Seed-stage startup raises $4M to build AI-powered scheduling assistant.",
        expected_categories=["hot"],
        expected_score_range=(2, 4),
        note="few-shot #2 (in prompt, scored 3): real but narrow news, hot only",
    ),
    ClassificationCase(
        headline=(
            "Why I think microservices were a mistake for most companies "
            "(engineer's personal blog post, widely shared on HN)."
        ),
        expected_categories=["insight", "hot"],
        expected_score_range=(4, 6),
        note=(
            "few-shot #3 (in prompt, scored 5): insight AND hot — this example was "
            "deliberately fixed to assign both (categories evaluated independently); "
            "regression here means the independence rule drifted"
        ),
    ),
    ClassificationCase(
        headline="Celebrity tweets about using ChatGPT for a diet plan, goes viral.",
        expected_categories=["noise"],
        expected_score_range=(1, 3),
        note="few-shot #4 (in prompt, scored 2): high engagement, zero impact — noise exclusivity",
    ),
    ClassificationCase(
        headline=(
            "Popular JS framework announces v2 with breaking changes to core API, "
            "migration guide released."
        ),
        expected_categories=["industry_shifting", "hot"],
        expected_score_range=(5, 7),
        note=(
            "few-shot #5 (in prompt, scored 6): industry_shifting scoped to one "
            "ecosystem — checks the score stays mid-band, not inflated to 9-10"
        ),
    ),
    # ── domain-scope regression tests ──────────────────────────────────────
    # Found Aug 6 2026 testing against the July 30 HN frontpage: the UEFA story
    # (huge in SPORTS) leaked into cultural_moment + industry_shifting at score
    # 7 because the prompt never said which industry the categories are about.
    # The Premier League story got noise on the same day — the two together
    # caught the inconsistency. The domain-scope rule in SYSTEM_PROMPT is the
    # fix; these two cases keep it from regressing.
    ClassificationCase(
        headline="UEFA and its national associations will not participate in FIFA competitions",
        expected_categories=["noise"],
        expected_score_range=(1, 3),
        note=(
            "domain-scope regression: enormous SPORTS story, no tech dimension — "
            "before the domain rule this scored cultural_moment+industry_shifting 7"
        ),
    ),
    ClassificationCase(
        headline="Premier league bans gambling sponsors",
        expected_categories=["noise"],
        expected_score_range=(1, 4),
        note=(
            "domain-scope regression: sports business/regulatory story, no tech "
            "dimension — the case the model got RIGHT even pre-rule; must stay right"
        ),
    ),
]


# ── verification ────────────────────────────────────────────────────────────
# All three from the live tests that shaped verify.py's design (Aug 6 2026).

VERIFICATION_CASES = [
    VerificationCase(
        url="https://zed.dev/deltadb",
        # wording matters: an earlier draft said "database technology" and the
        # verifier (correctly) sometimes rejected it — DeltaDB is a version
        # control system, not a database. Imprecise claims make flaky evals.
        claim="Zed announced DeltaDB, a new version control technology built by the Zed team.",
        expected_is_first_party=True,
        expected_supports_claim=True,
        note=(
            "first-party despite tier_c: company announcing its own product — "
            "the per-story judgment the static tier allowlist can't make"
        ),
    ),
    VerificationCase(
        url="https://www.promptarmor.com/resources/atlassian-rovo-exfiltrates-data",
        claim=(
            "Atlassian's Rovo AI assistant can be induced to exfiltrate data, "
            "bypassing security controls."
        ),
        expected_is_first_party=False,
        expected_supports_claim=True,
        note=(
            "the source-independence case: claim is TRUE and supported, but a "
            "security firm writing about Atlassian's product is third-party — "
            "confirmed must stay out of reach (supports=True, first_party=False)"
        ),
    ),
    VerificationCase(
        url="https://this-domain-does-not-exist-cerix-eval.example.com/story",
        claim="A company announced a product.",
        expected_is_first_party=False,
        expected_supports_claim=False,
        note=(
            "fail-closed regression: unreachable URL must yield False/False "
            "(unverifiable != verified), never a crash or a guess"
        ),
    ),
]
