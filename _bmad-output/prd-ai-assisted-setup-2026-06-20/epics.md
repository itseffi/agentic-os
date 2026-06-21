---
stepsCompleted: [1, 2, 3]
inputDocuments: ['prd.md', 'architecture.md', 'addendum.md']
---

# AI-Assisted Complex Repo Auto-Setup - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the AI-Assisted Complex Repo Auto-Setup feature, decomposing the PRD and Architecture into implementable stories. This is a file-based system (markdown, shell scripts) — stories produce files, not code.

**Delivery:** The PR template for this feature is at `pull-request.md`. When all epics are complete, use that document as the basis for opening the upstream PR to itseffi/agentic-os.

## Requirements Inventory

### Functional Requirements

- FR-1: Flag-based mode selection (`setup.sh --ai` enables advanced, no flags = classic unchanged)
- FR-2: Runtime targeting (`--runtime <comma-separated-list>`, v1 valid values: `claude`, `cursor`, `cline`, `antigravity` — adding a runtime requires a new adapter file + setup.sh VALID_RUNTIMES update)
- FR-3: Clean uninstall (`setup.sh --remove` deletes only agentic-os generated files)
- FR-4: Discoverability (classic setup completion message includes `--ai` prompt)
- FR-5: Repo structure scanning (AI reads filesystem, builds structural profile)
- FR-6: Complexity classification (4 tiers: zero, simple, multi, complex)
- FR-7: Configuration proposal (output proportional to tier, tailored to repo)
- FR-8: Relationship discovery (manifest-declared trusted, AI-inferred requires confirmation)
- FR-9: Signal catalog (structured list of known patterns and meanings)
- FR-10: Unified diff preview (all proposed changes shown as diffs before write)
- FR-11: Dry-run mode (full analysis, no writes to disk)
- FR-12: Approval gate (explicit user confirmation before writing)
- FR-13: Glob collision detection (scan existing .mdc files for pattern overlap)
- FR-14: Existing rule numbering respect (append to next available in appropriate band)
- FR-15: Non-destructive file policy (never modify or delete user files)
- FR-16: Framework coexistence detection (defer persona ownership if _bmad/ detected)
- FR-17: Claude Code adapter (generates CLAUDE.md with routing and rules)
- FR-18: Cursor adapter (generates .cursor/rules/NNN-agentic-os.mdc with proper frontmatter)
- FR-19: Cline adapter (generates .clinerules)
- FR-20: Antigravity adapter (extends existing AGENTS.md with managed block)
- FR-21: Manifest tracking (JSON at .agents/.agentic-os-manifest.json)
- FR-22: Gitignore management (append managed block, unless --track)
- FR-23: README update (document --ai path, architecture diagram, runtimes)
- FR-24: CONTRIBUTING.md (guide for adding signals, templates, adapters)
- FR-25: Target directory (`--target <path>`, default CWD)
- FR-26: Auto-approval mode (`--auto` requires explicit `--runtime`, shows preview then writes)
- FR-27: Test repo fixtures (real directory structures for UJ-1 through UJ-4)
- FR-28: Shell test runner (POSIX sh, flag parsing validation)
- FR-29: Python content validator (pytest, structural validation of generated content)
- FR-30: Test results gitignored (tests/results/ excluded from tracking)
- FR-31: Workspace bootstrapping (copy agentic-os infrastructure to target, auto-generate GOALS.md from repo analysis)

### NonFunctional Requirements

- NFR-1: Zero regression to existing setup.sh behavior
- NFR-2: Cross-platform (macOS, Linux, Windows via WSL/Git Bash)
- NFR-3: POSIX sh compatible (no bashisms in setup.sh)
- NFR-4: Minimal external dependencies (git, jq); setup.sh verifies jq availability before --remove operations
- NFR-5: Privacy-respecting scan (don't read file contents beyond configs/manifests)
- NFR-6: Generated files gitignored by default (security-first)
- NFR-7: Test results isolated (tests/results/ gitignored, no pollution of tracked files)

### Additional Requirements

- AR-1: Managed block markers included from Phase 1 (for future Phase 2 re-run compatibility)
- AR-2: Signal catalog must be contributor-friendly (structured markdown, not code)
- AR-3: Rule templates use placeholder syntax (predictable, AI fills specifics)
- AR-4: Adapters are reference docs (one file per runtime, no code)
- AR-5: Manifest uses JSON for shell-parseability (jq) and AI-readability
- AR-6: SKILL.md is single entry point (AI reads one file to start)

### UX Design Requirements

N/A — no UI component in this system.

### FR Coverage Map

- FR-1, FR-2, FR-3, FR-4, FR-25, FR-26: Epic 1 (Bootstrap & CLI)
- FR-5, FR-6, FR-7, FR-8, FR-9, FR-31: Epic 2 (AI-Installer Skill Core)
- FR-10, FR-11, FR-12: Epic 3 (Preview & Approval)
- FR-13, FR-14, FR-15, FR-16: Epic 3 (Preview & Approval — safety checks)
- FR-17, FR-18, FR-19, FR-20: Epic 4 (Runtime Adapters)
- FR-21, FR-22: Epic 5 (Manifest & Cleanup)
- FR-23, FR-24: Epic 6 (Documentation)
- FR-27, FR-28, FR-29, FR-30: Epic 7 (Test Infrastructure)

## Epic List

### Epic 1: Bootstrap Entry Point
Users can invoke the AI-assisted setup via shell script flags, target any directory, run in auto-approval mode, cleanly remove agentic-os, and discover the feature through the classic setup flow.
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-25, FR-26

### Epic 2: AI-Installer Skill Core
Users can have their repo intelligently analyzed — structure scanned, complexity classified, relationships discovered, and configuration proposed — all by invoking a single AI skill.
**FRs covered:** FR-5, FR-6, FR-7, FR-8, FR-9

### Epic 3: Preview, Safety & Approval
Users see exactly what will change (as diffs), are protected from conflicts with existing configs, and must explicitly approve before anything is written.
**FRs covered:** FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16

### Epic 4: Runtime Adapters
Users get semantically equivalent configuration output in the native format of their chosen AI tools — Claude Code, Cursor, Cline, or Antigravity.
**FRs covered:** FR-17, FR-18, FR-19, FR-20

### Epic 5: Manifest & State Management
Users can track what was generated, cleanly uninstall, and have generated files gitignored by default for security.
**FRs covered:** FR-21, FR-22

### Epic 6: Documentation & Contributing
Users and contributors can understand the feature, its usage, and how to extend it through updated README and new CONTRIBUTING.md.
**FRs covered:** FR-23, FR-24

### Epic 7: Test Infrastructure
Developers and contributors can validate setup.sh behavior and generated content quality through automated tests running against real repo fixtures.
**FRs covered:** FR-27, FR-28, FR-29, FR-30

---

## Epic 1: Bootstrap Entry Point

Users can invoke the AI-assisted setup via shell script flags, cleanly remove agentic-os, and discover the feature through the classic setup flow.

### Story 1.1: Add --ai flag and argument parsing to setup.sh

As a developer,
I want to run `setup.sh --ai` to enable AI-assisted setup,
So that I can get intelligent configuration without affecting the classic flow.

**Acceptance Criteria:**

**Given** a user runs `setup.sh` without any flags
**When** the script executes
**Then** behavior is 100% identical to current implementation (regression-safe)
**And** no AI-related files are created or referenced

**Given** a user runs `setup.sh --help`
**When** the script executes
**Then** it prints usage information listing all available flags (--ai, --runtime, --dry-run, --remove, --track, --target, --auto, --help)
**And** exits without executing setup

**Given** a user runs `setup.sh --ai`
**When** the script executes
**Then** it verifies jq is installed (required for --remove); if missing, prints install guidance and continues (jq only blocks --remove, not --ai)
**And** the AI-installer skill directory `.agents/skills/agentic-os-setup/` is verified to exist (ships in-tree)
**And** `.agents/.agentic-os-setup-context.json` is written with resolved flags (runtimes, dry_run, track)
**And** the script prints clear invocation instructions for the user's AI tool
**And** the classic questionnaire is NOT executed

### Story 1.2: Add --runtime flag for targeting specific AI tools

As a developer,
I want to specify which AI runtimes to configure via `--runtime claude,cursor`,
So that I only get configuration for tools I actually use.

**Acceptance Criteria:**

**Given** a user runs `setup.sh --ai --runtime claude,cursor`
**When** the script validates the flag
**Then** only `claude` and `cursor` are passed as targeting context to the AI skill
**And** invalid runtime names produce a clear error listing valid options (claude, cursor, cline, antigravity)

**Given** a user runs `setup.sh --ai` without `--runtime`
**When** the script executes
**Then** all runtimes are targeted by default (the AI skill will detect which are present)

### Story 1.3: Add --remove flag for clean uninstall

As a developer,
I want to run `setup.sh --remove` to cleanly undo agentic-os setup,
So that I can safely try it without commitment anxiety.

**Acceptance Criteria:**

**Given** a user runs `setup.sh --remove` and jq is not installed
**When** the script checks dependencies
**Then** it prints "Error: jq is required for --remove. Install: brew install jq (macOS) or apt install jq (Linux)" and exits with code 2

**Given** a user runs `setup.sh --remove` and a manifest exists at `.agents/.agentic-os-manifest.json`
**When** the script reads the manifest (using jq)
**Then** every file listed in the manifest is deleted
**And** the gitignore managed block (`# === AGENTIC-OS GENERATED ===`) is removed
**And** the setup context file (`.agents/.agentic-os-setup-context.json`) is deleted
**And** the manifest file itself is deleted
**And** a summary of deleted files is printed

**Given** a user runs `setup.sh --remove` and no manifest exists
**When** the script checks for the manifest
**Then** it prints "No agentic-os installation found" and exits cleanly

**Given** setup.sh --remove runs
**When** checking each file in the manifest
**Then** user's original files (not in manifest) are NEVER deleted or modified

### Story 1.5: Add --target flag for directory targeting

As a developer,
I want to run `setup.sh --ai --target ./my-project` to configure a different repo,
So that I can set up agentic-os without being inside the target directory.

**Acceptance Criteria:**

**Given** a user runs `setup.sh --ai --target ./some-project`
**When** the script executes
**Then** workspace infrastructure is bootstrapped into `./some-project` (skills, workflows, dirs, symlinks)
**And** the context bridge is written at `./some-project/.agents/.agentic-os-setup-context.json`
**And** the AI skill is locally available at `./some-project/.agents/skills/agentic-os-setup/SKILL.md`
**And** CLAUDE.md in the target has a skills reference section appended (if not already present)

**Given** a user runs `setup.sh --ai --target ./nonexistent`
**When** the script validates the target
**Then** it prints "Error: target directory does not exist: ./nonexistent" and exits with code 1

**Given** a user runs `setup.sh --ai` without `--target`
**When** the script executes
**Then** CWD is used as the target (unchanged default behavior)

**Given** a user runs `setup.sh --remove --target ./some-project`
**When** the script executes removal
**Then** the manifest at `./some-project/.agents/.agentic-os-manifest.json` is read and files are deleted relative to `./some-project`

### Story 1.6: Add --auto flag for unattended approval

As a developer running setup in a CI/automation context,
I want `setup.sh --ai --auto --runtime claude` to run without interactive approval,
So that setup can complete unattended while still showing what was generated.

**Acceptance Criteria:**

**Given** a user runs `setup.sh --ai --auto --runtime claude`
**When** the script validates flags
**Then** the context bridge contains `"auto": true`
**And** the AI skill reads `auto: true` and skips the approval gate (shows preview then writes immediately)

**Given** a user runs `setup.sh --ai --auto` WITHOUT `--runtime`
**When** the script validates flags
**Then** it prints "Error: --auto requires explicit --runtime (cannot auto-detect in unattended mode)" and exits with code 1

**Given** the AI skill runs in auto mode and detects a glob collision
**When** reaching the conflict detection step
**Then** it fails with a non-zero exit (does NOT silently overwrite) and prints the conflict report

**Given** a user passes both `--auto` and `--dry-run`
**When** the AI skill executes
**Then** diffs are shown but nothing is written (dry-run takes precedence)

### Story 1.4: Add discoverability message to classic setup

As a first-time user who ran the classic setup,
I want to see a hint about the --ai option,
So that I know a smarter setup path exists.

**Acceptance Criteria:**

**Given** a user completes the classic `setup.sh` questionnaire
**When** setup finishes successfully
**Then** the final output includes: "Want AI-powered setup? Run: setup.sh --ai"
**And** it's a single line (not a wall of text)
**And** it appears after the success message, not before

---

## Epic 2: AI-Installer Skill Core

Users can have their repo intelligently analyzed — structure scanned, complexity classified, relationships discovered, and configuration proposed — by invoking a single AI skill.

### Story 2.5: Define workspace bootstrapping protocol in SKILL.md

As a user running AI-assisted setup against their existing project,
I want agentic-os to set up the full workspace infrastructure (directories, AGENTS.md, skills, workflows, GOALS.md) automatically,
So that my repo is immediately usable as a personal OS without running the classic questionnaire.

**Acceptance Criteria:**

**Given** the AI skill runs against a target repo that has no agentic-os infrastructure
**When** the bootstrap phase executes
**Then** it creates: Tasks/, Knowledge/, BACKLOG.md, copies AGENTS.md, Workflows/, .agents/skills/ from the agentic-os source
**And** ensures `.claude/skills/agentic-os-setup/` exists (symlink bridge if fresh, or copy into existing directory)
**And** creates .gitignore from template if none exists
**And** creates CLAUDE.md with `@AGENTS.md` if none exists
**And** all created files are tracked in the manifest

**Given** the AI skill scans the target repo for GOALS.md inference
**When** generating GOALS.md
**Then** it infers: role (from README/package.json/git config), vision (from project scope), quarterly objectives (from recent activity), priorities (from most-active areas)
**And** marks inferred content with `[AI-inferred — refine as needed]`
**And** leaves empty fields with `<!-- Fill in: your answer here -->`

**Given** the target repo already has some agentic-os artifacts (e.g., AGENTS.md exists)
**When** the AI encounters existing files
**Then** it skips or extends them (never overwrites)
**And** notes what was skipped in the proposal summary

**Given** setup.sh has already bootstrapped the workspace
**When** the AI skill runs
**Then** all supporting files (catalog.md, templates/, adapters/, examples/) are at `.agents/skills/agentic-os-setup/` locally — no external path resolution needed

---

### Story 2.1: Create SKILL.md orchestrator

As a user invoking the setup skill in their AI tool,
I want a single instruction file that guides the AI through the entire setup process,
So that any supported runtime can execute the same intelligent workflow.

**Acceptance Criteria:**

**Given** the file `.agents/skills/agentic-os-setup/SKILL.md` exists
**When** an AI runtime reads it
**Then** it contains: mode detection, scanning protocol, classification logic, proposal generation, approval workflow, and write protocol sections
**And** it references catalog.md, templates/*, adapters/*, and examples/* for supporting data
**And** the skill includes `agents/openai.yaml` with name, description, version, and invocation fields (Agent Skills open standard compliance)
**And** the SKILL.md has YAML frontmatter with `name: agentic-os-setup` and `description:` fields enabling Claude Code slash-command discovery (`/agentic-os-setup`) via `.claude/skills/` (works as symlink or directory)
**And** the scanning protocol specifies what to read (directory structure, config files, manifests) and what to skip (file contents, binary files)
**And** the write protocol enforces: never write without approval, never modify user files (except append-only managed blocks on .gitignore and AGENTS.md)
**And** the write protocol defines the managed block format specification: marker syntax (`<!-- MANAGED BY AGENTIC-OS | hash:sha256:<hash> | DO NOT EDIT -->`), hash algorithm (SHA-256 of block content), start/end delimiter rules, and behavior when user edits are detected inside a managed block (warn and skip overwrite)

### Story 2.2: Create signal catalog

As an AI executing the setup skill,
I want a structured catalog of known filesystem patterns and their meanings,
So that I can anchor my detection and avoid hallucinating repo structure.

**Acceptance Criteria:**

**Given** the file `.agents/skills/agentic-os-setup/catalog.md` exists
**When** an AI reads it during scanning
**Then** it contains at minimum 15 signal entries covering common patterns
**And** each entry has: Pattern, Indicates, Complexity impact, Setup implications, Coexistence behavior
**And** signals include: `.cursor/rules/`, `.claude/`, `.clinerules`, `_bmad/`, `package.json`, `pyproject.toml`, `Cargo.toml`, `terraform/`, `docs/`, `src/`, `.github/`, `docker-compose.yml`, `Makefile`, `AGENTS.md`, `go.mod`

**Given** a repo contains a pattern not in the catalog
**When** the AI encounters it
**Then** the catalog does not prevent the AI from reasoning about novel patterns (it's a reference, not a hard gate)

### Story 2.3: Create rule templates

As an AI generating configuration rules,
I want template files for each rule type with placeholder syntax,
So that I produce consistent, predictable output across repos.

**Acceptance Criteria:**

**Given** the directory `.agents/skills/agentic-os-setup/templates/` exists
**When** listing its contents
**Then** it contains: `persona-routing.md`, `scope-isolation.md`, `cross-reference.md`, `naming-enforcement.md`, `quality-gates.md`

**Given** any template file
**When** an AI reads it
**Then** it contains: Intent, Inputs Required (with `{placeholder}` syntax), Output Pattern per runtime (Cursor .mdc, CLAUDE.md section, AGENTS.md section), and When to Use criteria
**And** the "When to Use" section specifies which complexity tiers and signals trigger this template

### Story 2.4: Create calibration examples

As an AI generating configuration,
I want reference examples showing expected output for different complexity tiers,
So that I calibrate my output volume and depth appropriately.

**Acceptance Criteria:**

**Given** the directory `.agents/skills/agentic-os-setup/examples/` exists
**When** listing its contents
**Then** it contains: `simple-output.md` and `complex-output.md`

**Given** `simple-output.md`
**When** an AI reads it
**Then** it shows a complete example of tier 1-2 output (one config file per runtime, minimal)

**Given** `complex-output.md`
**When** an AI reads it
**Then** it shows a complete example of tier 3-4 output (AGENTS.md, GOALS.md, runtime configs with persona routing, scope isolation, relationship enforcement)

---

## Epic 3: Preview, Safety & Approval

Users see exactly what will change, are protected from conflicts, and must explicitly approve before anything is written.

### Story 3.1: Define diff preview protocol in SKILL.md

As a user reviewing proposed changes,
I want all changes presented as unified diffs before anything is written,
So that I see exact content and maintain control.

**Acceptance Criteria:**

**Given** the SKILL.md approval workflow section
**When** an AI reaches the proposal stage
**Then** it presents all new files as full-content diffs (`--- /dev/null`, `+++ b/path`)
**And** extensions to existing files show the added sections only
**And** the format is compatible with standard diff tools
**And** the user can reject individual files while approving others

### Story 3.2: Define dry-run mode in SKILL.md

As a user who wants to preview without committing,
I want a dry-run mode that performs full analysis but writes nothing,
So that I can evaluate what would happen before deciding.

**Acceptance Criteria:**

**Given** SKILL.md mode detection section
**When** the AI detects dry-run intent (user says "dry run" or `--dry-run` was passed)
**Then** full scanning, classification, and proposal generation runs normally
**And** diffs are presented exactly as in normal mode
**And** zero files are written to disk
**And** no manifest is created

### Story 3.3: Define conflict detection protocol in SKILL.md

As a user with existing .cursor/rules/ files,
I want the AI to detect glob collisions before writing,
So that my existing setup is never silently broken.

**Acceptance Criteria:**

**Given** SKILL.md conflict detection section
**When** the AI is about to generate a .cursor/rules/ file
**Then** it first scans ALL existing .mdc files for their glob patterns
**And** if any proposed glob overlaps with an existing glob, it reports the collision
**And** the collision report includes: existing file name, its glob, proposed glob, and why they conflict
**And** on collision: AI proposes alternatives (narrower glob) or skips that rule

**Given** an existing rule numbering convention (e.g., 800-805)
**When** the AI generates a new rule
**Then** it uses the next available number in the appropriate band (e.g., 806)
**And** it NEVER renumbers or moves existing files

### Story 3.4: Define framework coexistence in SKILL.md

As a user with BMAD or another agent framework installed,
I want agentic-os to detect it and defer persona ownership,
So that two persona systems don't conflict.

**Acceptance Criteria:**

**Given** SKILL.md framework coexistence section
**When** `_bmad/` directory is detected during scanning
**Then** AI does NOT generate persona routing rules
**And** generated rules are limited to: scope isolation, cross-reference enforcement, naming patterns
**And** the AI explains what it's deferring and why in the proposal

---

## Epic 4: Runtime Adapters

Users get semantically equivalent configuration in the native format of their chosen AI tools.

### Story 4.1: Create Claude Code adapter

As a Claude Code user,
I want generated CLAUDE.md that teaches Claude about my repo structure,
So that Claude Code gives contextually-aware responses.

**Acceptance Criteria:**

**Given** the file `.agents/skills/agentic-os-setup/adapters/claude.md` exists
**When** an AI reads it
**Then** it describes: file path (CLAUDE.md at repo root), format specification (markdown with sections/headers), constraints (what Claude Code can express), merge behavior (create new file), and 2+ concrete examples

**Given** the adapter is used for a Multi-tier repo
**When** generating CLAUDE.md
**Then** output includes persona routing, execution rules, and quality gates sections
**And** references AGENTS.md for persona definitions where applicable

### Story 4.2: Create Cursor adapter

As a Cursor user,
I want generated .cursor/rules/NNN-agentic-os.mdc with proper frontmatter,
So that Cursor enforces agentic-os rules natively.

**Acceptance Criteria:**

**Given** the file `.agents/skills/agentic-os-setup/adapters/cursor.md` exists
**When** an AI reads it
**Then** it describes: file path convention (.cursor/rules/NNN-agentic-os.mdc), YAML frontmatter format (description, globs, alwaysApply), numbering rules (respect existing convention, default to 900 band if no convention), glob specificity rules (never `*` alone), and 2+ examples

**Given** the adapter specifies glob collision detection
**When** the AI references this adapter
**Then** it knows to scan existing .mdc files before writing

### Story 4.3: Create Cline adapter

As a Cline user,
I want generated .clinerules configuration,
So that Cline follows agentic-os behavioral rules.

**Acceptance Criteria:**

**Given** the file `.agents/skills/agentic-os-setup/adapters/cline.md` exists
**When** an AI reads it
**Then** it describes: file path (.clinerules at repo root), format specification, constraints, merge behavior (create new file), and 2+ examples
**And** behavioral intent is semantically equivalent to Claude and Cursor outputs

### Story 4.4: Create Antigravity adapter

As an Antigravity user with an existing AGENTS.md,
I want agentic-os to extend my AGENTS.md with a managed block,
So that my original content is preserved while agentic-os rules are appended.

**Acceptance Criteria:**

**Given** the file `.agents/skills/agentic-os-setup/adapters/antigravity.md` exists
**When** an AI reads it
**Then** it describes: file path (AGENTS.md at repo root), format specification, merge behavior (EXTEND existing — never replace), managed block markers (canonical format: `<!-- MANAGED BY AGENTIC-OS | hash:sha256:<hash> | DO NOT EDIT -->` / `<!-- END MANAGED BY AGENTIC-OS -->`), and 2+ examples showing extension pattern

**Given** an existing AGENTS.md with user-written content
**When** the AI applies this adapter
**Then** user content stays intact above the managed block
**And** agentic-os rules are appended within the managed block below
**And** if no AGENTS.md exists, one is created entirely within managed markers

---

## Epic 5: Manifest & State Management

Users can track what was generated, cleanly uninstall, and have generated files gitignored by default.

### Story 5.1: Define manifest schema in SKILL.md

As a user who may want to uninstall later,
I want every generated file tracked in a manifest,
So that setup.sh --remove can cleanly undo everything.

**Acceptance Criteria:**

**Given** SKILL.md write protocol section
**When** the AI writes any file
**Then** it also writes/updates `.agents/.agentic-os-manifest.json` with: version, created_at, complexity_tier, runtimes_targeted, files array (path, created_at, content_hash), denied_relationships, detected_frameworks

**Given** the manifest schema
**When** setup.sh --remove reads it
**Then** it can parse the JSON with standard tools (jq or shell parsing)
**And** the files array provides exact paths for deletion

### Story 5.2: Define gitignore management in SKILL.md

As a user who doesn't want generated configs committed,
I want generated files gitignored by default,
So that my team structure and tooling aren't exposed in public repos.

**Acceptance Criteria:**

**Given** SKILL.md write protocol section
**When** the AI writes files and `--track` was NOT passed
**Then** it appends a clearly delimited block to .gitignore:
```
# === AGENTIC-OS GENERATED (do not edit this block) ===
<file paths>
# === END AGENTIC-OS GENERATED ===
```
**And** the block is at the end of .gitignore (append-only)

**Given** `--track` was passed during setup
**When** the AI writes files
**Then** .gitignore is NOT modified
**And** generated files are intended to be committed

---

## Epic 6: Documentation & Contributing

Users and contributors can understand the feature and how to extend it.

### Story 6.1: Update README.md

As a user discovering agentic-os,
I want the README to document both classic and AI-assisted setup paths,
So that I know my options immediately.

**Acceptance Criteria:**

**Given** the README.md Quick Start section
**When** a user reads it
**Then** it shows classic `./setup.sh` as step 2
**And** immediately below, shows AI-assisted as alternative: `./setup.sh --ai --runtime claude,cursor`
**And** briefly explains when to use each (simple project → classic, existing project → AI-assisted)

**Given** the Architecture mermaid diagram
**When** updated
**Then** it includes the AI-installer skill as a component
**And** shows its relationship to other system components

**Given** the README
**When** a user reads the AI-assisted setup section
**Then** it includes a new mermaid flow diagram showing the AI-assisted setup flow: `setup.sh --ai` → skill dropped → user invokes AI → scan → classify → propose → approve → generate
**And** the diagram clearly shows the three modes (first-run, dry-run, re-run placeholder)

**Given** the Agent Compatibility section
**When** updated
**Then** it lists Cursor, Cline, and Antigravity alongside existing runtimes
**And** mentions the `--runtime` flag for targeting

**Given** the File System Layout
**When** updated
**Then** it shows `.agents/skills/agentic-os-setup/` with brief description

### Story 6.2: Create CONTRIBUTING.md ✅ FULFILLED

**Status:** Already implemented as part of this planning work. CONTRIBUTING.md exists at repo root with full content covering signals, templates, adapters, testing protocol, and PR standards.

As a potential contributor,
I want clear guidance on how to extend the AI-installer (signals, templates, adapters),
So that I can contribute without reverse-engineering the system.

**Acceptance Criteria:**

**Given** CONTRIBUTING.md exists at repo root
**When** a contributor reads it
**Then** it covers: how to add signals, templates, and adapters with exact format examples
**And** includes development workflow (fork, branch, test, PR)
**And** references the license (CC BY-NC-SA 4.0)
**And** documents manual testing protocol (test repos, verification steps, coexistence checks)
**And** defines what makes a good PR (atomic, tested, documented, non-breaking)

---

## Epic 7: Test Infrastructure

Developers and contributors can validate setup.sh behavior and generated content quality through automated tests running against real repo fixtures.

### Story 7.1: Create test repo fixtures

As a developer testing the AI-installer,
I want real directory structures that mimic each user journey,
So that I can run `setup.sh --ai --target` against them and validate end-to-end behavior.

**Acceptance Criteria:**

**Given** the `examples/` directory exists
**When** listing its contents
**Then** it contains 4 subdirectories: `uj-1-node-monorepo/`, `uj-2-architect-monorepo/`, `uj-3-flask-simple/`, `uj-4-rust-antigravity/`

**Given** `examples/uj-1-node-monorepo/`
**When** examining its structure
**Then** it contains: `package.json` (with workspaces field), `.cursor/rules/` with 3 `.mdc` files (002-dates.mdc, 003-eslint.mdc, 005-api.mdc), `packages/api/package.json`, `packages/web/package.json`, `src/`, `tests/`
**And** each .mdc file has valid YAML frontmatter with description and globs

**Given** `examples/uj-2-architect-monorepo/`
**When** examining its structure
**Then** it contains: `Designs/`, `Operations/job-descriptions/`, `Operations/job-interviews/`, `Team-Workitems/`, `Infrastructure/`, `_bmad/`, `.cursor/rules/` with 10 files in 800-band, `AGENTS.md` with existing user content

**Given** `examples/uj-3-flask-simple/`
**When** examining its structure
**Then** it contains: `src/app.py`, `tests/`, `requirements.txt`, `README.md`
**And** no existing AI configuration files

**Given** `examples/uj-4-rust-antigravity/`
**When** examining its structure
**Then** it contains: `Cargo.toml` (with [workspace] members = ["api", "core", "shared"]), `api/Cargo.toml`, `core/Cargo.toml`, `shared/Cargo.toml`, `AGENTS.md` with existing user-written content

### Story 7.2: Create shell test runner

As a developer modifying setup.sh,
I want an automated test script that validates flag parsing and mode routing,
So that regressions are caught immediately.

**Acceptance Criteria:**

**Given** the file `tests/test_setup.sh` exists and is executable
**When** a developer runs it
**Then** it tests: --help output correctness, --ai routes to AI mode, --runtime validates valid/invalid values, --remove without manifest exits cleanly, --remove with manifest deletes tracked files, --target with valid path works, --target with invalid path errors, --auto without --runtime errors, --auto with --runtime sets context bridge correctly, flag combinations (--ai --dry-run --runtime, --ai --auto --runtime --target)
**And** results are written to `tests/results/shell/`
**And** exit code is 0 if all pass, non-zero on any failure

**Given** the test runner uses POSIX sh
**When** it runs
**Then** it requires no dependencies beyond sh, jq, and standard tools (grep, diff, rm, mkdir)

### Story 7.3: Create Python content validator

As a developer modifying templates or adapters,
I want automated validation that generated content meets structural requirements,
So that format regressions are caught before merge.

**Acceptance Criteria:**

**Given** the file `tests/test_content.py` exists
**When** a developer runs `pytest tests/test_content.py`
**Then** it validates against pre-generated content in `tests/results/python/`:
- Manifest JSON is valid and matches schema (version, files array, content_hash format)
- .mdc files have valid YAML frontmatter (description, globs fields present)
- No .mdc file uses bare `*` as its glob
- Managed block markers match canonical format (`<!-- MANAGED BY AGENTIC-OS | hash:sha256:... | DO NOT EDIT -->`)
- Gitignore block has start/end delimiters
- Cursor file numbering doesn't conflict with existing fixtures
**And** results are written to `tests/results/python/report.xml` (JUnit XML) and `tests/results/python/report.txt` (plaintext)
**And** `pytest.ini` configures test paths and XML output; `tests/conftest.py` generates plaintext report

**Given** the test suite covers 5 scenarios
**When** examining test cases
**Then** scenarios are: (1) simple project output validation, (2) complex project with BMAD deferral, (3) collision detection on overlapping globs, (4) clean uninstall leaves zero artifacts, (5) auto-mode completes without interaction

### Story 7.4: Configure test results gitignore

As a developer running tests locally,
I want test output to be gitignored,
So that generated artifacts don't pollute the repository.

**Acceptance Criteria:**

**Given** the repo's `.gitignore`
**When** examining its contents
**Then** it includes `tests/results/`

**Given** a developer runs the test suite
**When** tests complete
**Then** all output (generated files, logs, reports) is written under `tests/results/`
**And** no tracked files are modified by the test run
