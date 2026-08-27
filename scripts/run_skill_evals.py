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


SCENARIOS_PATH = ROOT / "Evals" / "scenarios.json"


def load_scenarios() -> dict[str, str]:
    """Prompts shared between eval suites, keyed by id."""
    if not SCENARIOS_PATH.exists():
        return {}
    return json.loads(SCENARIOS_PATH.read_text(encoding="utf-8")).get("scenarios", {})


def case_input(case: dict, scenarios: dict[str, str]) -> str:
    """Resolve a case's prompt from an inline `input` or a shared `scenario` id."""
    if "scenario" in case:
        return scenarios[case["scenario"]]
    return case["input"]


@dataclass
class CaseResult:
    skill: str
    case_id: str
    passed: bool
    response: str
    checks: list[dict[str, Any]]
    rejected: list[str] | None = None
    error: str | None = None


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_expectation(expected: str, response: str) -> float:
    exp = _tokens(expected)
    if not exp:
        # Returning 1.0 here made an empty expectation a free pass. The validator rejects
        # empty strings, so reaching this is a bug in the caller, not a case to score.
        raise ValueError(f"expectation has no scoreable tokens: {expected!r}")
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


def _find_rejections(case: dict[str, Any], response: str) -> list[str]:
    """Phrases whose presence fails the case outright.

    Token-set overlap is unordered and blind to negation: 'enforces failing test first' and
    'skip the failing test first' share every token, so a response arguing against the skill
    scores 1.00. Reject phrases catch that inversion without needing a model.
    """
    low = response.lower()
    return [p for p in case.get("reject", []) if str(p).lower() in low]


def _judge_expectation(
    expectation: str,
    response: str,
    *,
    base_url: str,
    model: str,
    api_key: str,
) -> tuple[bool, str]:
    """Ask a model whether the response satisfies the expectation. Returns (verdict, raw)."""
    verdict = query_chat(
        base_url=base_url,
        model=model,
        api_key=api_key,
        system_prompt=(
            "You grade whether a response satisfies a stated expectation. Judge the stance "
            "the response actually takes, not whether it reuses the expectation's words. "
            "A response arguing against the expectation does not satisfy it. "
            "Reply with exactly YES or NO."
        ),
        user_input=f"Expectation:\n{expectation}\n\nResponse:\n{response}",
    )
    return verdict.strip().upper().startswith("YES"), verdict.strip()


def _evaluate_case(
    *,
    skill: str,
    case: dict[str, Any],
    response: str,
    threshold: float,
    judge: dict[str, str] | None = None,
) -> CaseResult:
    checks = []
    for expected in case["expected"]:
        if judge:
            ok, raw = _judge_expectation(expected, response, **judge)
            checks.append({"expected": expected, "verdict": raw[:80], "passed": ok})
        else:
            score = _score_expectation(expected, response)
            checks.append(
                {
                    "expected": expected,
                    "score": round(score, 3),
                    "passed": score >= threshold,
                }
            )
    rejected = _find_rejections(case, response)
    passed = all(c["passed"] for c in checks) and not rejected
    return CaseResult(
        skill=skill,
        case_id=case["id"],
        passed=passed,
        response=response,
        checks=checks,
        rejected=rejected or None,
    )


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
        "--judge",
        choices=["overlap", "openai"],
        default="overlap",
        help="How expectations are graded. 'overlap' is token-set matching, which is blind "
             "to negation; 'openai' asks a model whether the response satisfies each one.",
    )
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
        default=os.environ.get("OPENAI_BASE_URL", ""),
        help="OpenAI-compatible base URL, or set OPENAI_BASE_URL. "
             "Required by --provider openai and by --judge openai.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", ""),
        help="Model id, or set OPENAI_MODEL. "
             "Required by --provider openai and by --judge openai.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        help="API key. Omit for a local endpoint that needs none; no header is sent.",
    )
    args = parser.parse_args()

    # Both --provider openai and --judge openai reach a model, and both need the same two
    # settings. Validate once, naming whichever flags are actually missing.
    needs_model = [name for name, value in
                   (("--provider openai", args.provider == "openai"),
                    ("--judge openai", args.judge == "openai")) if value]
    if needs_model:
        missing = [flag for flag, value in (("--model", args.model), ("--base-url", args.base_url))
                   if not value]
        if missing:
            print(f"ERROR: {' and '.join(missing)} required by {' and '.join(needs_model)} "
                  "(or set OPENAI_MODEL / OPENAI_BASE_URL)")
            return 2

    # Both axes can be self-referential and each is disclosed independently. Caveating only
    # the judge left --provider fixture --judge openai printing nothing at all, while every
    # response being scored was text this repo had written for itself.
    provider_caveat = (
        "--provider fixture scores canned responses from Evals/skills/fixtures, which this "
        "repo wrote for itself; it measures nothing about a model."
        if args.provider == "fixture" else None
    )
    judge_caveat = (
        "--judge overlap compares token sets and cannot detect stance. A response arguing "
        "against a skill in the skill's own vocabulary scores as well as one following it. "
        "Use --judge openai for a verdict on the claim."
        if args.judge == "overlap" else None
    )

    judge = None
    if args.judge == "openai":
        judge = {"base_url": args.base_url, "model": args.model, "api_key": args.api_key}

    casesets = _load_case_files(args.skill)
    if not casesets:
        print("ERROR: no matching case files found")
        return 2

    scenarios = load_scenarios()
    results: list[CaseResult] = []
    for data in casesets:
        skill = data["skill"]
        for case in data["cases"]:
            case_text = case_input(case, scenarios)
            if args.provider == "fixture":
                response = _load_fixture_response(skill, case["id"])
            else:
                try:
                    response = query_chat(
                        base_url=args.base_url,
                        model=args.model,
                        api_key=args.api_key,
                        system_prompt=_system_prompt(skill),
                        user_input=case_text,
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
            try:
                results.append(
                    _evaluate_case(
                        skill=skill,
                        case=case,
                        response=response,
                        threshold=args.threshold,
                        judge=judge,
                    )
                )
            except ModelError as exc:
                results.append(
                    CaseResult(skill=skill, case_id=case["id"], passed=False,
                               response=response, checks=[], error=f"judge failed: {exc}")
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
        "provider_caveat": provider_caveat,
        "judge": args.judge,
        "judge_caveat": judge_caveat,
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
                "rejected": r.rejected,
                "error": r.error,
            }
            for r in results
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    for note in (n for n in (provider_caveat, judge_caveat) if n):
        print(f"NOTE: {note}")
    print(f"PASS RATE: {passed}/{total} = {pass_rate:.3f}")
    print(f"RESULTS: {out_path.relative_to(ROOT)}")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        suffix = f"  ({r.error})" if r.error else (
            f"  (rejected: {', '.join(r.rejected)})" if r.rejected else "")
        print(f"- [{status}] {r.skill}/{r.case_id}{suffix}")

    if pass_rate < args.min_pass_rate:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
