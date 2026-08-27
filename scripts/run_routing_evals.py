#!/usr/bin/env python3
"""Run lightweight routing evals (did the agent pick the right skill?)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_io import case_input, load_scenarios, unique_results_path  # noqa: E402
from model_client import ModelError, query_chat  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"
AGENTS_MD = ROOT / "AGENTS.md"
CASES_PATH = ROOT / "Evals" / "skills" / "routing_cases.json"
RESULTS_DIR = ROOT / "Evals" / "skills" / "results"




KEYWORD_CAVEAT = (
    "--provider keyword scores the built-in keyword table in this file, not an agent's "
    "routing. Use --provider openai to route with a model given the skill catalogue and the "
    "AGENTS.md policy."
)


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


def _routing_policy() -> str:
    """Return the Skill Routing Policy section of AGENTS.md, which is what a real agent sees."""
    if not AGENTS_MD.exists():
        return ""
    text = AGENTS_MD.read_text(encoding="utf-8")
    match = re.search(r"^## Skill Routing Policy.*?(?=^## )", text, re.MULTILINE | re.DOTALL)
    return match.group(0).strip() if match else ""


def _skill_catalogue() -> str:
    """Name and describe each routable skill from its own SKILL.md frontmatter."""
    lines = []
    for skill in sorted(KEYWORD_RULES):
        path = SKILLS_DIR / skill / "SKILL.md"
        description = ""
        if path.exists():
            match = re.search(r"^description:\s*(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
            description = match.group(1).strip() if match else ""
        lines.append(f"- {skill}" + (f": {description}" if description else ""))
    return "\n".join(lines)


def _model_system_prompt() -> str:
    policy = _routing_policy()
    return (
        "You route work to skills in a repository. Choose every skill that applies to the "
        "user's message, and no others.\n\n"
        f"Available skills:\n{_skill_catalogue()}\n\n"
        + (f"Routing policy from AGENTS.md:\n{policy}\n\n" if policy else "")
        + 'Reply with only a JSON array of skill names, for example ["tdd"]. '
        "Use an empty array if none apply."
    )


def route_skills_via_model(text: str, *, base_url: str, model: str, api_key: str) -> set[str]:
    """Ask a model to route, then map its JSON answer onto the known skill names.

    The bracket search tolerates a JSON array wrapped in prose or a fenced code block. It
    deliberately does not fall back to scanning the reply for skill names: that scan is blind
    to negation, so "tdd does not apply here" selected tdd, and "this is not a brainstorming
    task" selected brainstorming. A reply carrying no array is a protocol failure, and saying
    so beats guessing the opposite of what the model meant.
    """
    reply = query_chat(
        base_url=base_url,
        model=model,
        api_key=api_key,
        system_prompt=_model_system_prompt(),
        user_input=text,
    )

    match = re.search(r"\[.*?\]", reply, re.DOTALL)
    if not match:
        raise ModelError(f"reply contained no JSON array of skill names: {reply[:120].strip()!r}")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ModelError(f"could not parse skill array: {match.group(0)[:120]!r}") from exc
    if not isinstance(parsed, list):
        raise ModelError(f"expected a JSON array of skill names, got {type(parsed).__name__}")

    named = {str(x).strip() for x in parsed}
    known = set(KEYWORD_RULES)
    unknown = named - known
    if unknown:
        raise ModelError(f"reply named unknown skill(s): {sorted(unknown)}")
    return named


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
    scenarios = load_scenarios()

    for position, case in enumerate(cases, start=1):
        case_id = case.get("id") or f"<case {position}>"
        if "id" not in case:
            errors.append(f"{case_id}: missing 'id'")
        elif case_id in seen:
            errors.append(f"{case_id}: duplicate id")
        seen.add(case_id)

        if "input" in case and "scenario" in case:
            errors.append(f"{case_id}: set 'input' or 'scenario', not both")
        elif "scenario" in case:
            if case["scenario"] not in scenarios:
                errors.append(f"{case_id}: unknown scenario '{case['scenario']}'")
        elif not str(case.get("input", "")).strip():
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
    parser.add_argument(
        "--provider",
        choices=["keyword", "openai"],
        default="keyword",
        help="Who routes: the built-in keyword table, or a model given the routing policy.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", ""),
        help="OpenAI-compatible base URL, or set OPENAI_BASE_URL. Required by --provider openai.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", ""),
        help="Model id for --provider openai.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        help="API key. Omit for a local endpoint that needs none; no header is sent.",
    )
    args = parser.parse_args()

    if args.provider == "openai":
        # Validate both together. A silently defaulted base URL turned a misconfiguration
        # into five identical connection failures and a 0/5 pass rate that reads like the
        # router was wrong, while a missing --model said so plainly and exited.
        missing = [flag for flag, value in (("--model", args.model), ("--base-url", args.base_url))
                   if not value]
        if missing:
            print(f"ERROR: {' and '.join(missing)} required when --provider openai "
                  "(or set OPENAI_MODEL / OPENAI_BASE_URL)")
            return 2

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

    # One string, printed and recorded, so the two cannot drift apart.
    provider_caveat = KEYWORD_CAVEAT if args.provider == "keyword" else None

    scenarios = load_scenarios()
    results = []
    passed = 0
    for case in cases:
        text = case_input(case, scenarios)
        error: str | None = None
        if args.provider == "keyword":
            selected = route_skills(text)
        else:
            try:
                selected = route_skills_via_model(
                    text,
                    base_url=args.base_url,
                    model=args.model,
                    api_key=args.api_key,
                )
            except ModelError as exc:
                # Record and continue rather than aborting the whole run.
                selected, error = set(), str(exc)
        should = set(case.get("should_select", []))
        should_not = set(case.get("should_not_select", []))
        missing = sorted(list(should - selected))
        false_pos = sorted(list(selected & should_not))
        # Closed world: should_select is the complete expected answer. Without this a
        # router firing every non-forbidden skill scores the same as the correct one.
        unexpected = sorted(list(selected - should))
        ok = not missing and not unexpected and error is None
        if ok:
            passed += 1
        results.append(
            {
                "id": case["id"],
                "input": text,
                "selected": sorted(selected),
                "should_select": sorted(should),
                "should_not_select": sorted(should_not),
                "missing_required": missing,
                "forbidden_selected": false_pos,
                "unexpected_selected": unexpected,
                "error": error,
                "passed": ok,
            }
        )

    total = len(cases)
    pass_rate = passed / total if total else 0.0

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = unique_results_path(RESULTS_DIR, f"{ts}-routing")
    payload = {
        "timestamp_utc": ts,
        "provider": args.provider,
        "provider_caveat": provider_caveat,
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "pass_rate": round(pass_rate, 3),
            "min_pass_rate": args.min_pass_rate,
        },
        "results": results,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if provider_caveat:
        print(f"NOTE: {provider_caveat}")
    print(f"PASS RATE: {passed}/{total} = {pass_rate:.3f}")
    print(f"RESULTS: {out.relative_to(ROOT)}")
    for r in results:
        state = "PASS" if r["passed"] else "FAIL"
        detail = f"  ({r['error']})" if r.get("error") else ""
        print(f"- [{state}] {r['id']} -> selected={','.join(r['selected']) or '(none)'}{detail}")

    return 0 if pass_rate >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
