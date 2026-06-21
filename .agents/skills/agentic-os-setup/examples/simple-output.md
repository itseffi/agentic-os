# Calibration Example: Simple Tier Output

## Scenario

A single-purpose Node.js project with `src/`, `tests/`, `package.json`, and a `.github/workflows/` directory. No existing AI config. One developer.

**Detected signals:** package.json (jest, eslint), src/, .github/
**Classification:** Simple (1 concern folder, 0 AI configs, 0 teams, 0 cross-refs, no framework)
**Runtimes targeted:** claude, cursor

## Expected Output

### File: CLAUDE.md

```markdown
# Project Context

This is a Node.js project using Jest for testing and ESLint for linting.

## Quality Gates

Before completing work:
- Run tests: `npm test`
- Run linting: `npm run lint`
- Ensure new code has corresponding test coverage

## Project Structure

- `src/` — Application source code
- `tests/` — Test files (Jest)
- `.github/workflows/` — CI pipeline
```

### File: .cursor/rules/900-agentic-os.mdc

```yaml
---
description: Project context and quality gates for agentic-os
globs: src/**/*
alwaysApply: true
---
# Project Standards

This is a Node.js project. When working in src/:
- Run `npm test` before considering work complete
- Run `npm run lint` to verify code style
- New source files should have corresponding test files in tests/
- Follow existing naming conventions in src/
```

## What is NOT Generated (Simple Tier)

- No AGENTS.md (not enough complexity for personas)
- No GOALS.md (not a multi-concern workspace)
- No persona routing (single domain)
- No scope isolation (single domain)
- No cross-reference enforcement (no relationships detected)

## Volume Calibration

Simple tier output should be:
- 1 file per targeted runtime
- Under 30 lines per file
- Focused on project context and quality gates only
- No organizational/behavioral rules
