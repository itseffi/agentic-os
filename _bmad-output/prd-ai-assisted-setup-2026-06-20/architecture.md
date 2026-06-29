---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: ['prd.md', 'addendum.md']
workflowType: 'architecture'
project_name: 'AI-Assisted Complex Repo Auto-Setup'
date: '2026-06-20'
---

# Architecture Decision Document

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
This system has 31 FRs across 8 feature groups. The architecture must support:
- Shell script entry point with flag parsing, target directory, auto-approval (FR-1 through FR-4, FR-25, FR-26)
- AI skill execution across 4 runtimes (FR-5 through FR-9)
- Preview and approval workflow (FR-10 through FR-12)
- Conflict detection and safety guarantees (FR-13 through FR-16)
- Multi-runtime output generation (FR-17 through FR-20)
- Manifest-based tracking for clean uninstall (FR-21, FR-22)
- Documentation updates (FR-23, FR-24)
- Test infrastructure: fixtures, shell runner, Python validator (FR-27 through FR-30)

**Non-Functional Requirements:**
- Zero regression to existing setup.sh behavior
- Cross-platform (macOS, Windows via WSL/Git Bash, Linux)
- Minimal external dependencies: POSIX-compatible shell (sh), git, jq (for manifest JSON parsing). setup.sh verifies jq is available and prints install guidance if missing.
- AI runtimes are the execution engine — the system itself is passive files

**Scale & Complexity:**
- Primary domain: File-based AI configuration system (not a software application)
- Complexity level: Medium — multiple interacting file artifacts but no runtime processes
- Components: Shell script (bootstrap), AI skill (logic), signal catalog (data), rule templates (generators), runtime adapters (translators), manifest (state)

### Technical Constraints & Dependencies

- Must work within agentic-os's existing file layout (`.agents/skills/` canonical path)
- AI runtimes have no shared execution model — each reads markdown differently
- Shell script must be POSIX-compatible (not bash-only) for maximum portability
- External dependency: `jq` required for `--remove` manifest parsing. setup.sh checks for jq on invocation of `--remove` and exits with guidance if missing.
- No Node.js, Python, or other runtime dependencies in the bootstrap path
- The AI skill is the only component with "intelligence" — everything else is data or scaffolding

**Supported runtimes (v1 — canonical list):**

| Runtime ID | Tool | Adapter File | Output Target |
|-----------|------|-------------|--------------|
| `claude` | Claude Code | adapters/claude.md | CLAUDE.md (or CLAUDE-agentic-os.md) |
| `cursor` | Cursor | adapters/cursor.md | .cursor/rules/NNN-agentic-os.mdc |
| `cline` | Cline | adapters/cline.md | .clinerules (or .clinerules-agentic-os) |
| `antigravity` | Antigravity | adapters/antigravity.md | AGENTS.md (managed block) |

These are the only valid values for `--runtime`. Adding a new runtime requires: a new adapter file, a new entry in this table, and an update to `VALID_RUNTIMES` in setup.sh.

### Cross-Cutting Concerns

- **Safety:** Never modify user files except controlled append-only operations on `.gitignore` and AGENTS.md (managed blocks only); always preview before write
- **Portability:** Works across macOS/Linux/WSL without dependencies
- **Idempotency:** Running setup twice should not create duplicates
- **Privacy:** Generated configs may expose repo structure; gitignore by default
- **Coexistence:** Must detect and defer to existing frameworks (BMAD, etc.)

---

## Starter Template Evaluation

**Not applicable.** This is not a software application — it's a file-based system that extends an existing open-source project. No starter template, no build tools, no package managers.

**Technology Stack:**
- **Shell:** POSIX sh for `setup.sh` (portability)
- **Markdown:** SKILL.md, signal catalog, rule templates (AI-readable)
- **JSON:** Manifest file for state tracking
- **YAML:** Cursor .mdc frontmatter generation

---

## Core Architectural Decisions

### Decision 1: System Architecture Model

**Decision:** Passive file system with AI-runtime execution

The system produces files that AI runtimes interpret. There is no server, no daemon, no build step. The "intelligence" lives entirely within the AI-installer SKILL.md — everything else is data the skill consumes.

```
┌─────────────────────────────────────────────────┐
│ User's Repository                                │
│                                                  │
│  setup.sh ──┐                                   │
│             │ drops                              │
│             ▼                                    │
│  .agents/skills/agentic-os-setup/               │
│  ├── SKILL.md          (reasoning framework)    │
│  ├── catalog.md        (signal catalog)         │
│  ├── templates/        (rule templates)         │
│  │   ├── persona-routing.md                     │
│  │   ├── scope-isolation.md                     │
│  │   ├── cross-reference.md                     │
│  │   ├── naming-enforcement.md                  │
│  │   └── quality-gates.md                       │
│  ├── adapters/         (runtime adapters)       │
│  │   ├── claude.md                              │
│  │   ├── cursor.md                              │
│  │   ├── cline.md                               │
│  │   └── antigravity.md                         │
│  └── examples/         (calibration examples)   │
│      ├── simple-output.md                       │
│      └── complex-output.md                      │
│                                                  │
│  ← AI runtime reads SKILL.md and executes →     │
│                                                  │
│  Generated outputs:                              │
│  ├── CLAUDE.md                                  │
│  ├── AGENTS.md         (if complex tier)        │
│  ├── GOALS.md          (if complex tier)        │
│  ├── .cursor/rules/NNN-agentic-os.mdc           │
│  ├── .clinerules                                │
│  └── .agents/.agentic-os-manifest.json          │
└─────────────────────────────────────────────────┘
```

**Rationale:** AI runtimes are the execution engine. The system provides instructions (SKILL.md) and data (catalog, templates). This is the same pattern agentic-os already uses for all its skills — consistency with existing architecture.

### Decision 2: Shell Script Responsibilities (Minimal)

**Decision:** `setup.sh` handles ONLY bootstrapping and teardown — never AI logic.

**What setup.sh does:**
- Parse flags (`--ai`, `--runtime`, `--dry-run`, `--remove`, `--track`, `--target`, `--auto`, `--help`)
- Validate runtime flag values and dependency checks (jq for --remove)
- Resolve target directory (`--target <path>` or CWD) and `cd` into it for all operations
- **Bootstrap workspace infrastructure into target** (never overwrites existing files):
  - Create `Tasks/`, `Knowledge/` directories
  - Create `BACKLOG.md` (standard template)
  - Copy `Workflows/` from agentic-os source
  - Copy `.agents/skills/agentic-os-setup/` into target (or all skills if none exist)
  - Ensure `.claude/skills/` bridge: symlink if absent, or copy `agentic-os-setup` into existing directory. Create `skills` symlink at root.
  - Copy `.gitignore` from template (if none exists)
  - Append skills reference to `CLAUDE.md` (if not already present)
- Write `.agents/.agentic-os-setup-context.json` with resolved flags (runtimes, dry_run, track, auto)
- Validate `--auto` requires explicit `--runtime` (cannot auto-detect in unattended mode)
- Print invocation instructions (`/agentic-os-setup` slash command for Claude Code, or "Run the agentic-os-setup skill" for other runtimes)
- Handle `--remove` (read manifest, delete tracked files)
- Add discoverability message to classic setup output

**Source location:** The AI-installer skill files ship in-tree at `.agents/skills/agentic-os-setup/` as part of the agentic-os repo itself (same pattern as the existing 47 canonical skills). When running with `--target`, setup.sh copies the skill into the target repo so it's available locally.

**Discoverability:** The SKILL.md includes YAML frontmatter (`name: agentic-os-setup`, `description: ...`) which enables Claude Code to discover it as a `/agentic-os-setup` slash command via `.claude/skills/`. Works whether `.claude/skills/` is a symlink (fresh repos) or a real directory (repos with existing skills already installed). This matches the pattern used by all other skills in the repo (e.g., `/bmad-prd`, `/bmad-brainstorming`).

**What setup.sh does NOT do:**
- Scan repo structure (that's the AI's job)
- Generate config files (that's the AI's job)
- Detect complexity (that's the AI's job)
- Resolve conflicts (that's the AI's job)

**Rationale:** Keeping the script minimal means: (1) no portability bugs in complex logic, (2) the AI can be updated independently of the script, (3) the smart behavior lives in one place (SKILL.md), not split between shell and markdown.

### Decision 3: AI-Installer Skill Internal Architecture

**Decision:** Single SKILL.md as orchestrator with modular supporting files.

The SKILL.md is the entry point that the AI runtime reads. It references sub-files for specific concerns:

```
SKILL.md (orchestrator)
  ├── reads: catalog.md (signal definitions)
  ├── reads: templates/*.md (rule templates to fill)
  ├── reads: adapters/*.md (how to format per-runtime)
  └── reads: examples/*.md (calibration for output quality)
```

**SKILL.md sections:**
1. Mode detection (first-run vs dry-run vs re-run detection by checking manifest)
2. Scanning protocol (what to read, what to skip, privacy boundaries)
3. Classification logic (how to score complexity tiers)
4. Proposal generation (how to assemble output from templates + adapters)
5. Approval workflow (present diffs, wait for confirmation)
6. Write protocol (create files, update manifest, manage gitignore)

**Rationale:** Modularity — the catalog can be updated without touching the orchestrator. Templates can be added for new rule types. Adapters can be added for new runtimes. But the single SKILL.md entry point means AI runtimes only need to read ONE file to start.

### Decision 4: Signal Catalog Format

**Decision:** Structured markdown with consistent entry format.

```markdown
## Signal: .cursor/rules/

**Pattern:** Directory `.cursor/rules/` exists with `.mdc` files
**Indicates:** Existing Cursor AI configuration
**Complexity impact:** +1 tier signal
**Setup implications:**
- Scan existing rules for glob patterns (FR-13)
- Detect numbering convention (FR-14)
- Generate agentic-os rule in next available number slot
**Coexistence:** Additive only — never modify existing rules
```

Each signal entry has: Pattern, Indicates, Complexity impact, Setup implications, Coexistence behavior.

**Rationale:** Structured enough for the AI to reason systematically, but markdown so it's human-readable and editable by contributors without tooling.

### Decision 5: Rule Template Format

**Decision:** Templates use placeholder syntax that the AI fills with detected values.

```markdown
# Template: Persona Routing

## Intent
Route AI persona/behavior based on which folder the user is editing in.

## Inputs Required
- {domains}: List of detected concern domains with their folder paths
- {personas}: Mapping of domain → persona name and behavior description

## Output Pattern (Cursor .mdc)
---
description: Persona routing for agentic-os domains — {domain_name}
globs: {domain_path}/**/*
alwaysApply: true
---
# {persona_name} Mode
{persona_behavioral_rules}

## Output Pattern (CLAUDE.md section)
## Persona Routing
{for each domain}
- **{persona_name} Mode:** Triggered when editing `/{domain_path}/`. {persona_behavioral_rules}
{end for}

## When to Use
- Complexity tier: Multi or Complex
- Detected: 2+ distinct concern domains with different intent
- NOT when: single-purpose repo or _bmad/ detected (defer persona to BMAD)
```

**Rationale:** Templates make the system predictable (contributors know what output looks like) while the AI fills in the specifics. The "When to Use" section prevents over-application.

### Decision 6: Manifest Format and Location

**Decision:** JSON manifest at `.agents/.agentic-os-manifest.json`

```json
{
  "version": "1.0.0",
  "created_at": "2026-06-20T15:30:00Z",
  "complexity_tier": "multi",
  "runtimes_targeted": ["claude", "cursor"],
  "files": [
    {
      "path": "CLAUDE.md",
      "created_at": "2026-06-20T15:30:00Z",
      "content_hash": "sha256:abc123..."
    },
    {
      "path": ".cursor/rules/900-agentic-os.mdc",
      "created_at": "2026-06-20T15:30:00Z",
      "content_hash": "sha256:def456..."
    }
  ],
  "denied_relationships": [],
  "detected_frameworks": ["bmad"]
}
```

**Location:** `.agents/` because that's already agentic-os's internal directory (gitignored by default in the template).

**Version Migration Strategy:** The `version` field uses semver. Phase 2+ consumers MUST check version before processing:
- If manifest version < current expected version: run migration (add new fields with defaults, never delete old fields)
- If manifest version > current tool version: warn and proceed read-only (don't corrupt newer manifests)
- Phase 1 manifests will always be forward-readable because new phases ADD fields but never remove or rename existing ones (additive-only schema evolution)

**Rationale:** JSON is parseable by both shell (jq) and AI runtimes. The content hash enables future re-run delta detection (Phase 2). Denied relationships prevent re-proposal. Additive-only schema evolution ensures Phase 1 installs survive Phase 2 upgrades without breakage.

### Decision 7: Runtime Adapter Architecture

**Decision:** Each adapter is a self-contained reference document describing how to format output for that runtime.

The adapter does NOT contain code. It contains:
1. File path convention (where output goes)
2. Format specification (what valid output looks like)
3. Constraints (what this runtime can/cannot express)
4. Pre-existing file behavior (what to do if the target file already exists)
5. Examples (concrete output samples)

The AI reads the adapter and uses it as a formatting guide when generating output from templates.

**Pre-existing file behavior per runtime:**

| Runtime | Target file | If file exists already |
|---------|------------|----------------------|
| Claude Code | CLAUDE.md | Create `CLAUDE-agentic-os.md` as additive companion file. Reference it from proposal. Never modify existing CLAUDE.md. |
| Cursor | .cursor/rules/NNN-agentic-os.mdc | Always a new file (numbered). No conflict — glob collision detection handles overlap. |
| Cline | .clinerules | Create `.clinerules-agentic-os` as additive companion file. Never modify existing .clinerules. |
| Antigravity | AGENTS.md | Extend with managed block (append below user content). |

**Antigravity-specific behavior:** Antigravity uses AGENTS.md as its primary instruction file — the same file agentic-os already generates in classic mode and that users may have hand-written. The Antigravity adapter therefore specifies **extend semantics**: user content stays intact at the top, agentic-os appends a managed block below. This is the only runtime where the AI modifies an existing user file (append-only, never changes existing content).

```
AGENTS.md (Antigravity extend pattern):
┌─────────────────────────────────────────────────────────────────┐
│ [User's original content]                                        │ ← never touched
│ ...                                                              │
├─────────────────────────────────────────────────────────────────┤
│ <!-- MANAGED BY AGENTIC-OS | hash:sha256:<hash> | DO NOT EDIT -->│ ← managed block starts
│ ## Agentic-OS Generated Rules                                    │
│ ### Persona Routing                                              │
│ ### Scope Isolation                                              │
│ ### Quality Gates                                                │
│ <!-- END MANAGED BY AGENTIC-OS -->                               │ ← managed block ends
└─────────────────────────────────────────────────────────────────┘
```

**Canonical managed block marker format** (used everywhere — .gitignore comment block uses equivalent `# === AGENTIC-OS GENERATED ===` for gitignore syntax):
- Start: `<!-- MANAGED BY AGENTIC-OS | hash:sha256:<content-hash> | DO NOT EDIT -->`
- End: `<!-- END MANAGED BY AGENTIC-OS -->`
- Hash covers the content between markers (enables Phase 2 change detection)

**Rationale:** Adapters as reference docs means: (1) new runtimes can be supported by adding one file, (2) no code changes needed, (3) the AI handles the translation logic — we just teach it the target format. The Antigravity extend pattern prevents the "existing AGENTS.md gets replaced" failure mode identified in UJ-4.

### Decision 8: Conflict Detection Strategy

**Decision:** Pre-write scan with abort semantics.

Before writing ANY file, the AI must:
1. Check if the target path already exists (abort if user file, unless extending)
2. For .cursor/rules: scan ALL existing .mdc files for glob patterns that would overlap (UJ-1, UJ-2)
3. For CLAUDE.md: check if one exists already; if so, propose additions only (UJ-3)
4. For AGENTS.md: check if one exists already; if so, propose extension via managed block — if existing content has conflicting persona definitions, propose reconciliation options (UJ-4)

On conflict: report the collision clearly, propose alternatives, and wait for user decision. Never write conflicting content.

**Rationale:** "Ask forgiveness" is wrong for config files that affect daily work. One silent glob collision = hours of debugging "why is my AI behaving differently." Prevention over recovery.

### Decision 9: Gitignore Management

**Decision:** Append-only block with clear delimiters.

```gitignore
# === AGENTIC-OS GENERATED (do not edit this block) ===
CLAUDE.md
.cursor/rules/900-agentic-os.mdc
.clinerules
.agents/.agentic-os-manifest.json
# === END AGENTIC-OS GENERATED ===
```

The `--remove` command strips this exact block. The `--track` flag skips gitignore entirely.

**Rationale:** Delimited block enables clean removal without parsing complex gitignore files. The comment makes it obvious to humans what's managed.

---

## Implementation Patterns & Consistency Rules

### File Naming Patterns

| Artifact Type | Convention | Example |
|--------------|------------|---------|
| Skill files | UPPERCASE.md or lowercase-kebab.md | SKILL.md, catalog.md |
| Template files | lowercase-kebab.md | persona-routing.md |
| Adapter files | lowercase-runtime-name.md | claude.md, cursor.md |
| Example files | lowercase-purpose.md | simple-output.md |
| Generated configs | Follow target runtime convention | .cursor/rules/NNN-*.mdc |
| Manifest | dot-prefixed JSON | .agentic-os-manifest.json |

### Markdown Authoring Patterns for AI-Readable Content

**Structure pattern for all skill sub-files:**
```markdown
# {Title}

## Purpose
One sentence explaining what this file is for.

## {Main Content Sections}
...

## Usage Context
When this file is relevant and how the AI should use it.
```

**Placeholder syntax:** `{variable_name}` for single values, `{for each item}...{end for}` for iteration. These are not executed — they're instructions to the AI about what to substitute.

### Shell Script Patterns

**Flag parsing:** Use `getopts` or manual case parsing (POSIX compatible, no bashisms).

**Exit codes:**
- 0: Success
- 1: Invalid flags/arguments
- 2: Missing dependencies
- 3: Conflict detected (--remove found modified files)

**Output format:** Minimal, actionable. One instruction per line. Color only via tput (portable).

### Generated Output Patterns

**Managed block markers (for future Phase 2 re-run):**
```markdown
<!-- MANAGED BY AGENTIC-OS | hash:sha256:abc123 | DO NOT EDIT -->
{generated content}
<!-- END MANAGED BY AGENTIC-OS -->
```

Even in Phase 1 (no re-run), include these markers so Phase 2 can detect them later without regenerating all files.

**Cursor .mdc generation rules:**
- YAML frontmatter is required (description, globs)
- `alwaysApply: true` only when the rule genuinely applies to all matched files
- Globs must be specific (never `*` alone for agentic-os rules)
- Description must be human-readable and explain intent

---

## Project Structure & Boundaries

### Complete Directory Structure (what this feature adds to agentic-os)

```
agentic-os/                          (existing repo root)
├── setup.sh                         (MODIFIED: add --ai, --runtime, --dry-run, --remove, --track, --target, --auto flags)
├── pytest.ini                       (NEW: pytest configuration — test paths, JUnit XML output)
├── .agents/
│   └── skills/
│       └── agentic-os-setup/        (NEW: AI-installer skill directory)
│           ├── SKILL.md             (orchestrator — entry point for AI execution)
│           ├── catalog.md           (signal catalog — known patterns + meanings)
│           ├── agents/
│           │   └── openai.yaml      (Agent Skills open standard metadata)
│           ├── templates/
│           │   ├── persona-routing.md
│           │   ├── scope-isolation.md
│           │   ├── cross-reference.md
│           │   ├── naming-enforcement.md
│           │   └── quality-gates.md
│           ├── adapters/
│           │   ├── claude.md
│           │   ├── cursor.md
│           │   ├── cline.md
│           │   └── antigravity.md
│           └── examples/
│               ├── simple-output.md
│               └── complex-output.md
├── examples/                        (NEW: test repo fixtures)
│   ├── uj-1-node-monorepo/
│   ├── uj-2-architect-monorepo/
│   ├── uj-3-flask-simple/
│   └── uj-4-rust-antigravity/
├── tests/                           (NEW: automated test suite)
│   ├── test_setup.sh               (POSIX sh — flag parsing tests)
│   ├── test_content.py             (pytest — content validation)
│   ├── conftest.py                 (pytest hook — plaintext report generation)
│   └── results/                    (gitignored — test output)
│       ├── shell/report.txt
│       └── python/report.xml, report.txt
└── (no other root-level changes)
```

### What Gets Generated (in user's repo, not in agentic-os source)

```
user-repo/                           (after AI-installer executes)
├── CLAUDE.md                        (if --runtime includes claude)
├── AGENTS.md                        (if complexity ≥ Multi)
├── GOALS.md                         (if complexity = Complex)
├── .cursor/
│   └── rules/
│       └── NNN-agentic-os.mdc      (if --runtime includes cursor)
├── .clinerules                      (if --runtime includes cline)
├── .agents/
│   └── .agentic-os-manifest.json   (always — tracks what was generated)
└── .gitignore                       (appended with managed block, unless --track)
```

### Boundary Definitions

**Bootstrap boundary (setup.sh):**
- Input: CLI flags
- Output: Skill presence verified (ships in-tree), setup context written to `.agents/.agentic-os-setup-context.json`, terminal instruction printed
- Context bridge: setup.sh writes `{ "runtimes": [...], "dry_run": bool, "track": bool, "auto": bool }` so the AI skill knows what flags were passed
- Target resolution: `--target <path>` changes working directory before all operations (default: CWD). setup.sh copies the agentic-os-setup skill and workspace infrastructure into the target before writing the context bridge, so all files are local when the AI runs.
- Does NOT cross into: repo scanning, config generation, AI interaction

**AI execution boundary (SKILL.md):**
- Input: Entire repository filesystem (read-only scan) — all infrastructure is already local (setup.sh copied it)
- Responsibilities: Create/update AGENTS.md, infer GOALS.md, generate runtime-specific config (CLAUDE-agentic-os.md, etc.)
- Data sources: catalog.md, templates/, adapters/, examples/ (all at `.agents/skills/agentic-os-setup/`)
- Output: Proposed file contents (presented as diffs)
- Write authority: Only after explicit user approval (or auto-mode)
- State: Reads/writes manifest.json (tracks all AI-generated files)

**Adapter boundary:**
- Input: Structured intent (domain list, personas, relationships)
- Output: Runtime-specific formatted content
- Does NOT cross into: detection logic, approval workflow

**Manifest boundary:**
- Created by: AI-installer (write)
- Read by: setup.sh --remove (for cleanup), AI-installer re-run detection (Phase 2)
- Never read by: the generated configs themselves

---

## Validation Checklist

### Architectural Coherence

- [x] Single source of truth: SKILL.md is the only file with execution logic
- [x] Separation of concerns: script (bootstrap) / skill (logic) / catalog (data) / templates (patterns) / adapters (format)
- [x] No circular dependencies between components
- [x] Each component can be updated independently
- [x] New runtimes = add one adapter file (no orchestrator changes)
- [x] New rule types = add one template file (no orchestrator changes)
- [x] New signals = add entry to catalog (no structural changes)

### PRD Requirement Coverage

| FR | Covered By | Architecture Component |
|----|-----------|----------------------|
| FR-1 (flags) | setup.sh | Bootstrap boundary |
| FR-2 (runtime targeting) | setup.sh + SKILL.md | Flag parsing + adapter selection |
| FR-3 (uninstall) | setup.sh + manifest | Manifest read + file deletion |
| FR-4 (discoverability) | setup.sh | Classic output modification |
| FR-5 (scanning) | SKILL.md + catalog.md | Scanning protocol + signal matching |
| FR-6 (classification) | SKILL.md + catalog.md | Classification logic |
| FR-7 (proposal) | SKILL.md + templates + adapters | Template filling + adapter formatting |
| FR-8 (relationships) | SKILL.md | Relationship discovery protocol |
| FR-9 (signal catalog) | catalog.md | Standalone data file |
| FR-10 (diff preview) | SKILL.md | Approval workflow section |
| FR-11 (dry-run) | SKILL.md | Mode detection section |
| FR-12 (approval gate) | SKILL.md | Write protocol section |
| FR-13 (glob collision) | SKILL.md + adapters/cursor.md | Conflict detection + cursor-specific rules |
| FR-14 (numbering) | SKILL.md + adapters/cursor.md | Cursor adapter constraint |
| FR-15 (non-destructive) | SKILL.md | Core invariant in scanning + write protocol; .gitignore and AGENTS.md allow append-only managed blocks |
| FR-16 (framework coexistence) | SKILL.md + catalog.md | Signal for _bmad/ with "defer" behavior |
| FR-17 (Claude adapter) | adapters/claude.md | Create new CLAUDE.md |
| FR-18 (Cursor adapter) | adapters/cursor.md | Create new .mdc with glob/numbering logic |
| FR-19 (Cline adapter) | adapters/cline.md | Create new .clinerules |
| FR-20 (Antigravity adapter) | adapters/antigravity.md | Extend existing AGENTS.md with managed block (UJ-4) |
| FR-21 (manifest) | SKILL.md + manifest format | Write protocol + JSON schema |
| FR-22 (gitignore) | SKILL.md + setup.sh | Write protocol + --track flag |
| FR-23 (README update) | README.md | Document --ai path, update architecture diagram, add runtimes |
| FR-24 (CONTRIBUTING.md) | CONTRIBUTING.md | Guide for adding signals, templates, adapters; testing protocol |
| FR-25 (target directory) | setup.sh | --target flag, resolve dir before all operations |
| FR-26 (auto-approval) | setup.sh + SKILL.md | --auto flag, context bridge `auto` field, skip approval gate |
| FR-27 (test fixtures) | examples/ | 4 UJ-based directory structures |
| FR-28 (shell test runner) | tests/test_setup.sh | POSIX sh flag/routing tests |
| FR-29 (Python validator) | tests/test_content.py | pytest structural validation |
| FR-30 (results gitignored) | .gitignore | tests/results/ excluded |
| FR-31 (workspace bootstrapping) | setup.sh + SKILL.md | setup.sh copies infrastructure; AI creates AGENTS.md, infers GOALS.md |

### Risk Mitigations Confirmed

| Risk | Mitigation in Architecture |
|------|---------------------------|
| Config breaks existing workflows | Conflict detection in SKILL.md is mandatory pre-write step |
| Complexity wall (too many files) | Tier-gated output defined in SKILL.md classification logic |
| User edit corruption on re-run | Managed block markers included from Phase 1; manifest tracks hashes |
| Privacy/security exposure | Manifest location in .agents/ (gitignored); generated files gitignored by default |

---

## Pull Request

The PR document for this feature is at `pull-request.md` in this directory. It serves as the template for opening the upstream PR to itseffi/agentic-os and documents the BMad Method planning process, key design decisions, testing instructions, and scope boundaries.

---

## Test Infrastructure Architecture

### Decision 10: Test Repo Fixtures

**Decision:** Real directory structures in `examples/` mimic each UJ's repo layout.

```
examples/
├── uj-1-node-monorepo/       (UJ-1: Alex's Node.js monorepo with Cursor rules)
│   ├── package.json          (workspaces: ["packages/*"])
│   ├── .cursor/rules/
│   │   ├── 002-dates.mdc
│   │   ├── 003-eslint.mdc
│   │   └── 005-api.mdc
│   ├── packages/
│   │   ├── api/package.json
│   │   └── web/package.json
│   ├── src/
│   └── tests/
├── uj-2-architect-monorepo/  (UJ-2: Sam's complex documentation monorepo)
│   ├── Designs/
│   ├── Operations/
│   │   ├── job-descriptions/
│   │   └── job-interviews/
│   ├── Team-Workitems/
│   ├── Infrastructure/
│   ├── _bmad/
│   ├── .cursor/rules/        (10 files, 800-band)
│   └── AGENTS.md
├── uj-3-flask-simple/        (UJ-3: Jordan's simple Flask project)
│   ├── src/
│   │   └── app.py
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
└── uj-4-rust-antigravity/    (UJ-4: Riley's Rust workspace)
    ├── Cargo.toml            ([workspace] with members)
    ├── api/
    │   └── Cargo.toml
    ├── core/
    │   └── Cargo.toml
    ├── shared/
    │   └── Cargo.toml
    └── AGENTS.md
```

**Rationale:** Real structures (not mocks or descriptions) enable `setup.sh --ai --target examples/uj-X` to exercise the full flow. Each fixture represents a distinct complexity tier and runtime scenario.

### Decision 11: Dual Test Runner Strategy

**Decision:** Shell tests for setup.sh behavior + Python tests for generated content validation.

| Layer | Runner | What It Tests | Results |
|-------|--------|---------------|---------|
| CLI behavior | `tests/test_setup.sh` (POSIX sh) | Flag parsing, routing, error cases, --remove | `tests/results/shell/report.txt` (plaintext) |
| Content quality | `tests/test_content.py` (pytest) | Manifest schema, .mdc validity, glob rules, managed blocks | `tests/results/python/report.xml` (JUnit XML) + `tests/results/python/report.txt` (plaintext) |

**Configuration files:**
- `pytest.ini` — Configures test paths and `--junitxml` output
- `tests/conftest.py` — Generates plaintext report via `pytest_sessionfinish` hook

**5 test scenarios:**
1. Simple project (uj-3 fixture) — verify simple tier, minimal output
2. Complex project (uj-2 fixture) — verify complex tier, BMAD deferral
3. Collision detection (uj-1 fixture with overlapping glob) — verify abort on conflict
4. Clean uninstall (any fixture post-setup) — verify zero leftovers
5. Auto-mode (uj-3 fixture + --auto --runtime claude) — verify no-pause write

**Results gitignored:** `tests/results/` in `.gitignore`.

**Rationale:** Shell tests validate the bootstrap layer (no Python dependency for core script). Python tests validate structural correctness of generated artifacts (JSON schema, YAML parsing, regex matching for markers). Both are needed because setup.sh is POSIX sh but generated content needs structured validation.

---

## Implementation Sequence

### Phase 1 Implementation Order

1. **setup.sh modifications** — Add flag parsing, --remove logic, discoverability message
2. **SKILL.md orchestrator** — Core reasoning framework, mode detection, scanning protocol, classification, proposal, approval, write protocol
3. **catalog.md** — Initial signal catalog (15-20 signals covering common patterns)
4. **adapters/claude.md** — Claude Code output formatting reference
5. **adapters/cursor.md** — Cursor .mdc output formatting reference (most complex due to glob handling)
6. **adapters/cline.md** — Cline output formatting reference
7. **adapters/antigravity.md** — Antigravity AGENTS.md formatting reference
8. **templates/persona-routing.md** — First rule template
9. **templates/scope-isolation.md** — Second rule template
10. **templates/cross-reference.md** — Third rule template
11. **templates/naming-enforcement.md** — Fourth rule template
12. **templates/quality-gates.md** — Fifth rule template
13. **examples/simple-output.md** — Calibration: what tier 1-2 output looks like
14. **examples/complex-output.md** — Calibration: what tier 3-4 output looks like
15. **Testing** — Manual testing across runtimes with sample repos

### Dependencies Between Components

```
setup.sh ─── independent (no deps)
SKILL.md ─── depends on: catalog.md, templates/*, adapters/*, examples/*
catalog.md ─── independent (pure data, follows interface contract below)
templates/* ─── independent (pure patterns, follows interface contract below)
adapters/* ─── independent (pure format specs, follows interface contract below)
examples/* ─── depends on: templates + adapters (shows their combined output)
```

**Parallel development strategy:** Leaf components (catalog, templates, adapters) can be developed in parallel with SKILL.md IF they follow these interface contracts:

| Component | Contract (structure SKILL.md expects) |
|-----------|--------------------------------------|
| catalog.md | Each signal: `## Signal: <name>` with subsections: Pattern, Indicates, Complexity impact, Setup implications, Coexistence |
| templates/*.md | Each template: `# Template: <name>` with subsections: Intent, Inputs Required (`{placeholder}`), Output Pattern (per runtime), When to Use |
| adapters/*.md | Each adapter: File path convention, Format specification, Constraints, Pre-existing file behavior, Examples (2+) |

**Integration point:** SKILL.md is written last (or iteratively) as it consumes all leaf components. Examples are written after both templates and adapters since they demonstrate combined output. The claimed parallelism is real for leaf files but SKILL.md itself is the integration test — it cannot be finalized until leaf files stabilize.
