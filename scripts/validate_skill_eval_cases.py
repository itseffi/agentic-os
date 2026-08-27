#!/usr/bin/env python3
"""Validate behavioral skill eval case files (schema only)."""

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "Evals" / "skills" / "cases"

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
    cases = data.get("cases", [])
    if not isinstance(cases, list) or not cases:
        errors.append(f"{path}: 'cases' must be non-empty list")
        continue
    for i, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"{path}: case #{i} must be mapping")
            continue
        for key in ("id", "input", "expected"):
            if key not in case:
                errors.append(f"{path}: case #{i} missing '{key}'")
        exp = case.get("expected")
        if not isinstance(exp, list) or not exp:
            errors.append(f"{path}: case #{i} expected must be non-empty list")
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
