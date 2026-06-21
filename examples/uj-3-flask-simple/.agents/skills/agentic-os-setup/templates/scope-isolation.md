# Template: Scope Isolation

## Intent

Prevent AI from cross-contaminating context between unrelated concern domains. When working in one domain, the AI should not suggest content from or reference patterns in other domains unless explicitly asked.

## Inputs Required

- `{domains}`: List of domain paths that should be isolated from each other
- `{isolation_pairs}`: Specific pairs of domains that must not cross-reference

## Output Pattern (Cursor .mdc)

```yaml
---
description: Scope isolation between concern domains
globs: {domain_path_1}/**/*,{domain_path_2}/**/*
alwaysApply: true
---
# Cross-Domain Isolation

When working in `{domain_path_1}/`:
- Do not read or suggest content from {other_domains}
- Do not apply patterns from {other_domains} to this domain
- Keep completions scoped to this domain's conventions

When working in `{domain_path_2}/`:
- Do not read or suggest content from {other_domains}
- Do not apply patterns from {other_domains} to this domain
- Keep completions scoped to this domain's conventions
```

## Output Pattern (CLAUDE.md section)

```markdown
## Scope Isolation

The following domains are isolated — do not cross-reference unless explicitly asked:

{for each isolation_pair}
- `/{domain_a}/` and `/{domain_b}/` are independent concerns
{end for}

When editing in one domain, restrict suggestions and completions to that domain's patterns and conventions.
```

## Output Pattern (AGENTS.md section)

```markdown
## Scope Boundaries

{for each domain}
### {domain_name}
**Path:** `/{domain_path}/`
**Isolated from:** {list_of_other_domains}
**Rationale:** {why_these_are_separate_concerns}
{end for}
```

## When to Use

- **Complexity tier:** Multi or Complex
- **Detected signals:** 2+ concern domains that serve different purposes (e.g., infrastructure vs application code, documentation vs implementation)
- **Always pair with:** Persona Routing (if personas are generated, isolation prevents persona bleed)
