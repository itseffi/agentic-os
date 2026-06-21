# Adapter: Cursor

## Purpose

Describes how to format agentic-os generated output for Cursor AI consumption via `.cursor/rules/` files.

## File Path Convention

- **Directory:** `.cursor/rules/`
- **Filename:** `NNN-agentic-os.mdc` or `NNN-agentic-os-{concern}.mdc`
- **Numbering:** Use the next available number in the appropriate band. Default to 900-band if no convention exists. If existing rules use a different band, append after the highest existing number.

### Numbering Detection

1. List all existing `.mdc` files in `.cursor/rules/`
2. Extract the numeric prefix from each filename
3. Identify the convention (e.g., 0XX=core, 1XX=tools, 8XX=workflow)
4. Place agentic-os rules in the highest available band (typically 900+)
5. Never renumber or move existing files

## Format Specification

Each `.mdc` file requires YAML frontmatter:

```yaml
---
description: Human-readable description of this rule's purpose
globs: path/to/files/**/*.ext
alwaysApply: true
---
```

**Required fields:**
- `description` — Clear, concise explanation (shown in Cursor's rule list)
- `globs` — File patterns this rule applies to

**Optional fields:**
- `alwaysApply` — Set to `true` when the rule should always be active for matched files

**Body:** Markdown content after frontmatter contains the actual rules.

## Constraints

- Each file targets specific globs — rules are file-scoped, not global
- Globs must be specific: NEVER use `*` alone (too broad)
- One concern per file is preferred (persona routing separate from scope isolation)
- Keep individual files focused (under 50 lines of rule content)
- YAML frontmatter is mandatory

## Glob Specificity Rules

| Pattern | Acceptable? | Why |
|---------|:-----------:|-----|
| `src/**/*` | Yes | Targets specific directory |
| `**/*.ts` | Yes | Targets specific file type |
| `src/**/*.tsx` | Yes | Combines directory + type |
| `*` | No | Too broad — would match everything |
| `**/*` | No | Equivalent to matching all files |

## Pre-Existing File Behavior

| Scenario | Action |
|----------|--------|
| No `.cursor/rules/` directory | Create directory and add rule files starting at 900 |
| Directory exists with rules | Scan for glob collisions, use next available number |
| Glob collision detected | Report conflict, propose narrower glob or skip |

Never modify or renumber existing `.mdc` files.

## Collision Detection Protocol

Before writing ANY .mdc file:
1. Read all existing `.mdc` files in `.cursor/rules/`
2. Extract each file's `globs` value from frontmatter
3. Compare proposed globs against existing globs
4. If overlap exists: report which file conflicts, what its glob is, and why they conflict
5. Propose alternatives: narrower glob, different file scope, or skip

## Examples

### Example 1: Simple project context

```yaml
---
description: Project context and quality gates for agentic-os
globs: src/**/*
alwaysApply: true
---
# Project Standards

This is a TypeScript project using Vitest for testing.

When working in src/:
- Run `npm test` before considering work complete
- Run `npm run lint` to verify code style
- New files should have corresponding .test.ts files
```

### Example 2: Persona routing (Complex tier)

```yaml
---
description: Persona routing — Architecture domain
globs: Designs/**/*
alwaysApply: true
---
# Architect Mode

When working in Designs/:
- Prioritize structural scalability and system design patterns
- Reference AGENTS.md for full persona guidelines
- Cross-reference existing blueprints before proposing new designs
- Do not apply patterns from Operations/ or Infrastructure/
```

### Example 3: Scope isolation (Complex tier)

```yaml
---
description: Scope isolation between concern domains
globs: Operations/**/*,Designs/**/*,Infrastructure/**/*
alwaysApply: true
---
# Cross-Domain Isolation

When working in Operations/:
- Do not suggest content from Designs/ or Infrastructure/

When working in Designs/:
- Do not suggest content from Operations/ or Infrastructure/

When working in Infrastructure/:
- Do not suggest content from Operations/ or Designs/
```

## Usage Context

The AI reads this adapter when the user has targeted Cursor as a runtime. It formats the assembled proposal (from templates) into Cursor-native `.mdc` files, respecting numbering conventions, glob specificity, and collision detection requirements.
