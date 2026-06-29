---
name: spec-writing
description: Convert an approved PRD or clear requirements into an implementation-ready technical spec with scope, interfaces, and acceptance criteria.
---

# Spec Writing

Use this skill to produce an implementation-ready spec before planning or coding.

## The Process

### Step 1: Validate inputs

Require one of:
- approved PRD
- clear requirements with goals and constraints

If inputs are missing or ambiguous, list assumptions and open questions first.

### Step 2: Define scope boundaries

Document:
- in scope
- out of scope
- constraints (time, dependencies, compliance, platform)

### Step 3: Define solution design

Specify:
- architecture overview (high-level components)
- interfaces/contracts
- data model changes
- rollout and migration approach

### Step 4: Define acceptance and verification

Include:
- acceptance criteria (testable)
- non-functional expectations (performance, security, reliability)
- verification commands/checks required before completion

## Output Format

```markdown
# [Feature Name] Technical Spec

## Goal
[What this spec delivers and why]

## Scope
- In scope:
- Out of scope:
- Constraints:

## Design
- Architecture:
- Interfaces/contracts:
- Data model changes:
- Migration/rollout:

## Risks and Dependencies
- Risks:
- Dependencies:
- Mitigations:

## Acceptance Criteria
- AC1:
- AC2:
- AC3:

## Verification Plan
- Required checks:
- Commands:
- Evidence to capture:

## Open Questions
- Q1:
- Q2:
```

## Quality Bar

- No vague placeholders in final output
- Acceptance criteria must be measurable
- Verification plan must include explicit commands

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
