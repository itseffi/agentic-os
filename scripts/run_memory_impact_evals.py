#!/usr/bin/env python3
"""Run A/B memory-search impact evals."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "Evals" / "memory" / "cases.json"
RESULTS_DIR = ROOT / "Evals" / "memory" / "results"

# Both sides of the A/B are read from the cases file, so this runner compares two strings the
# repo wrote for itself. It has no provider option at all; nothing here is generated.
CAVEAT = (
    "both sides of the comparison are read from Evals/memory/cases.json; nothing is "
    "generated, so this measures the cases file, not memory search."
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _contains_phrase(response: str, phrase: str) -> bool:
    """True when `phrase` appears in `response` as a contiguous phrase.

    This used to test token-subset membership despite its name, so it matched the words in
    any order, scattered anywhere in the response, and returned True for an empty phrase.
    All 16 expectations across the shipped cases hold either way, so the loose reading bought
    nothing and hid what the check meant.
    """
    if not phrase.strip():
        raise ValueError("empty expectation phrase")
    return re.search(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)", response.lower()) is not None


def validate_cases(cases: list[dict]) -> list[str]:
    """Check the memory cases; nothing validated this file before.

    A case with both expectation lists empty scored a silent pass, and no validator covered
    Evals/memory/cases.json at all.
    """
    errors: list[str] = []
    seen: set[str] = set()
    for position, case in enumerate(cases, start=1):
        case_id = case.get("id") or f"<case {position}>"
        if "id" not in case:
            errors.append(f"{case_id}: missing 'id'")
        elif case_id in seen:
            errors.append(f"{case_id}: duplicate id")
        seen.add(case_id)

        for field in ("input", "baseline_response", "memory_search_response"):
            if not str(case.get(field, "")).strip():
                errors.append(f"{case_id}: missing or empty '{field}'")

        enabled = case.get("expected_when_enabled", [])
        absent = case.get("expected_missing_in_baseline", [])
        if not enabled and not absent:
            errors.append(f"{case_id}: needs at least one expectation; empty lists pass vacuously")
        for name, phrases in (("expected_when_enabled", enabled),
                              ("expected_missing_in_baseline", absent)):
            if not isinstance(phrases, list):
                errors.append(f"{case_id}: '{name}' must be a list")
                continue
            for phrase in phrases:
                if not isinstance(phrase, str) or not phrase.strip():
                    errors.append(f"{case_id}: '{name}' contains an empty phrase")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run memory-search impact evals.")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not cases:
        print("ERROR: no memory impact cases found")
        return 2

    case_errors = validate_cases(cases)
    if case_errors:
        print(f"ERROR: {len(case_errors)} invalid case(s) in {CASES_PATH.relative_to(ROOT)}")
        for err in case_errors:
            print(f"- {err}")
        return 2

    results = []
    passed = 0
    for case in cases:
        baseline = case["baseline_response"]
        with_memory = case["memory_search_response"]

        expected_enabled = case.get("expected_when_enabled", [])
        expected_absent_baseline = case.get("expected_missing_in_baseline", [])

        enabled_hits = [p for p in expected_enabled if _contains_phrase(with_memory, p)]
        enabled_misses = [p for p in expected_enabled if p not in enabled_hits]

        baseline_missing_ok = [p for p in expected_absent_baseline if not _contains_phrase(baseline, p)]
        baseline_missing_fail = [p for p in expected_absent_baseline if p not in baseline_missing_ok]

        ok = not enabled_misses and not baseline_missing_fail
        if ok:
            passed += 1

        results.append(
            {
                "id": case["id"],
                "input": case["input"],
                "baseline_response": baseline,
                "memory_search_response": with_memory,
                "expected_when_enabled": expected_enabled,
                "expected_missing_in_baseline": expected_absent_baseline,
                "enabled_hits": enabled_hits,
                "enabled_misses": enabled_misses,
                "baseline_missing_ok": baseline_missing_ok,
                "baseline_missing_fail": baseline_missing_fail,
                "passed": ok,
            }
        )

    total = len(cases)
    pass_rate = passed / total if total else 0.0

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{ts}-memory-impact.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": ts,
        "provider": "fixture",
        "provider_caveat": CAVEAT,
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "pass_rate": round(pass_rate, 3),
            "min_pass_rate": args.min_pass_rate,
        },
        "results": results,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"NOTE: {CAVEAT}")
    print(f"PASS RATE: {passed}/{total} = {pass_rate:.3f}")
    print(f"RESULTS: {out.relative_to(ROOT)}")
    for r in results:
        state = "PASS" if r["passed"] else "FAIL"
        print(f"- [{state}] {r['id']}")

    return 0 if pass_rate >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
