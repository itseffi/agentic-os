# Pull Request: AI-Assisted Complex Repo Auto-Setup

## Title

feat: Add AI-assisted setup path for complex repos (`setup.sh --ai`)

## Summary

Adds an AI-installer skill that enables intelligent, complexity-aware setup for existing repositories. Instead of the current one-size-fits-all questionnaire, users can run `setup.sh --ai` to bootstrap an AI skill that analyzes their repo structure, classifies its complexity (Zero/Simple/Multi/Complex), proposes configuration proportional to detected needs, previews everything as unified diffs, and writes only after explicit approval.

**The paradigm shift:** Setup is no longer a script that asks questions and writes files. Setup IS the AI reading the repo and configuring itself. The script becomes a bootstrap; the AI becomes the installer.

## Motivation

Agentic-os today assumes a greenfield personal workspace. But most developers who discover it already have a project — often a complex one with multiple concerns, existing AI configurations, team structures, and cross-domain relationships. They cannot use agentic-os without manually figuring out how to map their repo into the OS's expectations.

This feature makes agentic-os smart enough to meet users where they are — from a student's Flask project to an architect's multi-team monorepo.

## What's Included

### New files

- `.agents/skills/agentic-os-setup/SKILL.md` — Orchestrator (mode detection, scanning, classification, proposal, approval, write protocol)
- `.agents/skills/agentic-os-setup/agents/openai.yaml` — Agent Skills open standard metadata (routing, description)
- `.agents/skills/agentic-os-setup/catalog.md` — Signal catalog (15+ filesystem patterns and their meanings)
- `.agents/skills/agentic-os-setup/templates/` — Rule templates (persona-routing, scope-isolation, cross-reference, naming-enforcement, quality-gates)
- `.agents/skills/agentic-os-setup/adapters/` — Runtime adapters (claude.md, cursor.md, cline.md, antigravity.md)
- `.agents/skills/agentic-os-setup/examples/` — Calibration examples (simple-output.md, complex-output.md)
- `CONTRIBUTING.md` — Contributor guide for extending signals, templates, and adapters

### New files (test infrastructure)

- `pytest.ini` — Pytest configuration (test paths, JUnit XML output to `tests/results/python/report.xml`)
- `tests/test_setup.sh` — Shell test runner (29 tests, validates flag parsing and routing)
- `tests/test_content.py` — Python content validator (24 tests, validates structure and schema)
- `tests/conftest.py` — Pytest hook for plaintext report generation (`tests/results/python/report.txt`)
- `examples/uj-1-node-monorepo/` — Test fixture: Node.js monorepo with 3 Cursor rules
- `examples/uj-2-architect-monorepo/` — Test fixture: Complex multi-concern with BMAD, 10 Cursor rules
- `examples/uj-3-flask-simple/` — Test fixture: Simple Flask project, no AI config
- `examples/uj-4-rust-antigravity/` — Test fixture: Rust workspace with existing AGENTS.md

### Modified files

- `setup.sh` — Adds `--ai`, `--runtime`, `--dry-run`, `--remove`, `--track`, `--target`, `--auto`, `--help` flags
- `README.md` — Documents AI-assisted setup path, updated architecture diagram, new mermaid flow diagram, runtime compatibility
- `.gitignore` — Adds `tests/results/` exclusion

## Key Design Decisions

1. **AI-as-installer paradigm** — The shell script bootstraps; the AI executes. All intelligence lives in SKILL.md.
2. **4-tier complexity model** — Zero/Simple/Multi/Complex gates output volume proportionally.
3. **Non-destructive by design** — Never modifies user files. Creates companion files or append-only managed blocks.
4. **Multi-runtime support** — Claude Code, Cursor, Cline, Antigravity. Same intent, native format per tool.
5. **Backwards compatible** — `setup.sh` without flags = unchanged behavior. Zero regression risk.
6. **Clean uninstall** — Manifest-tracked files, `setup.sh --remove` restores repo to pre-setup state.
7. **Target directory** — `--target <path>` enables running against any repo without cd. setup.sh bootstraps the workspace (copies skills, workflows, dirs) into the target, so the AI skill runs locally with no cross-repo references.
8. **Auto-approval mode** — `--auto` skips interactive approval (requires explicit `--runtime`). Shows preview then writes.
9. **Dual test strategy** — Shell tests for CLI behavior, Python/pytest for content validation. Real repo fixtures for UJ-1 through UJ-4.

## Planning Methodology

This feature was planned using the **BMad Method** (Build Method for AI-assisted Development) — a structured workflow that produces traceable artifacts from brainstorming through implementation readiness:

- **Brainstorming** — 28 ideas across 3 phases, evaluated with structured reasoning frameworks
- **PRD** — 31 functional requirements, 7 non-functional requirements, 4 user journeys, success metrics
- **Architecture** — 11 decisions, FR coverage matrix, interface contracts for parallel development
- **Epics & Stories** — 7 epics, 27 stories with Given/When/Then acceptance criteria
- **Adversarial Review** — 15 findings identified and resolved before implementation
- **Implementation Readiness** — 100% FR coverage validated, 0 critical issues

Planning artifacts are in `_bmad-output/prd-ai-assisted-setup-2026-06-20/`.

## Supported Runtimes

Valid `--runtime` values: `claude`, `cursor`, `cline`, `antigravity`

| Runtime ID | Tool | Output format | Pre-existing behavior |
|-----------|------|--------------|----------------------|
| `claude` | Claude Code | CLAUDE.md (or CLAUDE-agentic-os.md if exists) | Companion file |
| `cursor` | Cursor | .cursor/rules/NNN-agentic-os.mdc | New numbered file |
| `cline` | Cline | .clinerules (or .clinerules-agentic-os if exists) | Companion file |
| `antigravity` | Antigravity | AGENTS.md | Managed block append |

Adding a new runtime requires: a new adapter file in `adapters/`, an update to `VALID_RUNTIMES` in setup.sh, and a row in this table.

## How to Test

```bash
# AI-assisted setup (all runtimes)
./setup.sh --ai

# Target specific runtimes
./setup.sh --ai --runtime claude,cursor

# Preview without writing
./setup.sh --ai --dry-run

# Run against a different directory (bootstraps workspace + skill into target)
./setup.sh --ai --target ./my-project --runtime claude

# Auto-approval mode (unattended, requires explicit --runtime)
./setup.sh --ai --auto --runtime claude,cursor

# Clean removal
./setup.sh --remove

# Classic setup (unchanged)
./setup.sh

# Run tests
sh tests/test_setup.sh
pytest tests/test_content.py
```

Then invoke the AI skill in your runtime of choice and verify:
- Correct complexity tier detected
- Appropriate output proposed (not over/under-generating)
- Dry-run shows accurate diffs
- No conflicts with existing configs
- Generated files are valid for their target runtime

## Verification Status

**Runtimes tested — all four, against a real Complex-tier repo:**

The architect-docs monorepo (BMAD framework, 50+ existing skills, `.cursor/rules/` 000–805, multi-domain `docs/`, ~176 work items) was cloned four times and the `agentic-os-setup` skill was run end-to-end against each clone, one runtime per clone. Every run classified Complex (driven by `_bmad/`), deferred persona routing to BMAD, and produced a lean AGENTS.md within the context budget with procedures relocated to an emitted `task-management` skill. Results verified on disk (real byte counts, not estimates):

| Runtime | AGENTS.md | Within 10k? | Emitted skill | Per-runtime file | BMAD deferral |
|---------|-----------|-------------|---------------|------------------|---------------|
| Claude | 5,178 chars | ✅ | task-management | CLAUDE-agentic-os.md (companion; existing CLAUDE.md untouched) | ✅ |
| Cursor | 4,815 chars | ✅ | task-management | .cursor/rules/806, 807 (no collision with 000–805, specific globs) | ✅ |
| Cline | 4,237 chars | ✅ | task-management | .clinerules (new; points to skill, no inlined procedures) | ✅ |
| Antigravity | 4,206 chars | ✅ | task-management | AGENTS.md managed block (valid sha256 start/end markers) | ✅ |

In every case: AGENTS.md carries a "Skills & Workflows" index and contains zero inlined procedure sections (backlog/daily/maintenance/helpful-prompts all live in the emitted skill); `orchestration-model` was correctly NOT emitted (BMAD owns personas); the manifest records `complexity_tier: complex`, `detected_frameworks: ["bmad"]`, and every generated file for clean `--remove`. Track-vs-gitignore was inferred per-repo (tracked when shared AI configs are already committed; gitignored when signals indicate a private personal workspace).

This is the same outcome that motivated the change: before, the skill generated a ~4–5 KB AGENTS.md packed with the full operational manual inline. Now AGENTS.md holds only always-on rules + an index, and the bulky procedures load on demand — so every turn is cheaper without losing any rule.

**Unit tests:**
- ✅ Shell tests: 29/29 passed (flag parsing, routing, --remove, --target, --auto)
- ✅ Python tests: 31/31 passed (manifest schema, .mdc frontmatter, glob specificity, managed blocks, numbering, **+ new context-budget / progressive-disclosure contract tests** that lock the lean-AGENTS.md shape so it can't silently regress)
- ✅ Skill evals 6/6, routing evals 5/5, eval-case validation pass

## Example Output (Complex Tier)

Tested against the architect-docs monorepo (BMAD framework, 50+ existing skills, `.cursor/rules/`, multi-domain `docs/`), Claude runtime:

```
Classification: Complex tier (driven by _bmad/ framework presence, multiple concern folders, 4+ AI config systems)

Files written:
  AGENTS.md          — 5.2 KB — Always-on rules ONLY (scope isolation, cross-refs,
                                naming, priority levels, verification) + Skills & Workflows index
  .agents/skills/task-management/SKILL.md — 4.1 KB — Emitted on-demand skill: task format,
                                backlog/daily/weekly/maintenance workflows, session evals (loads only when invoked)
  .agents/skills/task-management/agents/openai.yaml — routing metadata
  GOALS.md           — 3.9 KB — AI-inferred professional goals and priorities
  CLAUDE-agentic-os.md — 1.5 KB — Companion config (existing CLAUDE.md untouched)
  .agents/.agentic-os-manifest.json — Manifest for tracking/removal

AGENTS.md stayed within the ~10k context budget; step-by-step procedures were relocated to
the task-management skill rather than inlined.
Framework coexistence: Persona routing deferred to BMAD (orchestration-model skill not emitted).
Track decision: tracked (shared AI configs already committed in this repo).
```

## Reviewer Ask

Beyond validating the documented test cases, we'd appreciate reviewers testing against their own real-world repos — especially:
- Repos with existing AI configurations (Cursor rules, CLAUDE.md, .clinerules)
- Monorepos with workspaces (npm, Cargo, Go)
- Repos with non-standard structures not covered by the signal catalog
- Edge cases: empty repos, repos with only binary files, very large repos

Please report unexpected classifications, missing signals, or over/under-generation in the review.

## Dependencies

- `jq` required for `--remove` manifest parsing (setup.sh checks and guides if missing)
- No other external dependencies

## Out of Scope (Phase 2+)

- Re-run with delta merging (requires managed block checksum infrastructure)
- Team-scoped context isolation
- BMAD deep integration (v1 defers to BMAD when detected)
- Runtimes beyond v1 set (Copilot, Kiro, Codex, Pi)

## License

All contributions under [CC BY-NC-SA 4.0](LICENSE), consistent with the existing project license.
