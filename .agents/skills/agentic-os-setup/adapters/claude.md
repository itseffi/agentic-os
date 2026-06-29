# Adapter: Claude Code

## Purpose

Describes how to format agentic-os generated output for Claude Code consumption.

## File Path Convention

- **Primary:** `CLAUDE.md` at repo root
- **If CLAUDE.md already exists:** Create `CLAUDE-agentic-os.md` as a companion file. Never modify the existing CLAUDE.md.

## Format Specification

Claude Code reads CLAUDE.md as a markdown file with freeform structure. Effective patterns:

- Use `##` headers to organize sections (Persona Routing, Scope Isolation, Quality Gates, etc.)
- Bullet lists for rules and constraints
- Code blocks for commands and patterns
- Keep instructions direct and imperative ("Do X", "Never Y")

## Constraints

- Single file (no directory structure like Cursor)
- No frontmatter or metadata — pure markdown
- No glob-based routing — all rules apply globally (Claude Code doesn't have file-scoped rules)
- Rules must be self-describing (include "when editing in X" context inline)

## Pre-Existing File Behavior

| Scenario | Action |
|----------|--------|
| No CLAUDE.md exists | Create `CLAUDE.md` |
| CLAUDE.md exists | Create `CLAUDE-agentic-os.md` as companion. Add a note at top: "This file supplements the existing CLAUDE.md with agentic-os configuration." |

Never modify an existing CLAUDE.md.

## Examples

### Example 1: Simple Tier (single-purpose project)

```markdown
# Project Context

This is a Python FastAPI project using pytest for testing.

## Quality Gates

Before completing work:
- Run tests: `pytest`
- Run type checking: `mypy src/`
- Run formatting: `ruff format --check .`

## Project Structure

- `src/` — Application source (FastAPI routes and models)
- `tests/` — Test files (pytest)
- `alembic/` — Database migrations
```

### Example 2: Multi Tier (multiple concerns)

```markdown
# Agentic-OS Configuration

## Persona Routing

- **Backend Mode:** Triggered when editing `/backend/`. Focus on API design, data modeling, and performance.
- **Frontend Mode:** Triggered when editing `/frontend/`. Focus on component architecture, accessibility, and UX.
- **DevOps Mode:** Triggered when editing `/infra/`. Focus on reliability, security, and cost optimization.

## Scope Isolation

Do not cross-reference between isolated domains unless explicitly asked:
- `/backend/` and `/frontend/` have distinct conventions
- `/infra/` is independent from application code

## Quality Gates

- Backend: `cd backend && pytest && mypy .`
- Frontend: `cd frontend && npm test && npm run lint`
- Infrastructure: `cd infra && terraform validate`
```

## Usage Context

The AI reads this adapter when the user has targeted Claude Code as a runtime. It formats the assembled proposal (from templates) into Claude-appropriate markdown, respecting the constraints above.
