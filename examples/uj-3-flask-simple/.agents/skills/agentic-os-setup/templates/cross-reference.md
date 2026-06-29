# Template: Cross-Reference Enforcement

## Intent

Enforce that files in one domain correctly reference files in another domain where a declared relationship exists. Catches broken links, missing references, and orphaned documents.

## Inputs Required

- `{relationships}`: List of source → target relationships with their linking mechanism
- `{source_domain}`: Domain where the referencing file lives
- `{target_domain}`: Domain where the referenced file lives
- `{link_format}`: How the reference is expressed (frontmatter field, inline link, filename convention)

## Output Pattern (Cursor .mdc)

```yaml
---
description: Cross-reference enforcement — {source_domain} → {target_domain}
globs: {source_domain}/**/*
alwaysApply: true
---
# Cross-Reference Rules

Every file in `{source_domain}/` that matches `{file_pattern}` MUST:
- {reference_requirement_1}
- {reference_requirement_2}

Validation:
- Check that referenced {target_domain} file exists
- Warn if reference format doesn't match: `{link_format}`
```

## Output Pattern (CLAUDE.md section)

```markdown
## Cross-Reference Rules

{for each relationship}
- **{source_domain}/ → {target_domain}/**: Files matching `{file_pattern}` must contain a reference to a valid `{target_domain}` file using format: `{link_format}`
{end for}
```

## Output Pattern (AGENTS.md section)

```markdown
## Relationship Enforcement

{for each relationship}
### {relationship_name}
**Source:** `/{source_domain}/{file_pattern}`
**Target:** `/{target_domain}/`
**Link format:** `{link_format}`
**Rule:** {enforcement_description}
{end for}
```

## When to Use

- **Complexity tier:** Multi or Complex
- **Detected signals:** Cross-domain references found (e.g., interview files referencing job descriptions, work items referencing design docs, tests referencing source modules)
- **Requires:** User confirmation for AI-inferred relationships (only manifest-declared relationships are auto-included)
