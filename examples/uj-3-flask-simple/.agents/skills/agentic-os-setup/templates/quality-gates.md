# Template: Quality Gates

## Intent

Define quality checks that the AI should enforce or remind about when creating or modifying files within a domain. Derived from detected tooling (linters, test frameworks, CI pipelines).

## Inputs Required

- `{domain}`: Domain path or glob where quality gates apply
- `{gates}`: List of quality checks with their commands or descriptions
- `{test_framework}`: Detected test framework (jest, pytest, cargo test, go test, etc.)
- `{lint_tools}`: Detected linting/formatting tools
- `{ci_checks}`: Known CI pipeline checks

## Output Pattern (Cursor .mdc)

```yaml
---
description: Quality gates for {domain}
globs: {domain}/**/*.{extensions}
alwaysApply: true
---
# Quality Gates

Before considering work in `{domain}/` complete:

{for each gate}
- [ ] {gate_description}: `{gate_command}`
{end for}

When creating new files:
- Ensure they have corresponding test files (if test framework detected)
- Follow existing patterns for test file location and naming
```

## Output Pattern (CLAUDE.md section)

```markdown
## Quality Gates

Before completing work, verify:

{for each gate}
- **{gate_name}**: `{gate_command}` — {gate_purpose}
{end for}

Test framework: {test_framework}
Test location: {test_directory_pattern}
```

## Output Pattern (AGENTS.md section)

```markdown
## Quality Standards

### Pre-Completion Checklist
{for each gate}
- [ ] **{gate_name}**: {gate_description}
  Command: `{gate_command}`
{end for}

### Testing Requirements
- Framework: {test_framework}
- Location: `{test_directory_pattern}`
- Coverage: {coverage_expectations}
```

## When to Use

- **Complexity tier:** Simple, Multi, or Complex
- **Detected signals:** Test framework present (package.json scripts, pytest.ini, Cargo.toml test config), linting tools configured (.eslintrc, ruff.toml, .golangci.yml), CI workflows present (.github/workflows/)
- **Scales with tier:** Simple = test + lint only; Multi/Complex = full gate set including build verification
