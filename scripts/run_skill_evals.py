#!/usr/bin/env python3
"""Run lightweight behavioral skill evals and write scored results."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_client import ModelError, query_chat  # noqa: E402  (needs sys.path above)

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"
CASES_DIR = ROOT / "Evals" / "skills" / "cases"
FIXTURES_DIR = ROOT / "Evals" / "skills" / "fixtures"
RESULTS_DIR = ROOT / "Evals" / "skills" / "results"


@dataclass
class CaseResult:
    skill: str
    case_id: str
    passed: bool
    response: str
    checks: list[dict[str, Any]]
    error: str | None = None


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_expectation(expected: str, response: str) -> float:
    exp = _tokens(expected)
    if not exp:
        return 1.0
    got = _tokens(response)
    return len(exp & got) / len(exp)


def _load_case_files(skill_filter: str | None) -> list[dict[str, Any]]:
    casesets = []
    for path in sorted(CASES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if skill_filter and data.get("skill") != skill_filter:
            continue
        casesets.append(data)
    return casesets


def _load_fixture_response(skill: str, case_id: str) -> str:
    fixture_path = FIXTURES_DIR / f"{skill}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"missing fixture file: {fixture_path}")
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    responses = data.get("responses", {})
    if case_id not in responses:
        raise KeyError(f"missing fixture response for case '{case_id}' in {fixture_path}")
    return str(responses[case_id])


def _skill_brief(skill: str) -> str:
    """Return the skill's name and frontmatter description from its SKILL.md.

    The previous prompt never told the model which skill was under test, so --provider openai
    measured the base model's default behaviour rather than the skill.
    """
    path = SKILLS_DIR / skill / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"missing skill pack: {path}")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    description = match.group(1).strip() if match else ""
    return f"{skill}: {description}" if description else skill


def _system_prompt(skill: str) -> str:
    """Build the system prompt for one skill.

    Deliberately free of the vocabulary the expectations are scored on. The old fixed prompt
    said "include concrete verification-oriented guidance", which handed the verification
    cases a scored token before the model had said anything.
    """
    return (
        "You are a coding assistant working in a repository that defines reusable skills.\n"
        f"Apply this skill to the user's message:\n  {_skill_brief(skill)}\n"
        "Respond directly and concretely, as you would to a colleague."
    )


def _evaluate_case(
    *,
    skill: str,
    case: dict[str, Any],
    response: str,
    threshold: float,
) -> CaseResult:
    checks = []
    for expected in case["expected"]:
        score = _score_expectation(expected, response)
        checks.append(
            {
                "expected": expected,
                "score": round(score, 3),
                "passed": score >= threshold,
            }
        )
    passed = all(c["passed"] for c in checks)
    return CaseResult(skill=skill, case_id=case["id"], passed=passed, response=response, checks=checks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run behavioral skill evals.")
    parser.add_argument(
        "--provider",
        choices=["fixture", "openai"],
        default="fixture",
        help="Where responses come from: fixture files or OpenAI-compatible model endpoint.",
    )
    parser.add_argument("--skill", help="Run only one skill case file (e.g. verification).")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Per-expectation token-overlap pass threshold (0.0-1.0).",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="Fail process if overall pass rate is below this value.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", "http://localhost:8080/v1"),
        help="OpenAI-compatible base URL for --provider openai.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", ""),
        help="Model id for --provider openai.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", "none"),
        help="API key for --provider openai.",
    )
    args = parser.parse_args()

    if args.provider == "openai" and not args.model:
        print("ERROR: --model is required when --provider openai")
        return 2

    casesets = _load_case_files(args.skill)
    if not casesets:
        print("ERROR: no matching case files found")
        return 2

    results: list[CaseResult] = []
    for data in casesets:
        skill = data["skill"]
        for case in data["cases"]:
            if args.provider == "fixture":
                response = _load_fixture_response(skill, case["id"])
            else:
                try:
                    response = query_chat(
                        base_url=args.base_url,
                        model=args.model,
                        api_key=args.api_key,
                        system_prompt=_system_prompt(skill),
                        user_input=case["input"],
                    )
                except ModelError as exc:
                    # Record and continue: a single transport blip used to abort the run
                    # before anything was written, discarding every result so far.
                    results.append(
                        CaseResult(
                            skill=skill,
                            case_id=case["id"],
                            passed=False,
                            response="",
                            checks=[],
                            error=str(exc),
                        )
                    )
                    continue
            results.append(
                _evaluate_case(
                    skill=skill,
                    case=case,
                    response=response,
                    threshold=args.threshold,
                )
            )

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    pass_rate = passed / total if total else 0.0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{timestamp}-{args.provider}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": timestamp,
        "provider": args.provider,
        "threshold": args.threshold,
        "min_pass_rate": args.min_pass_rate,
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "pass_rate": round(pass_rate, 3),
        },
        "results": [
            {
                "skill": r.skill,
                "case_id": r.case_id,
                "passed": r.passed,
                "checks": r.checks,
                "response": r.response,
                "error": r.error,
            }
            for r in results
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"PASS RATE: {passed}/{total} = {pass_rate:.3f}")
    print(f"RESULTS: {out_path.relative_to(ROOT)}")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        suffix = f"  ({r.error})" if r.error else ""
        print(f"- [{status}] {r.skill}/{r.case_id}{suffix}")

    if pass_rate < args.min_pass_rate:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
