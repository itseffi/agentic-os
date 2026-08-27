#!/usr/bin/env python3
"""Run lightweight routing evals (did the agent pick the right skill?)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "Evals" / "skills" / "routing_cases.json"
RESULTS_DIR = ROOT / "Evals" / "skills" / "results"


KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "verification": ("verify", "verification", "complete", "done", "evidence", "pass now"),
    "tdd": ("tdd", "test first", "test later", "failing test", "red green"),
    "writing-plans": ("plan", "planning", "migration", "checkpoints", "steps"),
    "systematic-debugging": ("debug", "bug", "root cause", "intermittent", "failure"),
    "brainstorming": ("brainstorm", "ideas", "explore directions"),
}


def _boundary_pattern(keyword: str) -> str:
    """Anchor a keyword so it does not fire inside a longer word.

    Lowercases the keyword as well as the text: normalising only one side means a rule
    written as 'Red Green' would silently never match. Uses lookarounds rather than \\b so
    keywords that start or end with a non-word character ('c++', '-v') still match.
    """
    return r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"


def route_skills(text: str) -> set[str]:
    # Anchored matching: bare substrings fire on 'plan' inside 'explanation', 'complete'
    # inside 'incomplete', 'done' inside 'abandoned', 'steps' inside 'footsteps'.
    low = text.lower()
    selected: set[str] = set()
    for skill, patterns in KEYWORD_RULES.items():
        if any(re.search(_boundary_pattern(p), low) for p in patterns):
            selected.add(skill)
    return selected


def validate_cases(cases: list[dict]) -> list[str]:
    """Check routing cases before scoring; nothing else validates this file.

    validate_skill_eval_cases.py only globs Evals/skills/cases/*.json, and routing_cases.json
    sits a level above that, so without this a malformed case fails silently. A skill named in
    both should_select and should_not_select is the worst of them: the closed-world pass rule
    ignores should_not_select entirely, so the contradiction passes instead of being caught.
    """
    errors: list[str] = []
    known = set(KEYWORD_RULES)
    seen: set[str] = set()

    for position, case in enumerate(cases, start=1):
        case_id = case.get("id") or f"<case {position}>"
        if "id" not in case:
            errors.append(f"{case_id}: missing 'id'")
        elif case_id in seen:
            errors.append(f"{case_id}: duplicate id")
        seen.add(case_id)

        if not str(case.get("input", "")).strip():
            errors.append(f"{case_id}: missing or empty 'input'")

        should = set(case.get("should_select", []))
        should_not = set(case.get("should_not_select", []))
        if not should:
            errors.append(f"{case_id}: 'should_select' must be a non-empty list")

        contradictory = should & should_not
        if contradictory:
            errors.append(
                f"{case_id}: {sorted(contradictory)} listed in both should_select and "
                "should_not_select"
            )
        for name in sorted((should | should_not) - known):
            errors.append(f"{case_id}: unknown skill '{name}' (not in KEYWORD_RULES)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run routing evals.")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not cases:
        print("ERROR: no routing cases found")
        return 2

    case_errors = validate_cases(cases)
    if case_errors:
        print(f"ERROR: {len(case_errors)} invalid routing case(s) in {CASES_PATH.relative_to(ROOT)}")
        for err in case_errors:
            print(f"- {err}")
        return 2

    results = []
    passed = 0
    for case in cases:
        selected = route_skills(case["input"])
        should = set(case.get("should_select", []))
        should_not = set(case.get("should_not_select", []))
        missing = sorted(list(should - selected))
        false_pos = sorted(list(selected & should_not))
        # Closed world: should_select is the complete expected answer. Without this a
        # router firing every non-forbidden skill scores the same as the correct one.
        unexpected = sorted(list(selected - should))
        ok = not missing and not unexpected
        if ok:
            passed += 1
        results.append(
            {
                "id": case["id"],
                "input": case["input"],
                "selected": sorted(selected),
                "should_select": sorted(should),
                "should_not_select": sorted(should_not),
                "missing_required": missing,
                "forbidden_selected": false_pos,
                "unexpected_selected": unexpected,
                "passed": ok,
            }
        )

    total = len(cases)
    pass_rate = passed / total if total else 0.0

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{ts}-routing.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": ts,
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "pass_rate": round(pass_rate, 3),
            "min_pass_rate": args.min_pass_rate,
        },
        "results": results,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"PASS RATE: {passed}/{total} = {pass_rate:.3f}")
    print(f"RESULTS: {out.relative_to(ROOT)}")
    for r in results:
        state = "PASS" if r["passed"] else "FAIL"
        print(f"- [{state}] {r['id']} -> selected={','.join(r['selected']) or '(none)'}")

    return 0 if pass_rate >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
