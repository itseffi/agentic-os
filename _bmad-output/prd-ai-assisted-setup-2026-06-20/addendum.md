# Addendum — AI-Assisted Complex Repo Auto-Setup

## Rule Template Examples (for Architecture Phase)

These are the types of rules the AI-installer generates, with example output per runtime.

### Persona Routing by Folder

**Intent:** When editing in /Designs, adopt Architect persona. When in /Operations, adopt Talent Acquisition persona.

**Cursor (.mdc):**
```yaml
---
description: Persona routing for agentic-os domains
globs: Designs/**/*
alwaysApply: true
---
# Architect Mode
- Prioritize structural scalability and system design metrics
- Reference AGENTS.md for architecture persona guidelines
- Cross-reference parent blueprints for requirements traceability
```

**Claude (CLAUDE.md section):**
```markdown
## Persona Routing
- **Architect Mode:** Triggered when editing `/Designs/`. Prioritize structural scalability.
- **Talent Acquisition Mode:** Triggered when processing `/Operations/`. Focus on assessment rubrics.
```

### Scope Isolation

**Intent:** Do not suggest completions from /Operations while working in /Designs.

**Cursor (.mdc):**
```yaml
---
description: Scope isolation between concern domains
globs: Operations/**/*,Designs/**/*,Team-Workitems/**/*
alwaysApply: true
---
# Cross-Domain Isolation
- Do not read or suggest content from /Operations/ while user is in /Designs/ or /Team-Workitems/
- Do not read or suggest content from /Designs/ while user is in /Operations/
```

### Cross-Reference Enforcement

**Intent:** Interview notes must link to job descriptions.

**Cursor (.mdc rule within the Operations glob):**
```markdown
- Every file in job-interviews/ MUST contain frontmatter linking to a valid file in job-descriptions/ (e.g., `Job-ID: jd-senior-frontend-01`)
```

### Naming Pattern Enforcement

**Intent:** Candidate files follow exact format.

```markdown
- Files in job-interviews/ follow format: `candidate_[first-name]-[last-name].md`
```

---

## Complexity Tier Scoring Algorithm

### Scoring Model

The AI uses a **highest-dimension-wins** algorithm: each dimension independently suggests a tier, and the overall classification is the HIGHEST tier suggested by any single dimension. This prevents under-classifying repos that are complex in one dimension but simple in others.

### Dimension Scoring Table

| Dimension | Zero | Simple | Multi | Complex |
|-----------|------|--------|-------|---------|
| Top-level concern folders | 0 | 1-2 | 3-4 | 5+ |
| Existing AI config files | 0 | 0-1 | 2-3 | 4+ |
| Team/group indicators | 0 | 0 | 1 | 2+ |
| Cross-domain references detected | 0 | 0 | 1 | 2+ |
| Agent framework present (_bmad/, etc.) | No | No | No | Yes |

### Algorithm

1. For each dimension, map the detected count to a tier (Zero=0, Simple=1, Multi=2, Complex=3)
2. Take the maximum score across all dimensions
3. If max score = 0 → Zero tier; 1 → Simple; 2 → Multi; 3 → Complex
4. Present the classification WITH the scoring breakdown so the user can challenge it

### Override Protocol

The AI always proposes its classification with rationale. The user can override up or down. The override is respected without argument. This prevents the "I know my repo better than you" frustration.

### Calibration Notes

- A repo with `_bmad/` is automatically Complex (framework presence is a strong signal)
- A repo with only `src/` and `tests/` should never exceed Simple regardless of file count
- The 15+ signals in catalog.md feed INTO these 5 dimensions (many signals map to "concern folders" count)

---

## Rejected Alternatives

### "Single SETUP.md as universal entry point" (Trigger #1)
**Rejected because:** Lower discoverability. Users don't know to say "read SETUP.md." The setup.sh bootstrap provides a concrete entry point everyone understands.

### "Purely static pattern scanner" (Detection #1)
**Rejected because:** Too brittle for novel repo structures. Can't reason about intent, only match known patterns. AI-assisted approach handles the long tail.

### "All-or-nothing runtime targeting"
**Rejected because:** Persona stress tests showed users often only use 1-2 runtimes. Generating configs for unused tools creates noise and confusion.

### "Config files committed by default"
**Rejected because:** Architect persona identified security concern — generated configs can expose internal team structure, tool usage, ADO project names. Gitignore by default; opt-in to track.

---

## Phase Roadmap (High-Level)

| Phase | Scope | Key Capability |
|-------|-------|---------------|
| 1 (MVP) | This PRD | First-run, dry-run, conflict detection, uninstall |
| 2 | Re-run & teams | Delta merging, managed blocks, team isolation, BMAD deep integration |
| 3 | Integrations | MCP detection, relationship graph visualization, ADO/Jira awareness |
| 4 | Dynamic config | Ephemeral context generation, continuous adaptation, session-aware config |

---

## First Principles Insight (from brainstorming)

The platonic ideal: no setup exists. The AI reads signals at session start and computes context on-the-fly. Config is a projection, not a source. Phase 4 moves toward this — but Phases 1-3 build the infrastructure (signal catalog, relationship model, runtime adapters) that makes dynamic generation possible later. The static files generated in Phase 1 are stepping stones, not the destination.

---

## Reference Architecture Patterns (anonymized)

These patterns were observed in production repos and inform the signal catalog and rule templates:

1. **Multi-concern monorepo** — Designs/, Operations/, Team-Workitems/, Meetings/, Infrastructure/ at root level. Each folder is a concern domain with different AI persona needs.
2. **Layered AI config** — .cursor/rules/ with 0XX-9XX classification + .claude/skills/ + _bmad/ all coexisting. Each layer has different ownership semantics.
3. **Cross-domain linkage** — Job interviews reference job descriptions. Work items trace to design blueprints. Tasks shard from stories. These relationships are the high-value rules to generate.
4. **Team boundaries** — Subfolders like frontend-team/, backend-team/ within work-items indicate scope isolation needs.
