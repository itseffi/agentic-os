#!/usr/bin/env python3
"""Validate behavioral skill eval case files (schema only)."""

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "Evals" / "skills" / "cases"
FIXTURES_DIR = ROOT / "Evals" / "skills" / "fixtures"
SKILLS_DIR = ROOT / ".agents" / "skills"
SCENARIOS_PATH = ROOT / "Evals" / "scenarios.json"

SCENARIOS = (
    json.loads(SCENARIOS_PATH.read_text(encoding="utf-8")).get("scenarios", {})
    if SCENARIOS_PATH.exists() else {}
)

errors = []
count = 0
for path in sorted(CASES_DIR.glob("*.json")):
    count += 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: invalid JSON ({exc})")
        continue
    if not isinstance(data, dict):
        errors.append(f"{path}: top-level must be mapping")
        continue
    for key in ("skill", "version", "cases"):
        if key not in data:
            errors.append(f"{path}: missing '{key}'")
    # The runner selects fixtures and applies --skill by this field, not by the filename, so
    # a mismatch silently scores one skill's cases against another skill's fixture responses.
    declared = data.get("skill")
    # Reject an empty value outright rather than letting the guards below skip on it. With
    # `if declared`, "skill": "" silently disabled the filename, pack and fixture checks.
    if declared is not None and (not isinstance(declared, str) or not declared.strip()):
        errors.append(f"{path}: 'skill' must be a non-empty string")
        declared = None
    if declared is not None and declared != path.stem:
        errors.append(f"{path}: 'skill' is '{declared}' but the file is named '{path.stem}.json'")
    if declared is not None and not (SKILLS_DIR / str(declared)).is_dir():
        errors.append(f"{path}: 'skill' is '{declared}', which is not a pack in .agents/skills")

    fixture_path = FIXTURES_DIR / f"{declared}.json"
    fixture_ids: set[str] = set()
    # Track loading separately from contents: an empty fixture file yields an empty set, and
    # guarding the per-case check on truthiness would skip exactly the file that needs it.
    fixture_loaded = False
    if declared is not None:
        if not fixture_path.exists():
            errors.append(f"{path}: no fixture file at {fixture_path}")
        else:
            try:
                fixture_ids = set(json.loads(fixture_path.read_text(encoding="utf-8"))
                                  .get("responses", {}))
                fixture_loaded = True
            except Exception as exc:
                errors.append(f"{fixture_path}: invalid JSON ({exc})")

    cases = data.get("cases", [])
    if not isinstance(cases, list) or not cases:
        errors.append(f"{path}: 'cases' must be non-empty list")
        continue

    seen_ids: set[str] = set()
    for i, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"{path}: case #{i} must be mapping")
            continue
        for key in ("id", "expected"):
            if key not in case:
                errors.append(f"{path}: case #{i} missing '{key}'")
        case_id = case.get("id")
        if case_id:
            if case_id in seen_ids:
                errors.append(f"{path}: case #{i} duplicate id '{case_id}'")
            seen_ids.add(case_id)
            # A missing fixture entry aborts the run with an uncaught KeyError mid-suite.
            if fixture_loaded and case_id not in fixture_ids:
                errors.append(f"{path}: case '{case_id}' has no response in {fixture_path.name}")
        # A case supplies its prompt inline or by shared scenario id, never both.
        if "input" in case and "scenario" in case:
            errors.append(f"{path}: case #{i} sets 'input' and 'scenario', not both")
        elif "scenario" in case:
            if case["scenario"] not in SCENARIOS:
                errors.append(f"{path}: case #{i} unknown scenario '{case['scenario']}'")
        elif not str(case.get("input", "")).strip():
            errors.append(f"{path}: case #{i} missing or empty 'input'")
        exp = case.get("expected")
        if not isinstance(exp, list) or not exp:
            errors.append(f"{path}: case #{i} expected must be non-empty list")
        elif any(not isinstance(e, str) or not e.strip() for e in exp):
            errors.append(f"{path}: case #{i} 'expected' contains an empty string")
        if "reject" in case:
            rej = case["reject"]
            if not isinstance(rej, list) or not all(isinstance(r, str) and r.strip() for r in rej):
                errors.append(f"{path}: case #{i} 'reject' must be a list of non-empty strings")

if errors:
    print(f"FAIL: checked {count} file(s), found {len(errors)} issue(s)")
    for err in errors:
        print(f"- {err}")
    sys.exit(1)

print(f"PASS: checked {count} behavioral eval case file(s)")
