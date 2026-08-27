#!/usr/bin/env python3
"""Regression tests for System/mcp/server.py.

Covers the six defects fixed in items 1, 2, 4, 5, 6 and 7 of FIXES.md. The `mcp` package is
not a dependency of this repository, so it is stubbed: none of the behaviour under test
touches the protocol layer.

Plain script, no test framework, matching the other scripts here:

    python3 scripts/test_mcp_server.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import types as pytypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILURES.append(label + (f" ({detail})" if detail else ""))


def _stub_mcp() -> None:
    """Install a minimal `mcp` package so server.py imports without the real dependency."""
    for name in ["mcp", "mcp.server", "mcp.server.models", "mcp.server.stdio", "mcp.types"]:
        sys.modules[name] = pytypes.ModuleType(name)

    class _Server:
        def __init__(self, name):
            pass

        def list_tools(self):
            return lambda fn: fn

        def call_tool(self):
            return lambda fn: fn

    class _TextContent:
        def __init__(self, type=None, text=None):
            self.text = text

    sys.modules["mcp.server"].Server = _Server
    sys.modules["mcp.server"].NotificationOptions = object
    sys.modules["mcp.server.models"].InitializationOptions = object
    # dict, not object: types.Tool(...) is called with keywords, so a bare object() rejects
    # them and handle_list_tools cannot be exercised at all.
    sys.modules["mcp.types"].Tool = dict
    sys.modules["mcp.types"].TextContent = _TextContent
    sys.modules["mcp.types"].ImageContent = object
    sys.modules["mcp.types"].EmbeddedResource = object
    sys.modules["mcp"].server = sys.modules["mcp.server"]
    sys.modules["mcp"].types = sys.modules["mcp.types"]
    sys.modules["mcp.server"].stdio = sys.modules["mcp.server.stdio"]


def load_server():
    """Import server.py against a fresh temporary workspace."""
    import os
    import importlib.util

    workspace = Path(tempfile.mkdtemp())
    os.environ["PERSONAL_OS_DIR"] = str(workspace)
    _stub_mcp()
    spec = importlib.util.spec_from_file_location("mcp_server", ROOT / "System/mcp/server.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_server"] = module
    spec.loader.exec_module(module)
    return module, workspace


SERVER, WORKSPACE = load_server()


def call(tool: str, arguments: dict | None = None) -> dict:
    return json.loads(asyncio.run(SERVER.handle_call_tool(tool, arguments))[0].text)


def test_create_task_refuses_to_overwrite() -> None:
    """Item 1: overwriting reset an in-progress task to a blank template, reporting success."""
    call("create_task", {"title": "Migrate billing", "priority": "P0", "category": "technical"})
    path = WORKSPACE / "Tasks" / "migrate-billing.md"
    call("update_task_status", {"task_file": "migrate-billing.md", "status": "s"})
    path.write_text(path.read_text() + "- 2026-08-20: blocked on finance sign-off.\n")
    before = path.read_text()

    result = call("create_task", {"title": "Migrate billing"})
    check("second create is refused", result["success"] is False, str(result))
    check("refusal names the existing file", result.get("existing_file") == "migrate-billing.md")
    check("refusal is distinguishable from an I/O error", "already exists" in result.get("error", ""))
    check("the existing task is untouched", path.read_text() == before)

    # Punctuation-only differences slug to the same filename.
    check("slug collision is refused too",
          call("create_task", {"title": "Migrate billing!"})["success"] is False)


def test_get_system_status_survives_incomplete_frontmatter() -> None:
    """Item 2: one task missing a field took the whole tool down with a KeyError."""
    (WORKSPACE / "Tasks" / "no-priority.md").write_text(
        "---\ntitle: Ship the thing\nstatus: n\ncategory: technical\n---\n\n# Ship\n")
    try:
        result = call("get_system_status")
        check("get_system_status returns", "priority_distribution" in result, str(result)[:120])
        check("the incomplete task is counted with a default",
              result["priority_distribution"].get("P2", 0) >= 1, str(result["priority_distribution"]))
    except Exception as exc:  # noqa: BLE001
        check("get_system_status returns", False, f"{type(exc).__name__}: {exc}")


def test_dedup_sees_tasks_created_in_the_same_batch() -> None:
    """Item 4: existing_tasks was snapshotted before the loop and never updated."""
    result = call("process_backlog_with_dedup", {
        "items": ["Draft the Q3 partner outreach email",
                  "Draft the Q3 partner outreach emails"],
        "auto_create": True})
    check("only the first of two near-identical items is created",
          len(result["auto_created"]) == 1, str(result["auto_created"]))
    check("the second is flagged as a duplicate",
          len(result["potential_duplicates"]) == 1, str(result["potential_duplicates"]))

    # A batch item colliding with an existing file is reported, not silently overwritten.
    again = call("process_backlog_with_dedup", {
        "items": ["Something entirely unrelated to write about"], "auto_create": True})
    repeat = call("process_backlog_with_dedup", {
        "items": ["Something entirely unrelated to write about"], "auto_create": True})
    check("first creation succeeds", len(again["auto_created"]) == 1, str(again["auto_created"]))
    check("a colliding batch item is skipped and reported",
          repeat["skipped_existing"] or repeat["potential_duplicates"],
          f"created={repeat['auto_created']}")


def test_create_task_validates_its_inputs() -> None:
    """Item 5: priority and estimated_time reached the frontmatter unchecked."""
    call("create_task", {"title": "Bogus priority task", "priority": "URGENT", "category": "nope"})
    text = (WORKSPACE / "Tasks" / "bogus-priority-task.md").read_text()
    check("invalid priority is coerced to P2", "priority: P2" in text, text[:160])
    check("invalid category is coerced to other", "category: other" in text, text[:160])
    check("a coerced priority is counted by check_priority_limits",
          "URGENT" not in str(call("check_priority_limits")["priority_counts"]))

    call("create_task", {"title": "String time task", "estimated_time": "45"})
    check("a string estimated_time is coerced",
          "estimated_time: 45" in (WORKSPACE / "Tasks" / "string-time-task.md").read_text())
    try:
        call("get_task_summary")
        check("get_task_summary survives it", True)
    except Exception as exc:  # noqa: BLE001
        check("get_task_summary survives it", False, f"{type(exc).__name__}: {exc}")

    for title in ["   ", "!!!", ""]:
        check(f"empty-ish title {title!r} refused",
              call("create_task", {"title": title})["success"] is False)


def test_handlers_survive_null_arguments() -> None:
    """Item 6: arguments['title'] sat outside the try and escaped as a TypeError."""
    for tool in ["create_task", "update_task_status", "annotate_eval"]:
        for arguments in (None, {}):
            try:
                result = call(tool, arguments)
                check(f"{tool}({arguments}) returns a structured error",
                      result.get("success") is False and "required" in result.get("error", ""),
                      str(result)[:120])
            except Exception as exc:  # noqa: BLE001
                check(f"{tool}({arguments}) returns a structured error", False,
                      f"{type(exc).__name__}: {exc}")


def test_status_updates_do_not_grow_the_file() -> None:
    """Item 7: each update added one blank line after the frontmatter, without limit."""
    call("create_task", {"title": "Round trip"})
    path = WORKSPACE / "Tasks" / "round-trip.md"
    shapes = []
    for status in ["s", "b", "d"]:
        call("update_task_status", {"task_file": "round-trip.md", "status": status})
        shapes.append(path.read_text().split("---\n")[2][:4])
    check("the gap after the frontmatter is stable", len(set(shapes)) == 1, str(shapes))
    check("the body survives", "## Progress Log" in path.read_text())
    check("the status is applied", "status: d" in path.read_text())


def test_docs_do_not_advertise_missing_tools() -> None:
    """Every tool named in a docs table must actually be advertised by the server.

    generate_eval was removed from the server but stayed in Tutorials/session-evals.md, in a
    tool table and two diagrams, telling readers to call something that no longer existed.
    Stale help text was the same failure one item earlier.
    """
    import re

    advertised = {tool["name"] for tool in asyncio.run(SERVER.handle_list_tools())}
    check("the server advertises tools at all", len(advertised) > 5, str(len(advertised)))

    # Only tables actually headed `| Tool |`, and only docs describing THIS server.
    # System/integrations/** documents other MCP servers, and judgement-value tables are
    # headed `| Value |`; an earlier version of this check swept in all of them.
    documented: list[tuple[str, str]] = []
    for path in sorted(ROOT.glob("**/*.md")):
        parts = path.relative_to(ROOT).parts
        if ".git" in parts or path.name == "FIXES.md" or "integrations" in parts:
            continue
        in_tool_table = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\|\s*Tool\s*\|", line, re.IGNORECASE):
                in_tool_table = True
                continue
            if in_tool_table:
                if not line.startswith("|"):
                    in_tool_table = False
                    continue
                if re.match(r"^\|[\s:|-]+\|?\s*$", line):
                    continue
                match = re.match(r"^\|\s*`([a-z][a-z0-9_]+)`\s*\|", line)
                if match:
                    documented.append((path.relative_to(ROOT).as_posix(), match.group(1)))

    check("some tool tables were found", bool(documented), "no markdown tool tables matched")
    unknown = [(doc, name) for doc, name in documented if name not in advertised]
    check("no doc advertises a tool the server does not have", not unknown, str(unknown))


def main() -> int:
    test_create_task_refuses_to_overwrite()
    test_get_system_status_survives_incomplete_frontmatter()
    test_dedup_sees_tasks_created_in_the_same_batch()
    test_create_task_validates_its_inputs()
    test_handlers_survive_null_arguments()
    test_status_updates_do_not_grow_the_file()
    test_docs_do_not_advertise_missing_tools()

    if FAILURES:
        print(f"FAIL: {len(FAILURES)} of {CHECKS} check(s) failed")
        for failure in FAILURES:
            print(f"- {failure}")
        return 1
    print(f"PASS: {CHECKS} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
