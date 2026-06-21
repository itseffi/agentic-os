---
title: AI-Assisted Complex Repo Auto-Setup
status: draft
created: 2026-06-20
updated: 2026-06-20
---

# PRD: AI-Assisted Complex Repo Auto-Setup

## 0. Document Purpose

This PRD defines the requirements for extending agentic-os with an AI-assisted setup path that detects existing repository structure, classifies complexity, and generates appropriately-scoped configuration — without breaking the existing `setup.sh` questionnaire flow. It targets the upstream maintainer and contributors of itseffi/agentic-os as primary audience, and downstream users who will invoke the feature. The PRD uses stable FR IDs for traceability into architecture and implementation.

## 1. Vision

Agentic-os today assumes a greenfield personal workspace: five questions, a GOALS.md, some directories. But most developers who discover it already have a project — often a complex one with multiple concerns, existing AI configurations, team structures, and cross-domain relationships. They cannot use agentic-os without manually figuring out how to map their repo into the OS's expectations.

This feature makes agentic-os smart enough to meet users where they are. By shipping an AI-installer skill alongside the existing setup script, users invoke their AI tool of choice (Claude Code, Cursor, Cline, or Antigravity) and the AI analyzes the repo, proposes configuration proportional to detected complexity, previews everything as a diff, and only writes after human approval. The result: agentic-os works for a solo dev's weekend project AND an architect's multi-team monorepo — same tool, different output depth.

The paradigm shift: setup is no longer a script that asks questions and writes files. Setup IS the AI reading the repo and configuring itself. The script becomes a bootstrap; the AI becomes the installer.

## 2. Target User

### 2.1 Jobs To Be Done

- I want my AI tools to immediately understand my existing project structure without me manually writing config files (functional)
- I want to adopt agentic-os on an existing repo without breaking my current AI setup (functional, emotional — fear of disruption)
- I want configuration proportional to my repo's actual complexity, not a one-size-fits-all template (functional)
- I want to see what will change before anything is written, so I maintain control (emotional — trust, autonomy)
- I want to cleanly remove agentic-os if it doesn't work for me (emotional — commitment anxiety)

### 2.2 Non-Users (v1)

- Teams wanting fully automated CI/CD pipeline integration (multi-stage, artifact caching, cross-repo orchestration) — v1's `--auto` supports single-repo unattended runs but not full CI/CD workflows
- Users who only use the classic questionnaire and never want AI involvement — classic path remains untouched
- Users of runtimes not in v1 scope (GitHub Copilot, Kiro, Codex, Pi) — future phases

### 2.3 Key User Journeys

**UJ-1. Alex sets up agentic-os on their existing Node.js monorepo from Cursor.**

- **Persona + context:** Alex, mid-level full-stack dev, has 3 .cursor/rules files they wrote over 6 months. Uses Cursor daily, just started trying Claude Code.
- **Entry state:** Terminal, in project root. Has cloned agentic-os or copied files in.
- **Path:** Runs `setup.sh --ai --runtime cursor,claude`. Script verifies `.agents/skills/agentic-os-setup/` exists, writes setup context, prints: "AI-installer skill ready. Open Cursor and say: run the agentic-os setup skill." Alex opens Cursor, invokes the skill. AI scans repo, reports: "Detected: Node.js monorepo, 3 existing cursor rules (002-dates.mdc, 003-eslint.mdc, 005-api.mdc), complexity tier: Multi. I'd generate: .cursor/rules/900-agentic-os.mdc, CLAUDE.md, and AGENTS.md. No conflicts with existing rules." Alex reviews the unified diff preview, says "looks good." AI writes files.
- **Climax:** Alex immediately asks Cursor a question about their API routes and gets a response that references agentic-os context — tangibly better than before.
- **Resolution:** Three new files exist. Original rules untouched. Alex knows they can `setup.sh --remove` if needed.
- **Edge case:** If AI detects glob overlap with existing rule 005-api.mdc, it aborts with conflict report and asks Alex to resolve.

**UJ-2. Sam, a senior architect, adds agentic-os to their multi-team documentation monorepo.**

- **Persona + context:** Sam manages a repo with designs, team work items, job postings, infrastructure-as-code, and 3 teams. Has BMAD installed, 10+ cursor rules, MCP integrations.
- **Entry state:** Terminal, project root. Wants agentic-os to handle cross-domain rules and task routing.
- **Path:** Runs `setup.sh --ai --runtime claude,cursor,cline`. AI scans, reports: "Detected: complex tier. 5 concern domains (Designs, Operations, Team-Workitems, Infrastructure, Meetings). Existing AI config: _bmad/ (deferring persona ownership), .cursor/rules/ (10 files, 0XX-9XX numbering). I'd generate: AGENTS.md, GOALS.md, .cursor/rules/850-agentic-os.mdc (next available in 8XX band), CLAUDE.md, .clinerules. Proposed relationships: job-interviews → job-descriptions (confirm?), Team-Workitems → Designs (confirm?)." Sam confirms relationships, reviews diff, approves.
- **Climax:** Cross-domain linkage enforcement is active — AI now refuses to create interview notes without linking to job description. Scope isolation prevents context bleed between teams.
- **Resolution:** Agentic-os config lives alongside BMAD without conflict. Generated files are gitignored. Sam can re-run later when adding new folders.

**UJ-3. Jordan, a student, tries agentic-os on their Flask project for the first time.**

- **Persona + context:** Jordan just installed Claude Code extension yesterday. No existing AI config. Small Flask API project.
- **Entry state:** Terminal, project root. Ran `setup.sh` (no flags) and completed the classic questionnaire.
- **Path:** Classic setup finishes. Final output says: "Want smarter, AI-powered setup? Run: setup.sh --ai". Jordan is curious, runs it with `--runtime claude`. AI scans: "Detected: simple tier. Flask app with src/, tests/, requirements.txt. I'd generate: CLAUDE.md that teaches Claude about your Flask routes, models, and test patterns." Jordan sees a short diff, approves.
- **Climax:** Jordan asks Claude about their project and gets an answer that references their actual route structure — first "wow, it knows my code" moment.
- **Resolution:** One file generated (CLAUDE.md). Minimal, immediately valuable. Jordan keeps using it.

**UJ-4. Riley sets up agentic-os using Antigravity on their Rust microservices project.**

- **Persona + context:** Riley, a backend engineer, uses Antigravity as their primary AI coding tool. Has an existing AGENTS.md from a previous manual setup attempt. Runs a Rust workspace with 3 crates (api, core, shared).
- **Entry state:** Terminal, workspace root. Antigravity already configured and running.
- **Path:** Runs `setup.sh --ai --runtime antigravity`. Script verifies skill exists, writes setup context, prints: "AI-installer skill ready. Open Antigravity and say: run the agentic-os setup skill." Riley invokes the skill. AI scans: "Detected: Multi tier. Rust workspace with 3 crates. Existing AGENTS.md found — I'll extend it with agentic-os sections rather than replace. I'd add: persona routing (api crate → API designer, core → systems engineer), scope isolation between crates, and quality gate (cargo test must pass before declaring done)." Riley reviews the diff showing additions to AGENTS.md, approves.
- **Climax:** Riley asks Antigravity about a cross-crate dependency and gets a response scoped to the correct crate context — the AI respects the scope isolation rules.
- **Resolution:** AGENTS.md extended (not replaced). Manifest tracks the managed sections. Riley's original AGENTS.md content is preserved above the managed block.
- **Edge case:** If the existing AGENTS.md has conflicting persona definitions, AI proposes reconciliation options rather than silently appending.

## 3. Glossary

- **AI-installer skill** — A SKILL.md file containing a reasoning framework, signal catalog, and rule templates that any supported AI runtime can execute to configure agentic-os for the current repo.
- **Signal catalog** — A structured list of filesystem markers (file names, folder patterns, config files) and what they indicate about a repo's purpose, complexity, and existing tooling.
- **Complexity tier** — Classification of a repo's configuration needs: Zero (empty), Simple (single-purpose), Multi (2-3 concerns), Complex (4+ concerns, teams, cross-domain relationships).
- **Runtime adapter** — The component of the AI-installer skill that translates a configuration intent into the native format of a specific AI tool (CLAUDE.md for Claude Code, .mdc for Cursor, .clinerules for Cline, AGENTS.md for Antigravity).
- **Managed block** — A section of a generated file delimited by markers (e.g., `<!-- MANAGED BY AGENTIC-OS [hash] -->`) that the re-run system owns. Checksum guards prevent overwriting user edits.
- **Dry-run** — A mode where the AI-installer previews all proposed changes as unified diffs without writing any files.
- **Re-run** — A mode where the AI-installer detects changes since the last run and proposes only the delta.
- **Relationship** — A semantic link between two folders/concerns (e.g., interviews reference job descriptions). Can be manifest-declared (trusted) or AI-proposed (requires confirmation).
- **Glob collision** — When a generated .mdc rule's glob pattern overlaps with an existing rule's glob, causing unpredictable behavior in Cursor.
- **Scope isolation** — A rule type that prevents AI context from one domain (e.g., Operations) bleeding into another (e.g., Designs).

## 4. Features

### 4.1 Bootstrap Entry Point

**Description:** The existing `setup.sh` gains an `--ai` flag that bootstraps the AI-assisted setup path. Without `--ai`, behavior is 100% unchanged. The flag drops the AI-installer skill into the canonical skills location and prints clear instructions for the user's next step. The classic setup's completion message also surfaces the `--ai` option for discoverability. Realizes UJ-1, UJ-2, UJ-3, UJ-4.

**Functional Requirements:**

#### FR-1: Flag-based mode selection

The user can run `setup.sh --ai` to enable AI-assisted setup. Running `setup.sh` without flags executes the existing classic questionnaire with zero behavioral change.

**Consequences (testable):**
- `setup.sh` without flags produces identical output to current behavior (regression test)
- `setup.sh --ai` bootstraps workspace infrastructure into target, writes setup context file, and prints invocation instructions (including `/agentic-os-setup` slash command for Claude Code)
- `setup.sh --ai` does NOT execute the classic questionnaire
- `setup.sh --help` prints usage information for all flags and exits
- The SKILL.md includes YAML frontmatter (`name:`, `description:`) enabling Claude Code slash-command discovery via the `.claude/skills/` bridge path

#### FR-2: Runtime targeting

The user can specify which AI runtimes to configure via `--runtime <comma-separated-list>`. Valid values for v1: `claude`, `cursor`, `cline`, `antigravity`. Omitting `--runtime` defaults to all detected runtimes.

**Consequences (testable):**
- `setup.sh --ai --runtime claude,cursor` generates configs only for Claude Code and Cursor
- Invalid runtime names produce a clear error message listing valid options
- When `--runtime` is omitted, the AI-installer skill detects which runtimes are present (by checking for `.claude/`, `.cursor/`, `.clinerules`, `AGENTS.md`)

#### FR-3: Clean uninstall

The user can run `setup.sh --remove` to cleanly remove all agentic-os generated files and restore the repo to its pre-setup state.

**Consequences (testable):**
- `setup.sh --remove` deletes only files created by agentic-os (tracked in a manifest file `.agents/.agentic-os-manifest.json`)
- Original user files are never modified or deleted
- Removal also deletes the setup context file (`.agents/.agentic-os-setup-context.json`) and the manifest itself
- Removal produces a summary of what was deleted
- After removal, no agentic-os setup artifacts remain

#### FR-4: Discoverability

The classic `setup.sh` completion message includes a one-line prompt about the `--ai` option.

**Consequences (testable):**
- After classic setup completes, output includes: "Want AI-powered setup? Run: setup.sh --ai"
- The prompt is a single line, not a wall of text

#### FR-25: Target directory

The user can specify a target directory via `--target <path>` to run setup against a repo other than CWD.

**Consequences (testable):**
- `setup.sh --ai --target ./my-project` operates on `./my-project` instead of CWD
- All file reads and writes resolve relative to the target directory
- If `--target` is omitted, CWD is used (unchanged default)
- If the target path does not exist, the script exits with a clear error
- Works with both `--ai` and `--remove` modes
- setup.sh copies the agentic-os-setup skill and workspace infrastructure into the target directory during bootstrap, so all files are local when the AI runs
- No external path references in the context bridge — the AI finds everything at `.agents/skills/agentic-os-setup/` locally

#### FR-26: Auto-approval mode

The user can pass `--auto` alongside `--ai` to run the full AI-assisted setup without interactive approval. The AI shows the diff preview then immediately writes without waiting for user confirmation.

**Consequences (testable):**
- `setup.sh --ai --auto --runtime claude` runs full flow: scan → classify → propose → show preview → write (no pause)
- `--auto` REQUIRES explicit `--runtime` (cannot auto-detect in unattended mode) — exits with error if `--runtime` is missing
- The context bridge file contains `"auto": true` when this flag is passed
- Auto mode still shows the diff preview output (for logging/CI purposes)
- Auto mode still respects `--dry-run` (if both passed: show diffs, write nothing)
- Auto mode does NOT skip conflict detection — if collisions are found, the run fails with a non-zero exit code rather than silently overwriting

**Out of Scope:**
- GUI or web-based setup interface
- Automatic runtime detection in the shell script itself (that's the AI's job)

### 4.2 AI-Installer Skill

**Description:** The core of the feature — a SKILL.md file that any supported AI runtime can execute. Contains a reasoning framework for analyzing repos, a signal catalog for anchoring detection, rule templates for generating config, output examples for calibration, and runtime adapters for multi-tool output. Realizes UJ-1, UJ-2, UJ-3, UJ-4.

**Functional Requirements:**

#### FR-31: Workspace bootstrapping

When invoked against a target repo, the AI-installer first bootstraps the full agentic-os workspace structure before generating configuration. This replaces the classic setup's questionnaire with repo-analysis-based inference.

**Consequences (testable):**
- `Tasks/` and `Knowledge/` directories are created if not present
- `AGENTS.md` is copied from agentic-os source if not present in target
- `GOALS.md` is auto-generated with AI-inferred content (role, vision, priorities derived from repo signals) — inferred fields marked with `[AI-inferred — refine as needed]`
- `BACKLOG.md` is created with standard template if not present
- `Workflows/` directory is copied from agentic-os source if not present
- `.agents/skills/` directory (all canonical skill packs) is copied if not present
- `.claude/skills/` bridge ensured: if no `.claude/skills` exists, creates a symlink to `../.agents/skills`; if `.claude/skills` already exists as a directory, copies `agentic-os-setup` into it directly. `skills → .agents/skills` symlink created at root.
- `.gitignore` copied from template if not present (never overwrites existing)
- `CLAUDE.md` created with `@AGENTS.md` reference if not present (never overwrites existing)
- All bootstrapped files are tracked in the manifest for clean removal
- Existing files are NEVER overwritten during bootstrap — skip and note

#### FR-5: Repo structure scanning

When invoked, the AI-installer skill reads the repo's filesystem structure (directories, key files, existing config files) and builds a structural profile.

**Consequences (testable):**
- Skill identifies top-level directories and their likely purpose
- Skill detects existing AI configurations (.cursor/rules/, .claude/, .clinerules, _bmad/, AGENTS.md)
- Skill reads manifest/README files if present for declared relationships
- Skill does NOT read file contents beyond config files and manifests (privacy-respecting scan)

#### FR-6: Complexity classification

The AI-installer classifies the repo into one of four complexity tiers based on detected signals: Zero (empty/new), Simple (single-purpose), Multi (2-3 concerns), Complex (4+ concerns).

**Consequences (testable):**
- A repo with only src/ and tests/ is classified as Simple
- A repo with src/, docs/, and infrastructure/ is classified as Multi
- A repo with 4+ distinct concern folders, existing AI config, and team indicators is classified as Complex
- Classification is proposed to the user with rationale, not silently applied

#### FR-7: Configuration proposal

Based on complexity tier and detected structure, the AI-installer proposes a set of files to generate, with content tailored to the specific repo.

**Consequences (testable):**
- Simple tier: proposes at most 1 config file per targeted runtime
- Multi tier: proposes runtime configs + lightweight AGENTS.md
- Complex tier: proposes full suite (AGENTS.md, GOALS.md, runtime configs with persona routing, scope isolation, relationship enforcement)
- Every proposal includes the full content that would be written (not just file names)

#### FR-8: Relationship discovery

The AI-installer detects cross-domain relationships via two paths: (1) manifest-declared relationships are trusted without confirmation, (2) AI-inferred relationships are proposed with rationale and require explicit user confirmation.

**Consequences (testable):**
- If a manifest file declares "interviews → job-descriptions", this relationship is included without asking
- If the AI infers a relationship from folder naming patterns, it asks: "I think X relates to Y because Z — confirm?"
- User can deny an inferred relationship and it is excluded from generated config
- Denied relationships are not re-proposed on re-run

#### FR-9: Signal catalog

The skill includes a structured catalog of known filesystem signals and their meanings, used to anchor the AI's reasoning and prevent hallucination. The skill also includes `agents/openai.yaml` to comply with the repo's Agent Skills open standard (progressive disclosure metadata for routing).



**Consequences (testable):**
- Catalog includes entries for common patterns: `.cursor/rules/` (existing Cursor config), `terraform/` (infrastructure), `_bmad/` (BMAD framework), `package.json` (Node.js), `pyproject.toml` (Python), etc.
- Each entry specifies: pattern, what it indicates, and how it affects complexity scoring
- The AI uses the catalog as reference but can reason about patterns not in the catalog

### 4.3 Dry-Run and Preview

**Description:** Before writing any files, the AI-installer presents all proposed changes as unified diffs the user can review. A `--dry-run` flag produces the preview and exits without writing. Realizes UJ-1, UJ-2, UJ-3, UJ-4.

**Functional Requirements:**

#### FR-10: Unified diff preview

All proposed file creations and modifications are presented as unified diffs before any write operation.

**Consequences (testable):**
- New files show as full-content diffs (--- /dev/null, +++ b/path)
- The user sees exact content that would be written, not a summary
- Diffs are presented in a format compatible with standard diff tools

#### FR-11: Dry-run mode

When the AI-installer is invoked with a dry-run intent (or `setup.sh --ai --dry-run`), it performs full analysis and generates diffs but writes nothing to disk. The `--dry-run` flag is communicated to the AI skill via `.agents/.agentic-os-setup-context.json` (written by setup.sh).

**Consequences (testable):**
- After dry-run, no new files exist on disk
- Dry-run output is identical to what would be shown before a real write
- User can redirect dry-run output to a file for team review
- The setup context file contains `"dry_run": true` when this flag is passed

#### FR-12: Approval gate

After presenting diffs, the AI-installer waits for explicit user approval before writing any files.

**Consequences (testable):**
- AI does not write files until user confirms
- User can reject individual files while approving others
- User can request modifications to proposed content before approval

### 4.4 Conflict Detection and Safety

**Description:** The AI-installer detects potential conflicts with existing AI configurations and aborts or warns rather than silently overriding behavior. Realizes UJ-1, UJ-2, UJ-4.

**Functional Requirements:**

#### FR-13: Glob collision detection

Before generating .cursor/rules/ files, the AI-installer scans existing .mdc files for glob patterns that would overlap with proposed rules.

**Consequences (testable):**
- If a proposed rule's glob overlaps with an existing rule's glob, the AI reports the collision
- Collision report includes: the existing file, its glob, the proposed glob, and why they conflict
- On collision: AI proposes alternatives (narrower glob, different approach) or aborts that specific rule

#### FR-14: Existing rule numbering respect

When generating .cursor/rules/ files in a repo with existing numbered rules (0XX-9XX convention), the AI-installer appends to the next available number in the appropriate band.

**Consequences (testable):**
- If existing rules use 800-805, new rule is numbered 806 or higher (not 800)
- The band is determined by rule type (workflow rules → 8XX)
- Never renumbers or moves existing rule files

#### FR-15: Non-destructive file policy

The AI-installer NEVER modifies or deletes files it did not create, with one controlled exception: `.gitignore` receives an append-only managed block (FR-22). AGENTS.md may be extended via managed block append (FR-20). No other user files are modified.

**Consequences (testable):**
- Existing .cursor/rules/ files are never modified
- Existing CLAUDE.md is never modified; AI creates `CLAUDE-agentic-os.md` as a companion file instead
- Existing .clinerules is never modified; AI creates `.clinerules-agentic-os` as a companion file instead
- If user has a hand-written AGENTS.md, the AI extends it with a managed block (never replaces user content above the block)
- `.gitignore` is appended with a delimited block (never replaces existing entries)
- No user file content is ever deleted or rewritten by the setup process

#### FR-16: Framework coexistence detection

When the AI-installer detects an existing agent framework (_bmad/, or similar), it defers persona ownership and generates only cross-reference and structural rules.

**Consequences (testable):**
- If `_bmad/` directory exists, AI does NOT generate persona routing rules
- Generated rules are limited to: scope isolation, cross-reference enforcement, naming patterns
- The AI explains what it's deferring and why

### 4.5 Runtime Adapters

**Description:** The AI-installer translates configuration intent into the native format of each targeted AI runtime, producing semantically equivalent but syntactically different output per tool. Realizes UJ-1, UJ-2, UJ-3, UJ-4.

**Functional Requirements:**

#### FR-17: Claude Code adapter

Generates CLAUDE.md with persona routing, execution rules, and quality gates formatted for Claude Code's instruction-following model.

**Consequences (testable):**
- Output follows Claude Code's CLAUDE.md conventions (sections, headers, markdown formatting)
- References AGENTS.md for persona definitions
- Includes folder-specific behavior routing

#### FR-18: Cursor adapter

Generates .cursor/rules/NNN-agentic-os.mdc with proper YAML frontmatter (description, globs, alwaysApply) formatted for Cursor's rule system.

**Consequences (testable):**
- Output includes valid YAML frontmatter with description and globs fields
- Glob patterns are specific to detected concern domains (not catch-all `*`)
- Rule file is numbered according to existing convention (or starts at 900 if no convention detected)

#### FR-19: Cline adapter

Generates .clinerules or equivalent Cline configuration expressing the same behavioral intent.

**Consequences (testable):**
- Output follows Cline's expected configuration format
- Behavioral intent is semantically equivalent to Claude and Cursor outputs
- References shared AGENTS.md where applicable

#### FR-20: Antigravity adapter

Generates or augments AGENTS.md to serve as Antigravity's primary instruction file. Realizes UJ-4.

**Consequences (testable):**
- AGENTS.md includes all persona routing and behavioral rules
- Format is compatible with Antigravity's AGENTS.md parsing
- If AGENTS.md already exists (from classic setup or user-written), extends with a managed block rather than replacing
- Existing user-written content above the managed block is never modified
- Managed block markers clearly delimit agentic-os sections from user content

### 4.6 Installation Manifest

**Description:** The AI-installer maintains a manifest of all files it created, enabling clean uninstall and safe re-run detection. Realizes UJ-1.

**Functional Requirements:**

#### FR-21: Manifest tracking

Every file created by the AI-installer is recorded in `.agents/.agentic-os-manifest.json` with path, creation date, and content hash.

**Consequences (testable):**
- After setup, manifest contains entries for every generated file
- Each entry has: `path`, `created_at`, `content_hash`
- Manifest file itself is gitignored by default

#### FR-22: Gitignore management

Generated files are added to .gitignore by default. A `--track` flag opts into version-controlling generated config.

**Consequences (testable):**
- Without `--track`: all generated file paths are appended to .gitignore under an `# agentic-os generated` comment block
- With `--track`: generated files are NOT gitignored
- The gitignore block is clearly delimited for clean removal

### 4.7 Documentation Updates

**Description:** The feature requires updates to README.md to document the new `--ai` setup path, and a new CONTRIBUTING.md file to guide contributors working on the AI-installer skill, signal catalog, templates, and adapters. Realizes UJ-3 (discoverability), UJ-1 (understanding what happened).

**Functional Requirements:**

#### FR-23: README update

README.md must be updated to document the AI-assisted setup path alongside the existing Quick Start instructions.

**Consequences (testable):**
- Quick Start section includes a step for `--ai` setup as an alternative to classic mode
- Architecture mermaid diagram updated to show AI-installer skill as a component
- A new mermaid flow diagram shows the AI-assisted setup flow (setup.sh --ai → skill dropped → AI invoked → scan → classify → propose → approve → generate) with mode indicators (first-run, dry-run)
- Agent Compatibility section lists Cursor, Cline, and Antigravity alongside existing runtimes
- File System Layout shows the `.agents/skills/agentic-os-setup/` directory
- A "Setup Modes" section explains classic vs AI-assisted with clear when-to-use guidance

#### FR-24: CONTRIBUTING.md

A CONTRIBUTING.md file must exist at repo root describing how to contribute to the project, with specific guidance for the AI-installer skill components.

**Consequences (testable):**
- File exists at repo root as `CONTRIBUTING.md`
- Covers: how to add signals to the catalog, how to add rule templates, how to add runtime adapters
- Includes: development workflow (fork, branch, test, PR)
- References: license (CC BY-NC-SA 4.0), code of conduct expectations
- Documents: how to test changes across runtimes (manual testing protocol)
- Lists: what constitutes a good PR for this project (signal + template + adapter together)

### 4.8 Test Infrastructure

**Description:** The project includes test repos (real directory structures mimicking UJ-1 through UJ-4), a shell-based test runner for setup.sh flag validation, and a Python-based test runner for generated content validation. Enables automated regression testing. Realizes SM-2, SM-3, SM-4, SM-5.

**Functional Requirements:**

#### FR-27: Test repo fixtures

The project includes real directory structure fixtures in `examples/` that mimic each user journey's repo structure.

**Consequences (testable):**
- `examples/uj-1-node-monorepo/` contains a realistic Node.js monorepo structure (package.json with workspaces, .cursor/rules/ with 3 existing files, src/, tests/)
- `examples/uj-2-architect-monorepo/` contains a complex multi-concern structure (Designs/, Operations/, Team-Workitems/, Infrastructure/, _bmad/, .cursor/rules/ with 10+ files)
- `examples/uj-3-flask-simple/` contains a simple Flask project (src/, tests/, requirements.txt, no AI config)
- `examples/uj-4-rust-antigravity/` contains a Rust workspace (Cargo.toml with workspace, 3 crate dirs, existing AGENTS.md)
- Each fixture is a self-contained directory that setup.sh --ai --target can be invoked against

#### FR-28: Shell test runner

A POSIX-compatible shell test script validates setup.sh flag parsing, mode routing, and remove logic.

**Consequences (testable):**
- `tests/test_setup.sh` exists and is executable
- Tests validate: --help output, --ai flag routing, --runtime validation (valid and invalid), --remove with/without manifest, --target with valid/invalid paths, --auto requiring --runtime, flag combinations (--ai --dry-run --runtime, etc.)
- Tests run without external dependencies beyond sh, jq, and standard POSIX tools
- Tests produce pass/fail output with clear failure messages
- Test results are written to `tests/results/shell/report.txt` (plaintext summary)

#### FR-29: Python content validator

A pytest-based test suite validates that generated content (from running the AI skill against test fixtures) meets structural and semantic requirements.

**Consequences (testable):**
- `tests/test_content.py` exists with pytest test cases
- `pytest.ini` configures test paths and JUnit XML output (`tests/results/python/report.xml`)
- `tests/conftest.py` generates a plaintext report (`tests/results/python/report.txt`) via session hook
- Tests validate: manifest JSON schema correctness, .mdc YAML frontmatter validity, glob specificity (no bare `*`), managed block marker syntax, gitignore block structure, numbering respect (no renumbering existing files)
- Tests can run against pre-generated output in `tests/results/python/` or generate fresh output
- Tests cover 5 scenarios: simple project, complex project, existing AI config (collision detection), framework coexistence (BMAD deferral), clean uninstall verification
- Python test dependencies: `pytest`, `pyyaml`

#### FR-30: Test results gitignored

Test output artifacts are gitignored to prevent generated content from polluting the repository.

**Consequences (testable):**
- `tests/results/` directory exists in .gitignore
- Shell tests write to `tests/results/shell/report.txt`
- Python tests write to `tests/results/python/report.xml` (JUnit XML) and `tests/results/python/report.txt` (plaintext)
- Running tests does not modify any tracked files

## 5. Non-Goals (Explicit)

- **Re-run with delta merging** — Phase 2. V1 supports first-run and dry-run only; re-run requires managed blocks and checksum infrastructure.
- **Team-scoped context isolation** — Phase 2. Requires folder-to-team mapping that needs UX design.
- **BMAD deep integration** — V1 defers to BMAD when detected. Full integration (reading BMAD personas, extending them) is Phase 2.
- **Relationship graph visualization** — Phase 3. Useful but not load-bearing for setup.
- **MCP/Azure DevOps integration detection** — Phase 3. Beyond filesystem signals.
- **Dynamic/ephemeral config generation** — Phase 4 (first-principles vision). V1 generates static files.
- **CI/CD headless mode** — Partially addressed by `--auto` flag for single-runtime unattended runs. Full CI/CD integration (multi-stage pipelines, artifact caching) remains future scope.
- **Runtimes beyond v1 set** — GitHub Copilot, Kiro, Codex, Pi are future phases.
- **Modifying existing user files** — Never, except controlled append-only managed blocks on `.gitignore` (FR-22) and AGENTS.md (FR-20). No other user files are modified.

## 6. MVP Scope

### 6.1 In Scope

- `setup.sh --ai` flag with `--runtime`, `--dry-run`, `--remove`, `--track`, `--target`, `--auto` options
- AI-installer skill (SKILL.md) with reasoning framework, signal catalog, rule templates
- 4-tier complexity detection with user-facing proposal
- Config generation for Claude Code, Cursor, Cline, Antigravity
- Unified diff preview before any write
- Explicit approval gate (bypassed in auto mode)
- Auto-approval mode with explicit runtime requirement
- Target directory support for running against any repo
- Glob collision detection (scan + abort on conflict; hard fail in auto mode)
- Existing rule numbering respect
- Framework coexistence detection (defer to BMAD if present)
- Non-destructive file policy (never modify user files)
- Installation manifest for clean uninstall
- Gitignore management (default: ignore generated files)
- Discoverability message in classic setup output
- Test repo fixtures (4 UJ-based directory structures)
- Automated test suite (shell + Python, 5 scenarios)

### 6.2 Out of Scope for MVP

- Re-run / update mode — deferred to Phase 2. [NOTE FOR PM] Users will need to `--remove` and re-run for now.
- Managed blocks with checksum guards — Phase 2 prerequisite for safe re-run.
- Team isolation — Phase 2. Multi-team repos get basic config without team boundaries.
- Relationship graph persistence — Phase 3. Relationships are computed per-run, not saved.

## 7. Success Metrics

Note: This is an open-source CLI tool with no telemetry. Metrics are observable via GitHub issues, PR feedback, and manual testing — not automated analytics.

**Primary (observable via GitHub engagement + manual testing)**
- **SM-1**: Adoption signal — `--ai` is mentioned in issues/discussions as the preferred setup path by users who try it. Feature is referenced in community forks. Validates FR-1, FR-4.
- **SM-2**: Setup completion — manual testing across all 4 complexity tiers completes without user needing to abort due to poor proposals. Users who file issues report successful runs, not broken states. Validates FR-10, FR-12, FR-7.
- **SM-3**: Clean first-run — testing on repos with no existing AI config produces zero glob collisions or conflict aborts. Validates FR-13, FR-14.

**Secondary (observable via testing protocol)**
- **SM-4**: Uninstall confidence — `--remove` on any completed setup leaves zero leftover artifacts (verifiable in manual test protocol). Validates FR-3, FR-21.
- **SM-5**: Multi-runtime consistency — generated configs for the same repo express semantically equivalent intent across Claude, Cursor, Cline, and Antigravity (verifiable by comparing outputs). Validates FR-17, FR-18, FR-19, FR-20.

**Counter-metrics (design constraints, not measured)**
- **SM-C1**: Generated file count — should NOT increase over time. More files ≠ better. Tier-gating exists to prevent bloat. Counterbalances SM-2.
- **SM-C2**: False confidence — users should NOT trust generated config blindly. Dry-run exists to encourage review. Counterbalances SM-1.

## 8. Open Questions

1. ~~Should the AI-installer skill be a single SKILL.md or split into sub-files?~~ **RESOLVED** — Architecture Decision 3: Single SKILL.md as orchestrator with modular supporting files (catalog.md, templates/, adapters/, examples/).
2. What's the exact instruction the user types in each runtime? ("run setup" vs a slash command vs natural language) — To be defined per-adapter during implementation.
3. ~~How does the signal catalog stay up-to-date?~~ **RESOLVED** — CONTRIBUTING.md defines the community contribution path for adding signals.
4. ~~Should denied relationships be persisted?~~ **RESOLVED** — Architecture Decision 6: Manifest stores `denied_relationships` array to prevent re-proposal across sessions.
5. What's the minimum set of signals for each complexity tier? (Need to avoid over-classifying simple repos as Multi) — To be calibrated during catalog authoring and testing.

## 9. Delivery

The pull request template for this feature is at `pull-request.md` in this directory. It uses the PRD vision and motivation sections as the basis for PR messaging and documents the BMad Method planning process that produced these artifacts.

## 10. Assumptions Index

- [ASSUMPTION from §4.1] Classic `setup.sh` output can be modified to add the discoverability line without breaking existing workflows
- [ASSUMPTION from §4.2] AI runtimes can execute a SKILL.md by reading it as context/instructions without specialized plugin infrastructure
- [ASSUMPTION from §4.4] Cursor does not have built-in conflict resolution for overlapping .mdc globs — collisions are truly silent
- [ASSUMPTION from §4.5] Cline's .clinerules format is stable and documented enough to generate programmatically. **Validation plan:** Before implementing Story 4.3, verify current .clinerules format against Cline's official documentation/source. If format is unstable or undocumented, fallback: generate a generic markdown instruction file that Cline can read as context, and document the limitation in the adapter.
- [ASSUMPTION from §4.6] A JSON manifest is preferable to alternative tracking methods (e.g., marker comments in files)
