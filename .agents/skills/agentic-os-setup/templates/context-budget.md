# Template: Context Budget

## Intent

Keep generated agent-instruction files lean so they cost the fewest tokens per turn while
still encoding every rule the AI needs. Always-on files (AGENTS.md, CLAUDE.md, .clinerules,
the AGENTS.md managed block) are injected into the model's context on **every turn** — so
durable RULES stay inline, and step-by-step PROCEDURES move into on-demand skills that load
only when invoked. This is the framework's progressive-disclosure principle applied to the
files the installer itself generates.

## Inputs Required

- `{always_on_rules}`: the rules that must govern every turn (scope isolation, naming,
  verification, interaction style, priority levels, the Skills & Workflows index)
- `{procedures}`: the step-by-step workflows that only matter when invoked (task format,
  backlog/daily/weekly/maintenance, session evals, delegation patterns, helpful prompts)
- `{mandates}`: any load-bearing behavioral mandate (e.g. an orchestration/sub-agent model)
- `{context_cap}`: the target runtime's context-file size limit (commonly ~20,000 chars)

## Keep Inline vs Emit as Skill

| Content | Where it goes | Why |
|---------|---------------|-----|
| File-handling rules, scope isolation, cross-references, naming standards | INLINE (always-on) | Must apply on every edit, regardless of task |
| Verification discipline, interaction & writing style | INLINE (always-on) | Govern how the AI behaves on every turn |
| Priority Levels reference (P0/P1/P2/P3) | INLINE (always-on) | Short; needed whenever priorities are read |
| Skills & Workflows reference table (trigger → skill) | INLINE (always-on) | The index that makes progressive disclosure work |
| Mandate SUMMARY (2-3 lines) | INLINE (always-on) | Rule must still apply when the detail skill isn't loaded |
| Task File Format + full YAML template | EMIT as `task-management` skill | Only needed when creating tasks |
| Backlog / Daily / Weekly / Maintenance workflows | EMIT as `task-management` skill | Procedures, invoked occasionally |
| Session Evals, Helpful Prompts | EMIT as `task-management` skill | Reference material, not per-turn rules |
| Subagent delegation patterns + worked examples | EMIT as `orchestration-model` skill | Bulky; load only when delegating |

## Output Pattern (lean AGENTS.md skeleton)

```markdown
# AGENTS.md

Always-on rules below. Procedures live in on-demand skills (see Skills & Workflows).

## Workspace Layout
{compact bullet list, two levels deep for major dirs only}

## How to Work With Files
{read/write/list/search rules}

## Scope Isolation & Cross-References
{repo-specific boundaries and linkage rules}

## Naming Standards
{repo-specific patterns}

## Priority Levels
P0 (this week, max 3) / P1 (deadlines, max 5) / P2 (default) / P3 (nice-to-have)

## Mandate
{2-3 line summary of any orchestration/delegation model; full detail in the skill}

## Verification Discipline / Interaction & Writing Style
{always-on behavioral rules}

## Skills & Workflows
| Trigger phrase | Load |
|----------------|------|
| "process backlog", "daily prep", task work | task-management skill |
| delegating / decomposing non-trivial work | orchestration-model skill |
| ... | ... |
```

## Budget Rules

1. **Target** generated AGENTS.md at ≤ ~10,000 chars (≈ 2,500 tokens).
2. **Never exceed** `{context_cap}` — content past the cap is head/tail-truncated and the
   middle is silently dropped, so a fat file loses rules without warning.
3. **If over target:** relocate the lowest-priority sections to on-demand skills and leave
   a one-line pointer in the Skills & Workflows table. Relocate, never delete.
4. **Keep mandates inline as summaries** — moving a mandate entirely into a skill means it
   stops applying on turns when the skill isn't loaded.
5. **State the resulting char count** in the proposal so the user can confirm it fit.

## When to Use

- **Complexity tier:** Multi or Complex (Simple repos rarely approach the budget)
- **Always** when a framework is present (`_bmad/`) — these repos accumulate the most rules
  and overflow fastest, so procedures MUST be split into skills
- **Detected signals:** an existing AGENTS.md already near or over the context cap, many
  concern domains, or a delegation/orchestration mandate that would otherwise be inlined
