---
name: agentic-os-setup
description: AI-assisted repo setup — scans structure, classifies complexity, infers GOALS.md, generates runtime-specific configuration. Use when the user says "run agentic-os setup", "set up my repo", or "configure agentic-os".
---

# Agentic-OS AI-Assisted Setup

## Purpose

Intelligent, complexity-aware setup for agentic-os. Performs two jobs:

1. **Workspace bootstrapping** — Creates the agentic-os workspace structure (directories, AGENTS.md, GOALS.md, BACKLOG.md, symlinks, skills, workflows) in the target repo, auto-populating GOALS.md from repo analysis instead of a questionnaire.
2. **Configuration generation** — Scans repo structure, classifies complexity, proposes runtime-specific configuration proportional to detected needs, previews as unified diffs, and writes only after approval.

Both jobs run in sequence. The AI replaces the classic setup questionnaire entirely — it infers what the questionnaire would have asked from the repo's own signals.

## Mode Detection

Before beginning, check for the context bridge file at `.agents/.agentic-os-setup-context.json`. If present, read it to determine:
- `runtimes`: which runtime adapters to generate for
- `dry_run`: if true, perform full analysis and proposal but write zero files
- `track`: if true, skip gitignore management (files will be committed)
- `auto`: if true, show the diff preview but skip the approval gate — write immediately after presenting diffs

Note: By the time you run, `setup.sh` has already bootstrapped the workspace (copied skills, workflows, dirs, BACKLOG.md, symlinks into this repo). Your job is the smart parts: scan, classify, infer GOALS.md, generate runtime config, and handle files that need cross-referencing (CLAUDE.md, AGENTS.md, etc.).

**Track vs Gitignore decision:** If `track` is not explicitly set in the context bridge (i.e., the user didn't pass `--track`), YOU decide based on repo signals:
- **Gitignore (private):** Personal workspace, solo developer, no team indicators, sensitive content (personal goals, private structure)
- **Track (shared):** Team repo, multiple contributors in git log, existing shared configs (.cursor/rules/, AGENTS.md already tracked), CI/CD present, CONTRIBUTING.md exists

If you decide to track (not gitignore), skip the gitignore managed block entirely. State your reasoning in the proposal: "These files appear team-relevant and will be tracked in git (not gitignored)."

If the context bridge file is not present, ask the user which runtimes they want and whether this is a dry run.

Check for an existing manifest at `.agents/.agentic-os-manifest.json`:
- If manifest exists: this is a **re-run**. Phase 1 does not support re-run — inform the user that re-run with delta merging is planned for Phase 2, and suggest `setup.sh --remove` followed by a fresh `--ai` run if they want to regenerate.
- If no manifest: this is a **first-run**. Proceed with workspace bootstrapping, then scanning.

## AI Responsibilities (Post-Bootstrap)

`setup.sh` has already handled the "dumb" copying: directories, BACKLOG.md, Workflows/, .agents/skills/, symlinks, .gitignore template. Your job is the smart inference and generation:

### 1. Create or update AGENTS.md

If `AGENTS.md` does NOT exist: generate a **complete** AGENTS.md that combines:

**A) All standard agentic-os behavioral instructions** (these are NOT optional — they make the AI useful):
- How to Work With Files (read, write, list, search patterns)
- Task File Format (full YAML frontmatter template: title, category, priority, status, dates, resource_refs)
- Priority Levels — MUST use P0/P1/P2/P3 format exactly:
  - **P0**: Critical/urgent, must do THIS WEEK (max 3 recommended)
  - **P1**: Important, has deadlines, affects others (max 5 recommended)
  - **P2**: Normal priority, can be scheduled (default)
  - **P3**: Low priority, nice-to-have
- Backlog Processing Workflow (step-by-step: read → gather context → dedup check → clarify → create → summarize)
- Daily Guidance Workflow (read tasks → filter active → read goals → recommend focus → flag blocked)
- Goals Alignment rules (tie tasks to goals, flag orphan tasks)
- Skills Reference table (categorized: planning, building, analysis, research, decisions, strategy, meetings, stakeholders)
- Skill Routing Policy (execution-first: small task → direct edit, medium → plan+tdd, large → prd+plan+tdd)
- Workflows Reference table (prompt → workflow file mapping)
- Helpful Prompts section (examples: "Show my P0 and P1 tasks", "List blocked tasks", "Archive completed tasks", "Create an eval for this session")
- Subagent Delegation patterns (when to use, when not to, delegation order, output contract)
- Verification Discipline (identify → run → verify → only then claim done)
- Interaction Style (direct, batch questions, never delete user content)
- Session Evals (when to create, eval workflow steps)
- Maintenance Tasks — MUST include ALL of these:
  - Prune completed tasks (>30 days old → archive)
  - Check priority distribution (warn if >3 P0 or >5 P1)
  - Update AGENTS.md (when learning something important about user preferences or workflow, suggest adding it here)
  - Review evals (weekly, apply learnings)
- Writing Style Guidelines (avoid cliches, be direct and concise)

**B) Repo-specific customizations** (discovered during scanning):
- **Workspace layout** — the ACTUAL directory structure two levels deep
- **Task categories** — derived from concern domains found (not generic — use #devex-platform, #access-management, etc.)
- **Scope boundaries** — real isolation rules between domains
- **Cross-references** — real linkage rules between related folders
- **Naming standards** — real patterns detected in each domain

The workspace layout should go **two levels deep** for major directories:
```
docs/workitems/           — Cross-project work items (ZSP, CI, Crossplane)
docs/workitems/devex/     — DevEx Platform project (130+ items, ADO-synced)
docs/designs/             — Architecture decisions and designs
  ├── access-management/  — ZSP AWS access model
  ├── github-jira-migration-plan/
  └── ... (11 initiatives)
```

**Critical:** The behavioral sections (A) must be COMPLETE — don't summarize them into one-liners. The repo-specific sections (B) replace the generic equivalents from the template. The result should be a full operational manual for the AI, not a summary.

If `AGENTS.md` already exists: extend it with a managed block containing agentic-os behavioral rules (scope isolation, cross-references, etc.) — same as Antigravity adapter behavior.

### 2. Create or update AI tool wrapper files

For each targeted runtime, create the appropriate wrapper file if it doesn't exist:
- **Claude**: `CLAUDE.md` — if missing, create with `@AGENTS.md` and a Skills section pointing to `.agents/skills/`. If exists, create `CLAUDE-agentic-os.md` companion that includes the Skills section.
- **Codex**: `CODEX.md` — if missing, create with reference to AGENTS.md + skill location.
- **Pi**: `PI.md` — if missing, create with reference to AGENTS.md + skill location.
- **OpenClaw**: `OPENCLAW.md` — if missing, create with reference to AGENTS.md + skill location.

The Claude wrapper (or companion) MUST include a section like:
```markdown
## Skills

Canonical skills are available at `.agents/skills/*/SKILL.md` (also accessible via `.claude/skills/`).
To run a skill: read its SKILL.md and follow the instructions within.
```

This ensures Claude Code knows where skills live even if auto-discovery doesn't surface them.

### 3. Auto-generate GOALS.md

Instead of asking a questionnaire, infer goals from repo signals. Use the **deep scanning results** — don't just read top-level, read the actual work being done:

| Classic Question | AI Inference Source |
|-----------------|-------------------|
| "What's your current role?" | README, CONTRIBUTING, package.json author, git config, folder structure purpose. Also: what kind of work lives here (architecture docs → architect; work items → team lead; hiring → manager) |
| "What's your professional vision?" | Repo scope: what domain it serves, what it's building toward. Look at design docs and POM artifacts for strategic intent. |
| "12-month success criteria?" | Major initiatives in designs/ (each subfolder = a goal). Active epics in work items. Hiring roles = team growth goal. |
| "This quarter objectives?" | Recent commits focus, active branches, work-in-progress items. What's in draft state vs completed. |
| "Top 3 priorities?" | Largest/most-active subfolders. Most-recent work items. Active hiring positions. |
| "Key initiatives?" | Each major design folder, each project-scoped work item subfolder, active hiring rounds — present as a table with status |

Write `GOALS.md` using the standard template structure. Mark inferred sections with `[AI-inferred — refine as needed]`. Leave unknowable fields empty with `<!-- Fill in: your answer here -->`.

Include a **Key Initiatives** table that maps the actual work streams found (with file counts and activity indicators). This gives the user immediate visibility into what the AI detected as their active work.

### 4. Generate runtime-specific configuration

This is the classification + proposal flow (Scanning → Classification → Proposal → Preview → Write) described in the sections below.

---

## Scanning Protocol

### What to Read

Scan the repository filesystem **two levels deep** for structural signals. The goal is to understand not just top-level folders but the project/team/initiative scoping within them:

**Level 1 — Root directories:**
1. **Top-level directories** — list all directories at root (ignore hidden dirs except `.cursor/`, `.claude/`, `.cline/`)
2. **Config files at root** — package.json, pyproject.toml, Cargo.toml, go.mod, Makefile, docker-compose.yml, terraform/, .github/
3. **Existing AI configuration** — .cursor/rules/*.mdc, CLAUDE.md, .clinerules, AGENTS.md, .claude/
4. **Agent frameworks** — _bmad/, .agents/ contents
5. **Documentation** — docs/, README.md, CONTRIBUTING.md
6. **Team indicators** — directories containing "team", group-based folder structures

**Level 2 — Subdirectory structure (critical for complexity detection):**
7. **Scan one level inside each major directory** (docs/, src/, packages/, etc.) to identify:
   - **Project/team scoping** — subdirectories that represent distinct projects, teams, or initiatives (e.g., `docs/workitems/devex/` is a project-scoped collection, not just "workitems")
   - **Initiative groupings** — design folders that each represent a major work stream (e.g., `docs/designs/access-management/`, `docs/designs/github-jira-migration-plan/`)
   - **Role-based folders** — hiring/interview folders scoped by position (e.g., `docs/JoBInterviews/2026-PlatformEng/`)
   - **File count per subfolder** — a folder with 130 files is a major concern; a folder with 3 is a leaf

8. **Identify the real concern domains** — don't just map top-level directories. Understand what WORK is being done:
   - If `docs/workitems/devex/` has 130 items and `docs/workitems/` root has 15, then "DevEx Platform" is the primary project, not just "workitems"
   - If `docs/designs/` has 11 subdirectories, each is likely a distinct initiative worth naming
   - If there are role-specific interview/position folders, hiring is an active concern domain

9. **Assess initiative scale** — for each concern domain identified:
   - Count files to gauge volume
   - Note naming patterns (ADO IDs, date prefixes, kebab-case)
   - Identify active vs archived (recent dates vs old)
   - Look for cross-references between domains (work items referencing designs, interviews referencing positions)

### What NOT to Read

- File contents beyond config/manifest files (respect privacy — NFR-5)
- Binary files
- node_modules/, .git/, build artifacts, vendor/
- Any file > 100KB

### Signal Matching

Cross-reference detected patterns against `catalog.md`. For each matched signal, note:
- Which complexity dimension it contributes to
- What setup implications it carries
- Any coexistence behavior required

## Classification Logic

Use the **highest-dimension-wins** scoring algorithm:

### Dimensions

| Dimension | Zero | Simple | Multi | Complex |
|-----------|------|--------|-------|---------|
| Top-level concern folders | 0 | 1-2 | 3-4 | 5+ |
| Project-scoped subfolders (distinct initiatives/teams within a domain) | 0 | 0 | 1-2 | 3+ |
| Existing AI config files | 0 | 0-1 | 2-3 | 4+ |
| Team/group indicators | 0 | 0 | 1 | 2+ |
| Cross-domain references detected | 0 | 0 | 1 | 2+ |
| Agent framework present (_bmad/, etc.) | No | No | No | Yes |

### Algorithm

1. For each dimension, map the detected count to a tier (Zero=0, Simple=1, Multi=2, Complex=3)
2. Take the maximum score across all dimensions
3. If max = 0 → **Zero** tier; 1 → **Simple**; 2 → **Multi**; 3 → **Complex**
4. Present the classification WITH the scoring breakdown so the user can challenge it

### Override Protocol

Always propose the classification with rationale. The user can override up or down. Respect the override without argument.

### Calibration

- A repo with `_bmad/` is automatically Complex (framework presence is a strong signal)
- A repo with only `src/` and `tests/` should never exceed Simple regardless of file count
- See `examples/simple-output.md` and `examples/complex-output.md` for calibration

## Proposal Generation

Based on the classified tier and detected signals, assemble a configuration proposal:

### Tier Output Expectations

| Tier | What Gets Generated |
|------|-------------------|
| Zero | Nothing — repo is empty. Suggest running classic `setup.sh` instead. |
| Simple | 1 config file per targeted runtime. Minimal: basic project context, no persona routing. |
| Multi | Config files per runtime + AGENTS.md with persona definitions. Persona routing, scope isolation. |
| Complex | Full output: AGENTS.md, GOALS.md (if none exists), config files with persona routing, scope isolation, cross-reference enforcement, quality gates. |

### Assembly Process

1. Select applicable templates from `templates/` based on tier and detected signals (check each template's "When to Use" section)
2. Fill template placeholders with detected values (domains, personas, relationships)
3. Format output per runtime using the corresponding adapter in `adapters/`
4. Collect all proposed files into a unified proposal

### Relationship Discovery

- **Manifest-declared relationships** (found in package.json workspaces, go.work, etc.) are trusted — include them directly
- **AI-inferred relationships** (e.g., folder naming patterns suggest linkage) require user confirmation before inclusion in generated rules

## Framework Coexistence

When `_bmad/` directory is detected during scanning:
- Do NOT generate persona routing rules (defer persona ownership to BMAD)
- Limit generated rules to: scope isolation, cross-reference enforcement, naming patterns
- Explain what you're deferring and why in the proposal

When other AI configs exist (.cursor/rules/, CLAUDE.md, .clinerules):
- Do NOT modify or replace them
- Generate agentic-os rules as additive companion files (see adapter specs for pre-existing file behavior)
- Check for glob collisions with existing .cursor/rules/ before proposing new ones

## Diff Preview Protocol

All proposed changes MUST be presented as unified diffs before any files are written.

### New Files

Present as a diff against `/dev/null`:

```diff
--- /dev/null
+++ b/CLAUDE.md
@@ -0,0 +1,25 @@
+# Project Context
+
+{full file content with + prefix on each line}
```

### Extensions to Existing Files

For files being extended (e.g., AGENTS.md managed block append, .gitignore append):

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -42,0 +43,5 @@
+# === AGENTIC-OS GENERATED (do not edit this block) ===
+CLAUDE.md
+.agents/.agentic-os-manifest.json
+# === END AGENTIC-OS GENERATED ===
```

### Presentation Rules

1. Show ALL proposed files in a single diff block (or clearly labeled separate blocks)
2. Use standard unified diff format compatible with `patch` and `git apply`
3. Include file paths relative to repo root
4. For multi-file proposals, separate each file's diff with a blank line
5. After presenting diffs, clearly state: "These are the proposed changes. Approve all, approve selectively, or reject?"

### Selective Approval

The user can:
- **Approve all** — write everything as proposed
- **Approve selectively** — specify which files to write (e.g., "write CLAUDE.md and the manifest but skip the Cursor rules")
- **Reject** — write nothing, end the session

Respect the user's selection exactly. Only write approved files.

### Auto-Approval Mode

When `auto: true` is set in the context bridge:

1. Present all diffs exactly as in normal mode (for logging/audit)
2. **Do NOT wait for user approval** — proceed directly to writing
3. If conflict detection finds a collision: **FAIL with error** (do not silently overwrite). Print the conflict report and exit without writing any files.
4. If `dry_run` is also true: show diffs, write nothing (dry-run takes precedence over auto)

Auto mode is designed for unattended execution where the user has pre-selected their runtimes via `--runtime`. It still shows what will be written but doesn't pause for confirmation.

## Dry-Run Mode

When dry-run is active (detected from context bridge `dry_run: true` or user states "dry run"):

1. Execute the FULL workflow: scanning, classification, proposal generation
2. Present diffs exactly as in normal mode
3. **Write ZERO files to disk**
4. Do NOT create a manifest
5. Do NOT modify .gitignore
6. Clearly indicate at the start and end: "DRY RUN — no files will be written"

The user gets full visibility into what WOULD happen, without any side effects.

## Conflict Detection Protocol

Before writing ANY file, perform these safety checks:

### Cursor Glob Collision Detection

When proposing `.cursor/rules/` files:

1. List ALL existing `.mdc` files in `.cursor/rules/`
2. Parse YAML frontmatter of each to extract `globs` value
3. Compare each proposed glob against all existing globs
4. A collision exists if:
   - Proposed glob is identical to an existing glob
   - Proposed glob is a superset of an existing glob (e.g., `src/**/*` covers `src/components/**/*`)
   - Proposed glob overlaps with an existing glob (shared file matches)

**On collision:**
- Report: existing file name, its glob, proposed glob, and why they conflict
- Propose alternatives: narrower glob that avoids overlap, or skip that rule
- Never write a colliding rule without user approval of the alternative

### Numbering Respect

When generating Cursor `.mdc` files:
1. Scan existing files for their numeric prefixes
2. Identify the highest number in use
3. Use the next available number (e.g., if 805 exists, use 806)
4. NEVER renumber or move existing files
5. If no existing rules, default to 900-band

### Non-Destructive File Policy

**Core invariant:** Never modify or delete user files.

**Exceptions (append-only managed blocks):**
- `.gitignore` — append a delimited block at the end (never edit existing lines)
- `AGENTS.md` — append a managed block at the end (never edit existing content above the block)

**For all other existing files:**
- If the target path already exists and is NOT one of the append-only exceptions: create a companion file instead (see adapter specs for per-runtime behavior)
- If an existing managed block has been edited by the user (hash mismatch): warn and skip overwrite

### Framework Coexistence Check

When `_bmad/` is detected:
- Skip persona routing template entirely
- Explain in the proposal: "Persona routing deferred to BMAD framework (detected `_bmad/` directory)"
- Only generate: scope isolation, cross-reference enforcement, naming, quality gates

## Write Protocol

After the user approves the proposal (fully or selectively), write files following this exact sequence:

### Write Sequence

1. Create approved configuration files (CLAUDE.md, .cursor/rules/*.mdc, .clinerules, AGENTS.md extension)
2. Write the manifest (`.agents/.agentic-os-manifest.json`)
3. Update .gitignore (unless `--track` was specified)

### Manifest Schema

Write to `.agents/.agentic-os-manifest.json`:

```json
{
  "version": "1.0.0",
  "created_at": "<ISO 8601 timestamp>",
  "complexity_tier": "<zero|simple|multi|complex>",
  "runtimes_targeted": ["<runtime1>", "<runtime2>"],
  "files": [
    {
      "path": "<relative path from repo root>",
      "created_at": "<ISO 8601 timestamp>",
      "content_hash": "sha256:<hash of file content>"
    }
  ],
  "denied_relationships": [],
  "detected_frameworks": ["<framework names if any>"]
}
```

**Field definitions:**
- `version` — Schema version (always "1.0.0" for Phase 1). Future phases add fields but never remove or rename existing ones (additive-only evolution).
- `created_at` — When the setup was run
- `complexity_tier` — The classified tier
- `runtimes_targeted` — Which runtimes were configured
- `files` — Every file created or modified by this run. Each entry has the file path, creation timestamp, and SHA-256 hash of content.
- `denied_relationships` — Relationships the user rejected during proposal (prevents re-proposal on future re-runs)
- `detected_frameworks` — Frameworks found during scanning (e.g., "bmad")

**Important:** The manifest must include ALL generated files — this is what `setup.sh --remove` uses for clean uninstall. Missing entries = orphaned files on removal.

### Gitignore Management

**Default behavior** (when `--track` was NOT specified):

Append a managed block at the end of `.gitignore`:

```gitignore
# === AGENTIC-OS GENERATED (do not edit this block) ===
<path for each generated file>
.agents/.agentic-os-manifest.json
# === END AGENTIC-OS GENERATED ===
```

Rules:
- List every file path from the manifest's `files` array
- Include the manifest itself
- Always append at the end — never insert or modify existing gitignore content
- If `.gitignore` doesn't exist, create it with just the managed block
- The context bridge file (`.agents/.agentic-os-setup-context.json`) is NOT gitignored — it's ephemeral and deleted by `--remove`

**When `--track` is specified (explicit flag OR AI-inferred):**
- Do NOT modify `.gitignore`
- Generated files will be committed to the repository
- This is intentional — the configuration is shared with the team

**AI-inferred track decision** (when `track` is `false` in context bridge and user didn't explicitly pass `--track`):

Decide based on repo signals:
- **Gitignore** if: solo dev, personal workspace, no team indicators, sensitive/personal content
- **Track** if: team repo (multiple git authors), existing tracked AI configs (.cursor/rules/ committed), CONTRIBUTING.md present, CI/CD workflows exist, shared AGENTS.md already tracked

State the decision in the proposal. If you infer "track", explain why: "This appears to be a team repo (3 contributors, shared .cursor/rules/) — generated files will be tracked, not gitignored."

### Managed Block Specification

For files that use managed blocks (AGENTS.md, .gitignore):

**HTML-comment style** (for AGENTS.md and other markdown files):
```
<!-- MANAGED BY AGENTIC-OS | hash:sha256:<content-hash> | DO NOT EDIT -->
{content}
<!-- END MANAGED BY AGENTIC-OS -->
```

**Comment style** (for .gitignore and other non-markdown files):
```
# === AGENTIC-OS GENERATED (do not edit this block) ===
{content}
# === END AGENTIC-OS GENERATED ===
```

**Hash computation:**
- Hash the content BETWEEN the markers (not including markers themselves)
- Use SHA-256
- Store as hex string in the start marker
- Purpose: Phase 2 re-run can detect if user manually edited managed content

### Post-Write Confirmation

After writing all approved files:
1. Print a summary of what was written (file paths and sizes)
2. Confirm the manifest was created
3. Confirm gitignore status (updated or skipped due to --track)
4. Remind user: "To undo, run: setup.sh --remove"
