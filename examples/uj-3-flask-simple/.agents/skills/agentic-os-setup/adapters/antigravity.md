# Adapter: Antigravity

## Purpose

Describes how to format agentic-os generated output for Antigravity AI consumption via AGENTS.md.

## File Path Convention

- **Primary:** `AGENTS.md` at repo root
- **Behavior:** Always EXTEND existing content — never replace

## Format Specification

Antigravity reads AGENTS.md as its primary instruction file. It expects structured markdown with:

- `##` headers for major sections (Personas, Rules, Standards)
- `###` headers for subsections (individual personas, rule groups)
- Tables for structured data (scope boundaries, relationships)
- Bullet lists for behavioral rules
- Imperative tone ("Focus on X", "Validate Y", "Never Z")

## Constraints

- Single file (AGENTS.md)
- Must coexist with user-written content
- Agentic-os content lives ONLY within managed block markers
- User content above the managed block is never touched
- If no AGENTS.md exists, create one entirely within managed markers

## Managed Block Format

```markdown
<!-- MANAGED BY AGENTIC-OS | hash:sha256:<content-hash> | DO NOT EDIT -->
{generated content goes here}
<!-- END MANAGED BY AGENTIC-OS -->
```

- **Start marker:** `<!-- MANAGED BY AGENTIC-OS | hash:sha256:<hash> | DO NOT EDIT -->`
- **End marker:** `<!-- END MANAGED BY AGENTIC-OS -->`
- **Hash:** SHA-256 of the content between markers (enables future re-run detection)
- **Placement:** Always at the END of AGENTS.md (below any user content)

## Pre-Existing File Behavior

| Scenario | Action |
|----------|--------|
| No AGENTS.md exists | Create AGENTS.md with content entirely within managed block |
| AGENTS.md exists without managed block | Append managed block at end of file |
| AGENTS.md exists with managed block | Replace managed block content (preserve everything outside) |
| User edited content inside managed block | Detect hash mismatch → warn user and skip overwrite |

## Extend Semantics

```
AGENTS.md structure:
┌─────────────────────────────────────────────────────────────────┐
│ [User's original content]                                        │ ← never touched
│ ...                                                              │
├─────────────────────────────────────────────────────────────────┤
│ <!-- MANAGED BY AGENTIC-OS | hash:sha256:<hash> | DO NOT EDIT -->│
│ ## Agentic-OS Generated Rules                                    │
│ {all generated content here}                                     │
│ <!-- END MANAGED BY AGENTIC-OS -->                               │
└─────────────────────────────────────────────────────────────────┘
```

## Examples

### Example 1: New AGENTS.md (no existing file)

```markdown
<!-- MANAGED BY AGENTIC-OS | hash:sha256:a1b2c3d4e5f6 | DO NOT EDIT -->
## Agentic-OS Generated Rules

### Project Context

This is a Go microservices project with 3 services.

### Quality Gates

- Run `go test ./...` before completing work
- Run `golangci-lint run` for code quality
- Ensure new packages have corresponding test files

<!-- END MANAGED BY AGENTIC-OS -->
```

### Example 2: Extending existing AGENTS.md (Complex tier)

User's existing content (preserved as-is):
```markdown
# Team Agents

## Product Manager
Responsible for roadmap decisions...

## Tech Lead
Responsible for architecture decisions...
```

After agentic-os extension:
```markdown
# Team Agents

## Product Manager
Responsible for roadmap decisions...

## Tech Lead
Responsible for architecture decisions...

<!-- MANAGED BY AGENTIC-OS | hash:sha256:f7e8d9c0b1a2 | DO NOT EDIT -->
## Agentic-OS Generated Rules

### Personas

#### Architect
**Scope:** `/Designs/`
**Focus:** System design, scalability, requirements traceability
**Behavioral rules:**
- Prioritize structural patterns over quick fixes
- Reference existing blueprints before proposing new structures

#### Operations Specialist
**Scope:** `/Operations/`
**Focus:** Process efficiency, documentation completeness
**Behavioral rules:**
- Follow documentation standards
- Enforce cross-reference rules

### Scope Boundaries

| Domain | Isolated From | Rationale |
|--------|--------------|-----------|
| Designs/ | Operations/ | Architecture and HR are independent |
| Operations/ | Designs/ | Recruitment is independent of design |

### Cross-References

| Source | Target | Link Format |
|--------|--------|-------------|
| Operations/interviews/ | Operations/job-descriptions/ | `Job-ID: jd-*` |

<!-- END MANAGED BY AGENTIC-OS -->
```

## Usage Context

The AI reads this adapter when the user has targeted Antigravity as a runtime. It formats the assembled proposal (from templates) into AGENTS.md content within managed block markers, preserving any existing user content above the block.
