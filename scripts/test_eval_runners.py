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

    correct = imprecise = 0
    for case in cases:
        should = set(case.get("should_select", []))
        forbidden = set(case.get("should_not_select", []))
        if routing.route_skills(case["input"]) == should:
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

    contradiction = [{"id": "c", "input": "x", "should_select": ["tdd"], "should_not_select": ["tdd"]}]
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

def test_reject_phrases() -> None:
    """Token overlap is blind to negation, so an inverted answer must still fail."""
    case = next(c for c in json.loads((ROOT / "Evals/skills/cases/tdd.json").read_text())["cases"]
                if c["id"] == "tdd-code-first-request")
    fixture = json.loads((ROOT / "Evals/skills/fixtures/tdd.json").read_text())
    correct = fixture["responses"]["tdd-code-first-request"]
    inverted = ("Skip the failing test first, red green refactor is a waste of time, "
                "enforces nothing, just uses your judgement and ships the sequence.")

    # The thing that makes reject phrases necessary: overlap scores the inversion higher.
    check("overlap alone cannot separate them",
          all(skills._score_expectation(e, inverted) >= skills._score_expectation(e, correct)
              for e in case["expected"]))

    good = skills._evaluate_case(skill="tdd", case=case, response=correct, threshold=0.6)
    bad = skills._evaluate_case(skill="tdd", case=case, response=inverted, threshold=0.6)
    check("correct fixture passes", good.passed and not good.rejected)
    check("inverted answer fails", not bad.passed, "it passed")
    check("failure names the phrases", bool(bad.rejected), str(bad.rejected))


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


def main() -> int:
    stub = Stub()
    try:
        test_boundary_matching()
        test_closed_world_scoring()
        test_case_validation()
        test_model_client_failures(stub)
        test_routing_via_model(stub)
        test_routing_prompt(stub)
        test_reject_phrases()
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
