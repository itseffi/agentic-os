# Template: Persona Routing

## Intent

Route AI persona/behavior based on which folder the user is editing in. Each concern domain gets a distinct behavioral mode optimized for that domain's work.

## Inputs Required

- `{domains}`: List of detected concern domains with their folder paths
- `{personas}`: Mapping of domain → persona name and behavioral description
- `{repo_name}`: Repository name for context

## Output Pattern (Cursor .mdc)

```yaml
---
description: Persona routing for agentic-os domains — {domain_name}
globs: {domain_path}/**/*
alwaysApply: true
---
# {persona_name} Mode

When working in `{domain_path}/`:
- {persona_behavioral_rule_1}
- {persona_behavioral_rule_2}
- {persona_behavioral_rule_3}

Reference AGENTS.md for full persona guidelines.
```

One .mdc file per domain. Each gets a specific glob.

## Output Pattern (CLAUDE.md section)

```markdown
## Persona Routing

{for each domain}
- **{persona_name} Mode:** Triggered when editing `/{domain_path}/`. {persona_behavioral_summary}
{end for}

See AGENTS.md for full persona definitions.
```

## Output Pattern (AGENTS.md section)

```markdown
## Personas

{for each domain}
### {persona_name}

**Scope:** `/{domain_path}/`
**Focus:** {persona_focus_description}
**Behavioral rules:**
- {rule_1}
- {rule_2}
- {rule_3}
{end for}
```

## When to Use

- **Complexity tier:** Multi or Complex
- **Detected signals:** 2+ distinct concern domains with different intent (e.g., `Designs/` + `Operations/` or `frontend/` + `backend/` + `infra/`)
- **NOT when:** Single-purpose repo, or `_bmad/` detected (defer persona ownership to BMAD)
