# Signal Catalog

## Purpose

Structured reference of known filesystem patterns and their meanings. The AI uses this catalog to anchor detection during repo scanning. Patterns not listed here do not prevent the AI from reasoning about novel structures — this is a reference, not a hard gate.

---

## Signal: .cursor/rules/

**Pattern:** Directory `.cursor/rules/` exists with `.mdc` files
**Indicates:** Existing Cursor AI configuration
**Complexity impact:** +1 existing AI config
**Setup implications:**
- Scan existing rules for glob patterns (collision detection)
- Detect numbering convention (respect existing band)
- Generate agentic-os rule in next available number slot
**Coexistence:** Additive only — never modify existing rules

---

## Signal: CLAUDE.md

**Pattern:** File `CLAUDE.md` at repo root
**Indicates:** Existing Claude Code configuration
**Complexity impact:** +1 existing AI config
**Setup implications:**
- Do not overwrite — create `CLAUDE-agentic-os.md` as companion file
- Reference companion from proposal
**Coexistence:** Companion file pattern

---

## Signal: .clinerules

**Pattern:** File `.clinerules` at repo root
**Indicates:** Existing Cline configuration
**Complexity impact:** +1 existing AI config
**Setup implications:**
- Do not overwrite — create `.clinerules-agentic-os` as companion file
**Coexistence:** Companion file pattern

---

## Signal: AGENTS.md

**Pattern:** File `AGENTS.md` at repo root
**Indicates:** Existing agent instructions (possibly Antigravity or hand-written)
**Complexity impact:** +1 existing AI config
**Setup implications:**
- Extend with managed block (append below existing content)
- Never replace or modify existing content
**Coexistence:** Managed block append pattern

---

## Signal: _bmad/

**Pattern:** Directory `_bmad/` at repo root
**Indicates:** BMad agent framework installed
**Complexity impact:** Automatically Complex tier (framework presence)
**Setup implications:**
- Defer persona routing entirely to BMAD
- Only generate: scope isolation, cross-reference, naming enforcement
- Explain deferral in proposal
**Coexistence:** Defer persona ownership

---

## Signal: .claude/

**Pattern:** Directory `.claude/` at repo root
**Indicates:** Claude Code project configuration or skills
**Complexity impact:** +1 existing AI config
**Setup implications:**
- Inspect for skills/ subdirectory
- Note existing configuration approach
**Coexistence:** Do not modify contents

---

## Signal: package.json

**Pattern:** File `package.json` at repo root
**Indicates:** Node.js/JavaScript project
**Complexity impact:** +1 concern folder (if workspaces found: +1 per workspace root)
**Setup implications:**
- Check for `workspaces` field (monorepo indicator → Multi or Complex)
- Detect test framework (jest, vitest, mocha) for quality gate template
- Note scripts for build/test/lint commands
**Coexistence:** Read-only reference

---

## Signal: pyproject.toml

**Pattern:** File `pyproject.toml` at repo root
**Indicates:** Python project (modern packaging)
**Complexity impact:** +1 concern folder
**Setup implications:**
- Check for monorepo tools (hatch workspaces, pants)
- Detect test framework (pytest, unittest)
- Note linting tools (ruff, black, mypy)
**Coexistence:** Read-only reference

---

## Signal: Cargo.toml

**Pattern:** File `Cargo.toml` at repo root
**Indicates:** Rust project
**Complexity impact:** +1 concern folder (if workspace: +1 per member)
**Setup implications:**
- Check for `[workspace]` section (monorepo indicator)
- Note crate structure for scope isolation
**Coexistence:** Read-only reference

---

## Signal: go.mod

**Pattern:** File `go.mod` at repo root
**Indicates:** Go project
**Complexity impact:** +1 concern folder
**Setup implications:**
- Check for go.work (multi-module workspace)
- Note module path for naming conventions
**Coexistence:** Read-only reference

---

## Signal: terraform/

**Pattern:** Directory `terraform/` or `infra/` with `.tf` files
**Indicates:** Infrastructure-as-Code component
**Complexity impact:** +1 concern folder
**Setup implications:**
- Distinct concern domain (infrastructure vs application code)
- Consider scope isolation between IaC and app code
- Note state backend for quality gate template
**Coexistence:** Read-only reference

---

## Signal: docker-compose.yml

**Pattern:** File `docker-compose.yml` or `docker-compose.yaml` at root
**Indicates:** Multi-service local development setup
**Complexity impact:** +1 concern folder (if 3+ services)
**Setup implications:**
- Indicates multiple services that may need scope isolation
- Service names can inform persona routing
**Coexistence:** Read-only reference

---

## Signal: .github/

**Pattern:** Directory `.github/` with workflows/
**Indicates:** GitHub Actions CI/CD pipeline
**Complexity impact:** Neutral (doesn't affect tier directly)
**Setup implications:**
- Note CI structure for quality gate template
- Detect workflow organization patterns
**Coexistence:** Read-only reference

---

## Signal: docs/

**Pattern:** Directory `docs/` at root
**Indicates:** Documentation as a distinct concern
**Complexity impact:** +1 concern folder
**Setup implications:**
- Potential scope isolation (docs vs code)
- May indicate architectural documentation needs
**Coexistence:** Read-only reference

---

## Signal: Makefile

**Pattern:** File `Makefile` at repo root
**Indicates:** Build automation (often multi-concern orchestration)
**Complexity impact:** Neutral (indicator of maturity, not complexity)
**Setup implications:**
- Read target names for project structure hints
- Note common targets (build, test, lint, deploy)
**Coexistence:** Read-only reference

---

## Signal: src/

**Pattern:** Directory `src/` at repo root (without other concern folders)
**Indicates:** Single-purpose project with conventional structure
**Complexity impact:** Neutral (alone = Simple tier cap)
**Setup implications:**
- If `src/` is the only concern folder, tier should not exceed Simple
- Common in libraries, CLI tools, single applications
**Coexistence:** Read-only reference

---

## Usage Context

The AI reads this catalog during the scanning phase to:
1. Identify which signals are present in the target repo
2. Map each signal to its complexity dimension contribution
3. Determine coexistence behavior before proposing any output
4. Anchor decisions in documented patterns rather than hallucination

Signals not in this catalog can still be reasoned about — this catalog accelerates recognition of common patterns but does not limit the AI's analytical capability.
