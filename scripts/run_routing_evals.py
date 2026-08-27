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


def route_skills(text: str) -> set[str]:
    # Match on word boundaries: bare substrings fire on 'plan' inside 'explanation',
    # 'complete' inside 'incomplete', 'done' inside 'abandoned', 'steps' inside 'footsteps'.
    low = text.lower()
    selected: set[str] = set()
    for skill, patterns in KEYWORD_RULES.items():
        if any(re.search(rf"\b{re.escape(p)}\b", low) for p in patterns):
            selected.add(skill)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Run routing evals.")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not cases:
        print("ERROR: no routing cases found")
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
