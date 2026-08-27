#!/usr/bin/env python3
"""Shared helpers for the eval runners: scenario prompts and results paths.

`load_scenarios` and `case_input` were copy-pasted into two runners when scenarios were
introduced, which is the duplication that item 22 had just removed from the case files.
`unique_results_path` fixes a collision that had been latent since the first audit.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def unique_results_path(directory: Path, stem: str, suffix: str = ".json") -> Path:
    """Return a path that does not yet exist, creating the directory if needed.

    Result filenames are stamped to the second, so two runs inside the same second used to
    resolve to the same path and the second silently overwrote the first. Appends -2, -3 and
    so on instead of destroying the earlier run.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}{suffix}"
    counter = 2
    while path.exists():
        path = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return path
