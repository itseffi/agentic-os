# Calibration Example: Complex Tier Output

## Scenario

A multi-concern monorepo with `Designs/`, `Operations/`, `Team-Workitems/`, `Infrastructure/`, and `docs/` at root. Existing `.cursor/rules/` (files 800-805), existing AGENTS.md, existing `.clinerules`. Two team indicators. Cross-references between Operations and Designs.

**Detected signals:** .cursor/rules/ (6 files, 800-band), AGENTS.md, .clinerules, 5 concern folders, team indicators, cross-domain references
**Classification:** Complex (5+ concern folders, 4+ AI configs, 2 teams, 2+ cross-refs)
**Runtimes targeted:** claude, cursor, cline, antigravity

## Key principle for Complex tier

Complex repos accumulate the most rules — so the generated AGENTS.md MUST stay lean
(always-on rules + a Skills & Workflows index) and the step-by-step PROCEDURES are emitted
as on-demand skills under `.agents/skills/`. Never inline the full operational manual; it
overflows the context budget and burns tokens every turn. See `templates/context-budget.md`.

## Expected Output

### File: AGENTS.md (extended via managed block — existing user content preserved above)

The managed block holds ONLY always-on rules plus the index. Procedures are pointers.

```markdown
<!-- MANAGED BY AGENTIC-OS | hash:sha256:e3b0c44298fc1c149afbf4c8996fb924 | DO NOT EDIT -->
## Agentic-OS Generated Rules

### Workspace Layout
- Designs/<initiative>/ — architecture & system design
- Operations/ — process, recruitment, documentation
- Team-Workitems/ — work items (trace to Designs/ via Design-Ref:)
- Infrastructure/ — IaC, deployment, security baselines

### Scope Boundaries
| Domain | Isolated From | Rationale |
|--------|--------------|-----------|
| Designs/ | Operations/, Team-Workitems/ | Architecture is independent of HR ops |
| Operations/ | Designs/, Infrastructure/ | Recruitment is independent of design |
| Infrastructure/ | Operations/, Designs/ | IaC has distinct safety requirements |

### Cross-References
| Source | Target | Link Format |
|--------|--------|-------------|
| Operations/job-interviews/ | Operations/job-descriptions/ | `Job-ID: jd-*` |
| Team-Workitems/ | Designs/ | `Design-Ref: *` |

### Priority Levels
P0 (this week, max 3) / P1 (deadlines, max 5) / P2 (default) / P3 (nice-to-have)

### Verification Discipline
Identify what "done" means → run verification → confirm output → only then claim done.

### Skills & Workflows (load on demand)
| Trigger | Load |
|---------|------|
| "process backlog", task format, daily/weekly, maintenance | task-management skill |
| decomposing or delegating non-trivial work | orchestration-model skill |

<!-- END MANAGED BY AGENTIC-OS -->
```

### Emitted skill: .agents/skills/task-management/SKILL.md (procedures moved out of AGENTS.md)

```markdown
---
name: task-management
description: Task file format, priorities, backlog/daily/weekly/maintenance workflows. Load when creating or triaging tasks, processing the backlog, or doing workspace hygiene.
---

# Task & Workflow Management

## When to Use
Creating/triaging tasks, "process my backlog", daily guidance, weekly review, maintenance.

## When Not to Use
Simple one-off edits with no task tracking; pure code changes.

## Task File Format
1. YAML frontmatter: title, category, priority (P0-P3), status, created, due, resource_refs, goal_ref
2. Body + Acceptance Criteria checklist.

## Backlog Processing
1. Read BACKLOG.md → 2. classify domain → 3. dedup check → 4. clarify → 5. create task files → 6. summarize.

## Maintenance
- Prune done tasks >30 days. Warn if >3 P0 or >5 P1. Review evals weekly.
```

A matching `agents/openai.yaml` (name, description, version: 1, invocation.trigger) is emitted alongside each skill so OpenAI-style runtimes can route to it.

### File: CLAUDE-agentic-os.md (companion — existing CLAUDE.md untouched)

```markdown
# Agentic-OS Configuration

This file supplements the existing CLAUDE.md with agentic-os configuration.

## Persona Routing
- **Architect Mode** (editing `/Designs/`): structural scalability, requirements traceability.
- **Operations Mode** (editing `/Operations/`): process efficiency, documentation completeness.
- **Infrastructure Mode** (editing `/Infrastructure/`): reliability, security, operational readiness.

See AGENTS.md for scope boundaries and the Skills & Workflows index.

## Skills
Canonical skills live under `.agents/skills/*/SKILL.md`. To run one, read its SKILL.md and follow the instructions. Procedures (task-management, orchestration-model) load on demand — they are not duplicated here.
```

### File: .clinerules-agentic-os (companion — existing .clinerules untouched)

```markdown
# Agentic-OS Rules

## Scope Isolation
- When in /Designs/: do not suggest content from /Operations/ or /Infrastructure/.
- When in /Operations/: do not suggest content from /Designs/ or /Team-Workitems/.
- When in /Infrastructure/: do not suggest content from /Operations/ or /Designs/.

## Procedures
Task format, backlog, daily/weekly, and maintenance procedures are defined in the
task-management skill (`.agents/skills/task-management/SKILL.md`). Load it when doing that
work rather than duplicating the steps here.
```

### File: .cursor/rules/806-agentic-os-personas.mdc

```yaml
---
description: Persona routing for agentic-os domains — Designs
globs: Designs/**/*
alwaysApply: true
---
# Architect Mode

When working in Designs/:
- Prioritize structural scalability and system design metrics
- Reference AGENTS.md for architecture persona guidelines and the Skills & Workflows index
- Cross-reference parent blueprints for requirements traceability
- Do not suggest patterns from Operations/ or Infrastructure/
```

### File: .cursor/rules/807-agentic-os-isolation.mdc

```yaml
---
description: Scope isolation between concern domains
globs: Operations/**/*,Designs/**/*,Team-Workitems/**/*,Infrastructure/**/*
alwaysApply: true
---
# Cross-Domain Isolation

When working in Operations/:
- Do not read or suggest content from Designs/ or Infrastructure/

When working in Designs/:
- Do not read or suggest content from Operations/ or Team-Workitems/

When working in Infrastructure/:
- Do not read or suggest content from Operations/ or Designs/
```

## Volume Calibration

Complex tier output should be:
- **Lean AGENTS.md** — always-on rules + Skills & Workflows index ONLY, within the context
  budget (≤ ~10,000 chars; never above the runtime cap). State the char count in the proposal.
- **Emitted on-demand skills** for procedures (task-management; orchestration-model unless
  `_bmad/` is present). Each is a valid skill pack with frontmatter, When to Use / When Not
  to Use, and a numbered process — plus a matching `agents/openai.yaml`.
- Per-runtime config files for all targeted runtimes (claude, cursor, cline, antigravity),
  using companion files where a config already exists.
- Cursor rules in separate files by concern (personas, isolation) to avoid glob conflicts.
- Every emitted skill file listed in the manifest and (unless `--track`) the gitignore
  managed block, so privacy and `--remove` cover them too.
