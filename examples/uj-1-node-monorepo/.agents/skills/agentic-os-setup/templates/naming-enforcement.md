# Template: Naming Enforcement

## Intent

Enforce consistent file and directory naming conventions within a domain. Catches deviations from established patterns and guides creation of new files.

## Inputs Required

- `{domain}`: Domain path where naming rules apply
- `{patterns}`: List of naming patterns with their regex or description
- `{examples}`: Valid and invalid filename examples

## Output Pattern (Cursor .mdc)

```yaml
---
description: Naming conventions for {domain}
globs: {domain}/**/*
alwaysApply: true
---
# Naming Conventions

Files in `{domain}/` follow these patterns:

{for each pattern}
- **{file_type}**: `{naming_pattern}`
  Example: `{valid_example}`
{end for}

When creating new files in this domain:
- Follow the naming pattern exactly
- Warn if a proposed filename doesn't match the convention
```

## Output Pattern (CLAUDE.md section)

```markdown
## Naming Conventions

{for each domain_with_patterns}
### {domain}/
{for each pattern}
- `{file_type}` files: `{naming_pattern}` (e.g., `{valid_example}`)
{end for}
{end for}
```

## Output Pattern (AGENTS.md section)

```markdown
## Naming Standards

{for each domain_with_patterns}
### {domain}
| File Type | Pattern | Example |
|-----------|---------|---------|
{for each pattern}
| {file_type} | `{naming_pattern}` | `{valid_example}` |
{end for}
{end for}
```

## When to Use

- **Complexity tier:** Simple, Multi, or Complex (applicable at any tier where patterns are detected)
- **Detected signals:** Consistent naming patterns observed in existing files (3+ files following same convention)
- **Common patterns:** kebab-case files, prefixed files (NNN-name.ext), date-prefixed (YYYY-MM-DD-name), type-prefixed (feat-*, fix-*)
