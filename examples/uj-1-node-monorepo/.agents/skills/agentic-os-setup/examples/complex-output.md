# Calibration Example: Complex Tier Output

## Scenario

A multi-concern monorepo with `Designs/`, `Operations/`, `Team-Workitems/`, `Infrastructure/`, and `docs/` at root. Existing `.cursor/rules/` (files 800-805), existing AGENTS.md. Two team indicators. Cross-references between Operations and Designs.

**Detected signals:** .cursor/rules/ (6 files, 800-band), AGENTS.md, 5 concern folders, team indicators, cross-domain references
**Classification:** Complex (5+ concern folders, 4+ AI configs, 2 teams, 2+ cross-refs)
**Runtimes targeted:** claude, cursor, antigravity

## Expected Output

### File: CLAUDE-agentic-os.md (companion — existing CLAUDE.md untouched)

```markdown
# Agentic-OS Configuration

## Persona Routing

- **Architect Mode:** Triggered when editing `/Designs/`. Prioritize structural scalability, system design patterns, and requirements traceability.
- **Operations Mode:** Triggered when editing `/Operations/`. Focus on process efficiency, candidate assessment, and documentation completeness.
- **Engineering Mode:** Triggered when editing `/Infrastructure/`. Focus on reliability, security, and operational readiness.

See AGENTS.md for full persona definitions.

## Scope Isolation

The following domains are isolated — do not cross-reference unless explicitly asked:
- `/Designs/` and `/Operations/` are independent concerns
- `/Infrastructure/` and `/Team-Workitems/` are independent concerns

## Cross-Reference Rules

- **Operations/ → Designs/**: Interview files must reference a valid job description via `Job-ID:` frontmatter field
- **Team-Workitems/ → Designs/**: Work items should trace to design documents via `Design-Ref:` field

## Naming Conventions

### Operations/job-interviews/
- Candidate files: `candidate_[first-name]-[last-name].md`

### Team-Workitems/
- Work items: `[priority]-[short-description].md`

## Quality Gates

Before completing work, verify:
- **Linting**: `make lint`
- **Tests**: `make test`
- **Cross-references**: Verify linked documents exist
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
- Reference AGENTS.md for architecture persona guidelines
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
- Keep completions scoped to HR/recruitment conventions

When working in Designs/:
- Do not read or suggest content from Operations/ or Team-Workitems/
- Keep completions scoped to architecture patterns

When working in Infrastructure/:
- Do not read or suggest content from Operations/ or Designs/
- Keep completions scoped to IaC and deployment patterns
```

### File: AGENTS.md (extended via managed block — existing content preserved above)

```markdown
<!-- MANAGED BY AGENTIC-OS | hash:sha256:e3b0c44298fc1c149afbf4c8996fb924 | DO NOT EDIT -->
## Agentic-OS Generated Rules

### Personas

#### Architect
**Scope:** `/Designs/`
**Focus:** System design, scalability, requirements traceability
**Behavioral rules:**
- Prioritize structural patterns over quick fixes
- Reference existing blueprints before proposing new structures
- Validate against design principles in docs/

#### Operations Specialist
**Scope:** `/Operations/`
**Focus:** Process efficiency, documentation completeness, candidate assessment
**Behavioral rules:**
- Follow HR documentation standards
- Enforce cross-reference rules (interviews → job descriptions)
- Maintain naming conventions strictly

#### Infrastructure Engineer
**Scope:** `/Infrastructure/`
**Focus:** Reliability, security, operational readiness
**Behavioral rules:**
- Validate against security baselines
- Consider blast radius of changes
- Reference runbooks for operational procedures

### Scope Boundaries

| Domain | Isolated From | Rationale |
|--------|--------------|-----------|
| Designs/ | Operations/, Team-Workitems/ | Architecture concerns are independent of HR operations |
| Operations/ | Designs/, Infrastructure/ | Recruitment is independent of system design |
| Infrastructure/ | Operations/, Designs/ | IaC has distinct safety requirements |

### Cross-References

| Source | Target | Link Format | Rule |
|--------|--------|-------------|------|
| Operations/job-interviews/ | Operations/job-descriptions/ | `Job-ID: jd-*` | Every interview file must link to a valid JD |
| Team-Workitems/ | Designs/ | `Design-Ref: *` | Work items should trace to design docs |

<!-- END MANAGED BY AGENTIC-OS -->
```

## Volume Calibration

Complex tier output should be:
- Multiple config files per runtime (personas, isolation, cross-refs may be separate)
- AGENTS.md with full persona definitions and relationship tables
- 50-150 lines per major file
- Comprehensive organizational rules covering personas, isolation, cross-references, and naming
- Cursor rules in separate files by concern (personas, isolation) to avoid glob conflicts
