import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "classification")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent")))

from classify import classify
from verify import verify_article
from cases import CLASSIFICATION_CASES, VERIFICATION_CASES


def run_classification_cases() -> tuple[int, int]:
    passed = 0
    print("=== classification evals ===")
    for case in CLASSIFICATION_CASES:
        lo, hi = case.expected_score_range
        try:
            result = classify(case.headline)
            # set match: order doesn't matter, but the exact category set does
            categories_ok = set(result.categories) == set(case.expected_categories)
            score_ok = lo <= result.score <= hi
            ok = categories_ok and score_ok
            actual = f"{sorted(result.categories)} score={result.score}"
        except Exception as e:
            # an eval harness must never crash mid-run — an exception IS a failure
            ok = False
            actual = f"EXCEPTION: {e}"

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status}] {case.headline[:60]}")
        print(f"       expected {sorted(case.expected_categories)} score in {lo}-{hi}")
        print(f"       actual   {actual}")
        if not ok:
            print(f"       why this case exists: {case.note}")
        print()
    return passed, len(CLASSIFICATION_CASES)


def run_verification_cases() -> tuple[int, int, int]:
    passed = 0
    skipped = 0
    print("=== verification evals ===")
    for case in VERIFICATION_CASES:
        skip = False
        try:
            result = verify_article(case.url, case.claim)
            ok = (
                result.is_first_party == case.expected_is_first_party
                and result.supports_claim == case.expected_supports_claim
            )
            actual = f"first_party={result.is_first_party} supports={result.supports_claim}"

            # live-web evals are flaky by construction: a site that blocks or
            # rate-limits us makes the verifier fail closed (correct behavior!)
            # but the case can't pass. If the fetch failed AND this case
            # expected a fetch-dependent verdict, that's SKIP (infrastructure
            # unavailable), not FAIL (wrong judgment). The fail-closed case
            # itself (expects False/False) still passes normally.
            fetch_failed = result.reasoning.startswith("unverified: fetch failed")
            expects_fetch = case.expected_is_first_party or case.expected_supports_claim
            if not ok and fetch_failed and expects_fetch:
                skip = True
        except Exception as e:
            ok = False
            actual = f"EXCEPTION: {e}"

        status = "SKIP" if skip else ("PASS" if ok else "FAIL")
        if ok:
            passed += 1
        elif skip:
            skipped += 1
        print(f"[{status}] {case.url[:70]}")
        print(f"       expected first_party={case.expected_is_first_party} "
              f"supports={case.expected_supports_claim}")
        print(f"       actual   {actual}")
        if skip:
            print("       (site unreachable right now — verdict not evaluated, re-run later)")
        elif not ok:
            print(f"       why this case exists: {case.note}")
        print()
    return passed, skipped, len(VERIFICATION_CASES)


if __name__ == "__main__":
    c_passed, c_total = run_classification_cases()
    v_passed, v_skipped, v_total = run_verification_cases()

    print("=== summary ===")
    print(f"classification: {c_passed}/{c_total} passed")
    print(f"verification:   {v_passed}/{v_total} passed"
          + (f" ({v_skipped} skipped: site unreachable)" if v_skipped else ""))

    # skips don't fail the run — they mean "couldn't evaluate", not "wrong".
    # A FAIL is a real judgment regression and exits non-zero for CI.
    all_ok = c_passed == c_total and (v_passed + v_skipped) == v_total
    sys.exit(0 if all_ok else 1)
