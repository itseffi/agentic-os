#!/usr/bin/env python3
"""Regression tests for the eval runners and the shared model client.

Every check here corresponds to a defect that was found and fixed. Without them the fixes
are only demonstrated in a transcript, and several of them broke each other while being
made: closed-world scoring silently disabled the contradiction check, word-boundary anchors
stopped non-word-edged keywords matching, and the routing prose fallback selected the skill
a model had just ruled out.

Plain script, no test framework, matching the other scripts in this directory:

    python3 scripts/test_eval_runners.py
"""

from __future__ import annotations

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import model_client  # noqa: E402
import run_memory_impact_evals as memory  # noqa: E402
import run_routing_evals as routing  # noqa: E402
import run_skill_evals as skills  # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILURES.append(f"{label}" + (f" ({detail})" if detail else ""))


def raises(label: str, fn, exc=model_client.ModelError) -> None:
    try:
        result = fn()
    except exc:
        check(label, True)
    except Exception as other:  # noqa: BLE001
        check(label, False, f"raised {type(other).__name__}: {other}")
    else:
        check(label, False, f"returned {result!r} instead of raising {exc.__name__}")


# --------------------------------------------------------------------------- stub server

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.server.last_request = json.loads(body)
        self.server.last_headers = dict(self.headers)
        mode = self.server.mode
        if mode == "http500":
            payload = b'{"error":{"message":"upstream exploded"}}'
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if mode == "error_object":
            data = {"error": {"message": "invalid api key"}}
        elif mode == "null_content":
            data = {"choices": [{"message": {"content": None}}]}
        elif mode == "no_choices":
            data = {"object": "chat.completion"}
        else:
            data = {"choices": [{"message": {"content": self.server.reply}}]}
        payload = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class Stub:
    def __init__(self):
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.server.mode = "ok"
        self.server.reply = '["tdd"]'
        self.server.last_request = None
        self.server.last_headers = {}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1"

    def set(self, *, mode: str = "ok", reply: str = '["tdd"]'):
        self.server.mode = mode
        self.server.reply = reply

    def stop(self):
        self.server.shutdown()


# --------------------------------------------------------------- routing keyword matching

def test_boundary_matching() -> None:
    """Keywords must not fire inside longer words, and normalisation must cover both sides."""
    for text in ["Write an explanation of the auth flow", "We abandoned that approach",
                 "Retrace your footsteps in the changelog"]:
        check(f"no false positive: {text!r}", routing.route_skills(text) == set(),
              f"selected {sorted(routing.route_skills(text))}")

    # 'migration' is a genuine writing-plans keyword, so this one should still fire.
    check("true positive survives", routing.route_skills("The migration is incomplete") == {"writing-plans"})

    # Lowercasing only the text would make an uppercase rule permanently dead.
    check("uppercase keyword matches",
          bool(re.search(routing._boundary_pattern("Red Green"), "try red green refactor")))
    # \b cannot anchor a keyword whose edge is not a word character.
    for keyword in ["c++", "-v", "+1"]:
        check(f"non-word-edged keyword {keyword!r} matches",
              bool(re.search(routing._boundary_pattern(keyword), f"we use {keyword} here")))


def test_closed_world_scoring() -> None:
    """should_select is the whole expected answer, not a lower bound."""
    cases = json.loads((ROOT / "Evals/skills/routing_cases.json").read_text())["cases"]
    every_skill = set(routing.KEYWORD_RULES)
    scenarios = routing.load_scenarios()

    correct = imprecise = 0
    for case in cases:
        should = set(case.get("should_select", []))
        forbidden = set(case.get("should_not_select", []))
        if routing.route_skills(routing.case_input(case, scenarios)) == should:
            correct += 1
        # A router firing everything not explicitly forbidden used to score full marks.
        if (every_skill - forbidden) == should:
            imprecise += 1
    check("real router passes every case", correct == len(cases), f"{correct}/{len(cases)}")
    check("imprecise router fails every case", imprecise == 0, f"{imprecise} passed")


def test_case_validation() -> None:
    """Nothing else validates routing_cases.json, so malformed cases must be caught here."""
    check("shipped cases are valid", routing.validate_cases(
        json.loads((ROOT / "Evals/skills/routing_cases.json").read_text())["cases"]) == [])

    contradiction = [{"id": "c", "input": "x", "should_select": ["tdd"], "should_not_select": ["tdd"]}]  # noqa: E501
    errors = routing.validate_cases(contradiction)
    check("contradiction rejected", any("both should_select" in e for e in errors), str(errors))

    unknown = [{"id": "u", "input": "x", "should_select": ["verifcation"]}]
    check("unknown skill rejected",
          any("unknown skill" in e for e in routing.validate_cases(unknown)))

    duplicates = [{"id": "d", "input": "x", "should_select": ["tdd"]},
                  {"id": "d", "input": "   ", "should_select": []}]
    errors = routing.validate_cases(duplicates)
    for expected in ["duplicate id", "missing or empty 'input'", "must be a non-empty list"]:
        check(f"rejected: {expected}", any(expected in e for e in errors), str(errors))


# ------------------------------------------------------------------------- model client

def test_auth_header(stub: Stub) -> None:
    """No key means no Authorization header, not `Bearer none`."""
    stub.set(mode="ok", reply="hi")
    for key, expected in [("", None), ("none", None), ("sk-real", "Bearer sk-real")]:
        model_client.query_chat(base_url=stub.base_url, model="m", api_key=key,
                                system_prompt="s", user_input="u")
        sent = stub.server.last_headers.get("Authorization")
        check(f"api_key={key!r} sends {expected!r}", sent == expected, f"sent {sent!r}")


def test_model_client_failures(stub: Stub) -> None:
    """Every failure mode must surface as ModelError, not a traceback or a None."""
    call = lambda: model_client.query_chat(  # noqa: E731
        base_url=stub.base_url, model="stub", api_key="none",
        system_prompt="s", user_input="u")

    stub.set(mode="ok", reply="hello")
    check("happy path returns text", call() == "hello")

    stub.set(mode="http500")
    raises("HTTP 500 raises ModelError", call)
    try:
        stub.set(mode="http500"); call()
    except model_client.ModelError as exc:
        check("HTTP error keeps the API message", "upstream exploded" in str(exc), str(exc))

    stub.set(mode="error_object")
    raises("200 carrying an error object raises ModelError", call)
    try:
        stub.set(mode="error_object"); call()
    except model_client.ModelError as exc:
        check("error object keeps its message", "invalid api key" in str(exc), str(exc))

    stub.set(mode="null_content")
    raises("null content raises rather than returning None", call)

    stub.set(mode="no_choices")
    raises("missing choices raises ModelError", call)


def test_routing_via_model(stub: Stub) -> None:
    """Parse a JSON array; never guess from prose, which inverts negated answers."""
    kwargs = dict(base_url=stub.base_url, model="stub", api_key="none")
    route = lambda: routing.route_skills_via_model("x", **kwargs)  # noqa: E731

    for reply, expected in [('["tdd"]', {"tdd"}),
                            ('["tdd", "verification"]', {"tdd", "verification"}),
                            ("[]", set()),
                            ('Here you go:\n```json\n["tdd"]\n```', {"tdd"})]:
        stub.set(reply=reply)
        check(f"parses {reply[:24]!r}", route() == expected)

    # The removed fallback selected exactly what the model ruled out.
    for reply in ["tdd does not apply here.", "This is not a brainstorming task.",
                  "I think you want the tdd skill here."]:
        stub.set(reply=reply)
        raises(f"no array is an error, not a guess: {reply[:28]!r}", route)

    stub.set(reply='["not-a-real-skill"]')
    raises("unknown skill name is an error", route)


def test_routing_prompt(stub: Stub) -> None:
    """The model must actually be told what it is routing between."""
    stub.set(reply='["tdd"]')
    routing.route_skills_via_model("Implement it first", base_url=stub.base_url,
                                   model="stub", api_key="none")
    system = stub.server.last_request["messages"][0]["content"]
    check("names every skill", all(s in system for s in routing.KEYWORD_RULES))
    check("carries SKILL.md descriptions", "Test-driven development" in system)
    check("carries the AGENTS.md routing policy", "Skill Routing Policy" in system)
    check("user message is the case input",
          stub.server.last_request["messages"][1]["content"] == "Implement it first")


# --------------------------------------------------------------------------- skill evals

def _tdd_case() -> dict:
    return next(c for c in json.loads((ROOT / "Evals/skills/cases/tdd.json").read_text())["cases"]
                if c["id"] == "tdd-code-first-request")


def test_reject_phrases() -> None:
    """A response naming a blocklisted phrase must fail however well it scores."""
    case = _tdd_case()
    correct = json.loads(
        (ROOT / "Evals/skills/fixtures/tdd.json").read_text())["responses"]["tdd-code-first-request"]
    blunt = "Ship the feature, tests can come later."

    good = skills._evaluate_case(skill="tdd", case=case, response=correct, threshold=0.6)
    check("correct fixture passes", good.passed and not good.rejected)

    bad = skills._evaluate_case(skill="tdd", case=case, response=blunt, threshold=0.6)
    check("blocklisted phrase fails the case", not bad.passed)
    check("failure names the phrase", bad.rejected == ["tests can come later"], str(bad.rejected))


def test_overlap_judge_cannot_detect_stance() -> None:
    """Characterisation test for a KNOWN GAP. These responses pass and should not.

    An earlier version of this file asserted the guard worked by feeding it a sentence built
    out of the blocklist itself, which proved only that the blocklist matches the blocklist.
    Realistic inversions discuss the skill in its own vocabulary while advising against it,
    name none of the blocked phrases, and score 0.75 to 1.00 on token overlap.

    If these start failing, the metric has improved: delete this test and update item 18,
    which currently overstates how much the reject lists cover.
    """
    case = _tdd_case()
    realistic_inversions = [
        "You could do the red-green-refactor sequence with a failing test first, but for this "
        "small change I'd write the code and add a test after.",
        "Normally TDD enforces a failing test first and uses the red green refactor sequence; "
        "here that's overkill, so implement first.",
        "The red green refactor sequence with a failing test first uses time we don't have. "
        "Implement, then test.",
    ]
    for response in realistic_inversions:
        result = skills._evaluate_case(skill="tdd", case=case, response=response, threshold=0.6)
        check("KNOWN GAP: overlap passes a realistic inversion", result.passed,
              "it now fails, so the gap is closed: remove this test and correct item 18")
        check("KNOWN GAP: reject list does not catch it", result.rejected is None,
              f"now caught by {result.rejected}")


STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "in", "is", "it", "no",
             "not", "of", "on", "or", "s", "that", "the", "this", "to", "with", "you", "your"}


def test_skill_prompt_is_not_contaminated() -> None:
    """The scaffolding must name the skill without handing over the scored vocabulary.

    The skill's own SKILL.md description is legitimate context that a real agent also sees,
    and it necessarily shares words with the expectations, so it is excluded here. What must
    stay clean is the wording around it. The prompt this replaced said "include concrete
    verification-oriented guidance", which supplied a scored token unprompted.
    """
    check("names the skill under test", "tdd" in skills._system_prompt("tdd"))
    check("carries the skill description", "Test-driven development" in skills._system_prompt("tdd"))
    check("old contaminating phrase is gone",
          "verification-oriented" not in skills._system_prompt("verification"))

    for skill in ["verification", "writing-plans", "tdd"]:
        prompt = skills._system_prompt(skill)
        scaffolding = skills._tokens(prompt.replace(skills._skill_brief(skill), ""))
        scored: set[str] = set()
        for case in json.loads((ROOT / f"Evals/skills/cases/{skill}.json").read_text())["cases"]:
            for expectation in case["expected"]:
                scored |= skills._tokens(expectation)
        leaked = {t for t in scored & scaffolding if len(t) > 2 and t not in STOPWORDS}
        check(f"{skill} scaffolding leaks no scored vocabulary", not leaked, f"leaked {sorted(leaked)}")


def test_every_self_referential_axis_is_disclosed(stub: Stub) -> None:
    """Every axis that scores something the repo wrote for itself must say so.

    Caveating only the judge left `--provider fixture --judge openai` printing nothing while
    scoring canned fixture text, and left the memory runner silent though both sides of its
    comparison come from its cases file.
    """
    import subprocess

    def run(script: str, args: list[str], results_dir: str):
        # Read the path the runner prints rather than diffing a glob. The glob silently
        # yielded nothing when a run in the same second reused a filename, turning a real
        # collision into a KeyError three lines later instead of a clear failure.
        proc = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                              capture_output=True, text=True, cwd=ROOT)
        line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULTS:")), None)
        if line is None:
            check(f"{script}: printed a RESULTS path", False, proc.stdout[:160])
            return proc.stdout, {}
        path = ROOT / line.split("RESULTS:", 1)[1].strip()
        payload = json.loads(path.read_text())
        path.unlink()
        return proc.stdout, payload

    skills_dir, memory_dir = "Evals/skills/results", "Evals/memory/results"
    model = ["--model", "stub", "--base-url", stub.base_url]
    stub.set(mode="ok", reply="YES")

    matrix = [
        ("run_skill_evals.py", ["--skill", "tdd"], skills_dir, ["provider_caveat", "judge_caveat"]),
        ("run_skill_evals.py", ["--skill", "tdd", "--judge", "openai", *model], skills_dir,
         ["provider_caveat"]),
        ("run_routing_evals.py", [], skills_dir, ["provider_caveat"]),
        ("run_memory_impact_evals.py", [], memory_dir, ["provider_caveat"]),
    ]
    for script, args, results_dir, expected_keys in matrix:
        label = f"{script} {' '.join(a for a in args if not a.startswith('http'))}".strip()
        stdout, payload = run(script, args, results_dir)
        for key in expected_keys:
            check(f"{label}: {key} is set", bool(payload.get(key)), f"got {payload.get(key)!r}")
        notes = [line for line in stdout.splitlines() if line.startswith("NOTE:")]
        check(f"{label}: prints one NOTE per caveat",
              len(notes) == len(expected_keys), f"{len(notes)} notes, expected {len(expected_keys)}")
        # The printed text and the recorded text must be the same string, or they drift.
        printed = {" ".join(n[len("NOTE:"):].split()) for n in notes}
        recorded = {" ".join(str(payload[k]).split()) for k in expected_keys}
        check(f"{label}: printed and recorded caveats match", printed == recorded,
              f"printed {printed} vs recorded {recorded}")

    # The one combination with nothing self-referential must stay quiet.
    stub.set(mode="ok", reply="YES")
    stdout, payload = run("run_routing_evals.py",
                          ["--provider", "openai", *model], skills_dir)
    check("routing --provider openai carries no caveat", payload.get("provider_caveat") is None,
          f"got {payload.get('provider_caveat')!r}")
    check("routing --provider openai prints no NOTE",
          not [l for l in stdout.splitlines() if l.startswith("NOTE:")], stdout[:120])


def test_model_settings_are_required_not_defaulted() -> None:
    """Missing model settings must fail fast, not silently target a dead localhost.

    --model was validated and --base-url was not, so a misconfigured run produced a red eval
    full of connection errors instead of one line saying what was missing.
    """
    import subprocess

    def run(script: str, args: list[str]) -> tuple[int, str]:
        proc = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                              capture_output=True, text=True, cwd=ROOT,
                              env={"PATH": "/usr/bin:/bin"})
        return proc.returncode, proc.stdout + proc.stderr

    for script, args, expect in [
        ("run_routing_evals.py", ["--provider", "openai"], ["--model", "--base-url"]),
        ("run_routing_evals.py", ["--provider", "openai", "--model", "m"], ["--base-url"]),
        ("run_skill_evals.py", ["--judge", "openai"], ["--model", "--base-url"]),
        ("run_skill_evals.py", ["--provider", "openai", "--model", "m"], ["--base-url"]),
    ]:
        code, out = run(script, args)
        label = f"{script} {' '.join(args)}"
        check(f"{label}: exits 2", code == 2, f"exit {code}: {out[:120]}")
        for flag in expect:
            check(f"{label}: names {flag}", flag in out, out[:160])
        check(f"{label}: does not attempt a request", "Connection refused" not in out, out[:160])

    # The help must not claim these are only for --provider, since --judge needs them too.
    # Match inside the options block, not the wrapped usage line at the top, and collapse
    # argparse's line wrapping before looking for the phrase.
    _, help_text = run("run_skill_evals.py", ["--help"])
    options = help_text.split("options:", 1)[-1]
    entries = re.split(r"\n(?=\s{2}-)", options)
    for flag in ["--base-url", "--model"]:
        entry = next((e for e in entries if e.strip().startswith(flag)), "")
        collapsed = " ".join(entry.split())
        check(f"help for {flag} mentions --judge openai", "--judge openai" in collapsed,
              collapsed[:140] or "entry not found")


def test_no_duplicated_prompts_across_suites() -> None:
    """The same scenario must live in one place, not be copy-pasted between suites.

    Three routing cases previously duplicated a skill case: one verbatim, two with wording
    that had already drifted apart.
    """
    import difflib

    scenarios = routing.load_scenarios()
    prompts: list[tuple[str, str, str]] = []
    for case in json.loads((ROOT / "Evals/skills/routing_cases.json").read_text())["cases"]:
        prompts.append(("routing", case["id"], routing.case_input(case, scenarios)))
    for path in sorted((ROOT / "Evals/skills/cases").glob("*.json")):
        for case in json.loads(path.read_text())["cases"]:
            prompts.append((f"skill:{path.stem}", case["id"], routing.case_input(case, scenarios)))

    for i, (suite_a, id_a, text_a) in enumerate(prompts):
        for suite_b, id_b, text_b in prompts[i + 1:]:
            if suite_a == suite_b:
                continue
            ratio = difflib.SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()
            # Identical is fine: it means both reference the same scenario id. Near-identical
            # is the smell, because it means two copies that have started to diverge.
            check(f"{id_a} vs {id_b}: not a drifted copy", ratio < 0.95 or text_a == text_b,
                  f"similarity {ratio:.2f}: {text_a!r} vs {text_b!r}")

    shared = [p for p in prompts if p[2] in scenarios.values()]
    check("shared scenarios are actually referenced", len(shared) >= 6, f"{len(shared)} references")


def test_scenario_references_are_validated() -> None:
    """A case must supply a prompt exactly one way, and a bad scenario id must be caught."""
    both = [{"id": "b", "input": "x", "scenario": "code-first-request", "should_select": ["tdd"]}]
    check("input and scenario together rejected",
          any("not both" in e for e in routing.validate_cases(both)),
          str(routing.validate_cases(both)))

    unknown = [{"id": "u", "scenario": "no-such-scenario", "should_select": ["tdd"]}]
    check("unknown scenario rejected",
          any("unknown scenario" in e for e in routing.validate_cases(unknown)),
          str(routing.validate_cases(unknown)))

    neither = [{"id": "n", "should_select": ["tdd"]}]
    check("missing prompt rejected",
          any("missing or empty" in e for e in routing.validate_cases(neither)),
          str(routing.validate_cases(neither)))


def test_scoring_per_runner() -> None:
    """Each runner scores differently; pin what each one actually means by a pass."""
    # Routing: exact set equality, no partial credit either way.
    for selected, should, expected in [({"tdd"}, {"tdd"}, True), (set(), {"tdd"}, False),
                                       ({"tdd", "verification"}, {"tdd"}, False),
                                       (set(), set(), True)]:
        ok = not (should - selected) and not (selected - should)
        check(f"routing {sorted(selected)} vs {sorted(should)}", ok is expected)

    # Skill evals: unordered token ratio. Order-blindness is inherent to the metric and is
    # pinned by test_overlap_judge_cannot_detect_stance; what must not happen is a free pass.
    check("skill: exact match scores 1.0",
          skills._score_expectation("enforces failing test first", "enforces failing test first") == 1.0)
    check("skill: partial match is a ratio",
          skills._score_expectation("a b c d e", "a b c") == 0.6)
    raises("skill: empty expectation is an error, not a 1.0",
           lambda: skills._score_expectation("", "anything"), ValueError)

    # Memory: contiguous phrase, not a bag of words.
    check("memory: exact phrase matches",
          memory._contains_phrase("verification before claiming", "verification before claiming"))
    check("memory: shuffled words do not match",
          not memory._contains_phrase("claiming verification before", "verification before claiming"))
    check("memory: scattered words do not match",
          not memory._contains_phrase(
              "before I claim anything I run verification on the claiming step",
              "verification before claiming"))
    raises("memory: empty phrase is an error, not True",
           lambda: memory._contains_phrase("anything", ""), ValueError)


def test_no_vacuous_passes() -> None:
    """A case with nothing to assert must be rejected, not scored as a pass."""
    empty_lists = [{"id": "v", "input": "i", "baseline_response": "b",
                    "memory_search_response": "w",
                    "expected_when_enabled": [], "expected_missing_in_baseline": []}]
    check("memory: empty expectation lists rejected",
          any("vacuously" in e for e in memory.validate_cases(empty_lists)),
          str(memory.validate_cases(empty_lists)))

    empty_phrase = [{"id": "p", "input": "i", "baseline_response": "b",
                     "memory_search_response": "w", "expected_when_enabled": ["  "]}]
    check("memory: empty phrase rejected",
          any("empty phrase" in e for e in memory.validate_cases(empty_phrase)),
          str(memory.validate_cases(empty_phrase)))

    missing_field = [{"id": "f", "input": "i", "expected_when_enabled": ["x"]}]
    errors = memory.validate_cases(missing_field)
    for field in ("baseline_response", "memory_search_response"):
        check(f"memory: missing {field} rejected", any(field in e for e in errors), str(errors))

    check("memory: shipped cases are valid",
          memory.validate_cases(json.loads(
              (ROOT / "Evals/memory/cases.json").read_text())["cases"]) == [])


def test_results_paths_do_not_collide() -> None:
    """Two runs in the same second must not overwrite each other."""
    import subprocess

    written = []
    for _ in range(3):
        proc = subprocess.run([sys.executable, str(SCRIPTS / "run_routing_evals.py")],
                              capture_output=True, text=True, cwd=ROOT)
        line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULTS:")), "")
        written.append(line.split("RESULTS:", 1)[1].strip() if line else None)

    check("three rapid runs report three paths", all(written), str(written))
    check("three rapid runs do not share a path", len(set(written)) == 3, str(written))
    for rel in written:
        if rel:
            path = ROOT / rel
            check(f"{rel} exists on disk", path.exists())
            if path.exists():
                path.unlink()


def test_error_messages_name_an_absolute_path() -> None:
    """A validation error must say which file it read, unambiguously.

    A repo-relative path is unattributable when the runner executes from a copy: a synthetic
    bad file under /tmp reported `Evals/memory/cases.json`, which reads as though the
    checked-in file were broken.
    """
    import subprocess
    import tempfile

    for script, rel, payload in [
        ("run_memory_impact_evals.py", "Evals/memory/cases.json",
         {"version": 1, "cases": [{"id": "vacuous", "input": "x", "baseline_response": "b",
                                   "memory_search_response": "w",
                                   "expected_when_enabled": [],
                                   "expected_missing_in_baseline": []}]}),
        ("run_routing_evals.py", "Evals/skills/routing_cases.json",
         {"version": 1, "cases": [{"id": "c", "input": "x", "should_select": ["tdd"],
                                   "should_not_select": ["tdd"]}]}),
    ]:
        sandbox = Path(tempfile.mkdtemp())
        (sandbox / "scripts").mkdir()
        for helper in (script, "eval_io.py", "model_client.py"):
            (sandbox / "scripts" / helper).write_text((SCRIPTS / helper).read_text())
        target = sandbox / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload))

        proc = subprocess.run([sys.executable, str(sandbox / "scripts" / script)],
                              capture_output=True, text=True, cwd=ROOT)
        check(f"{script}: sandboxed bad file exits 2", proc.returncode == 2,
              f"exit {proc.returncode}: {proc.stdout[:120]}")
        check(f"{script}: error names the sandbox path", str(sandbox) in proc.stdout,
              proc.stdout[:200])
        check(f"{script}: error does not read as the repo's file",
              str(ROOT / rel) not in proc.stdout, proc.stdout[:200])


def main() -> int:
    stub = Stub()
    try:
        test_boundary_matching()
        test_closed_world_scoring()
        test_case_validation()
        test_auth_header(stub)
        test_model_client_failures(stub)
        test_routing_via_model(stub)
        test_routing_prompt(stub)
        test_reject_phrases()
        test_overlap_judge_cannot_detect_stance()
        test_every_self_referential_axis_is_disclosed(stub)
        test_model_settings_are_required_not_defaulted()
        test_no_duplicated_prompts_across_suites()
        test_scenario_references_are_validated()
        test_scoring_per_runner()
        test_no_vacuous_passes()
        test_results_paths_do_not_collide()
        test_error_messages_name_an_absolute_path()
        test_skill_prompt_is_not_contaminated()
    finally:
        stub.stop()

    if FAILURES:
        print(f"FAIL: {len(FAILURES)} of {CHECKS} check(s) failed")
        for failure in FAILURES:
            print(f"- {failure}")
        return 1
    print(f"PASS: {CHECKS} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
