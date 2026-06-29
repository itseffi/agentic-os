# Skills (Canonical)

This directory is the canonical runtime skill location for Codex/OpenAI-style skills.

## Layout

- One folder per skill
- Each skill folder must contain `SKILL.md`
- Optional agent-specific metadata can live at `agents/openai.yaml`
- Recommended: include `## When to Use` and `## When Not to Use` sections

Example:

```
.agents/skills/verification/SKILL.md
.agents/skills/verification/agents/openai.yaml
.agents/skills/tdd/SKILL.md
.agents/skills/linear-issue-sync/SKILL.md
```

## Source of Truth

Runtime skill packs in `.agents/skills/` are the source of truth.

Edit skills directly in this directory, then validate:

```bash
python scripts/validate_skills.py
```

If using Claude-specific skill discovery, this repo bridges:

```bash
.claude/skills -> ../.agents/skills
```
