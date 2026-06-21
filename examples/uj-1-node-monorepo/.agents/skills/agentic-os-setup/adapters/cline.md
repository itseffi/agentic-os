# Adapter: Cline

## Purpose

Describes how to format agentic-os generated output for Cline AI consumption.

## File Path Convention

- **Primary:** `.clinerules` at repo root
- **If `.clinerules` already exists:** Create `.clinerules-agentic-os` as a companion file. Never modify the existing `.clinerules`.

## Format Specification

Cline reads `.clinerules` as a plain text/markdown file containing behavioral instructions. Effective patterns:

- Use `##` headers to organize sections
- Direct imperative rules ("Always X", "Never Y", "When doing Z, ensure W")
- Bullet lists for grouped rules
- Keep language concise and actionable

## Constraints

- Single file (no directory-based rule system like Cursor)
- No frontmatter or metadata
- No glob-based routing — all rules apply globally
- Rules must be self-describing (include path context inline where needed)
- Simpler format than Claude or Cursor — focus on behavioral directives

## Pre-Existing File Behavior

| Scenario | Action |
|----------|--------|
| No `.clinerules` exists | Create `.clinerules` |
| `.clinerules` exists | Create `.clinerules-agentic-os` as companion. Never modify existing file. |

## Examples

### Example 1: Simple Tier

```markdown
# Project Rules

## Quality Gates

- Always run `npm test` before completing work
- Always run `npm run lint` before completing work
- New source files must have corresponding test files

## Project Structure

- Source code lives in `src/`
- Tests live in `tests/`
- Follow existing naming conventions
```

### Example 2: Multi Tier

```markdown
# Agentic-OS Rules

## Persona Routing

When working in `/backend/`:
- Focus on API design, data modeling, and performance
- Follow Python conventions (PEP 8, type hints)

When working in `/frontend/`:
- Focus on component architecture and accessibility
- Follow React/TypeScript conventions

## Scope Isolation

- Do not suggest content from `/backend/` when working in `/frontend/`
- Do not suggest content from `/frontend/` when working in `/backend/`
- Keep suggestions scoped to the current domain

## Quality Gates

- Backend: run `pytest` and `mypy` before completing work
- Frontend: run `npm test` and `npm run lint` before completing work
```

## Usage Context

The AI reads this adapter when the user has targeted Cline as a runtime. It formats the assembled proposal (from templates) into Cline-appropriate rules, respecting the single-file, directive-focused format.
