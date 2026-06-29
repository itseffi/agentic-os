---
name: prd-writing
description: Write a structured PRD for high-risk, cross-team, or multi-sprint initiatives before implementation.
---

# PRD Writing

Create clear, implementation-ready product requirements documents for initiatives that need alignment before coding.

## The Process

### Step 1: Confirm PRD is needed

Use PRD only if at least one is true:
- cross-team dependency
- multi-sprint scope
- high-risk decision or expensive tradeoff
- stakeholder alignment needed before build

If none apply, recommend execution-first flow (`writing-plans` -> `tdd` -> `verification`) instead.

### Step 2: Gather required inputs

Collect:
- product goal and target user
- business context and constraints
- known assumptions and risks
- success criteria and timeline

State explicit assumptions when inputs are missing.

### Step 3: Produce PRD in required format

Use this exact structure:

```markdown
# [Product Name]

## About
[High-level overview of the product and goal.]

## Market Insights
[Market context, competitors, trends, and target users.]

## Problem
[Core user problem, pain points, and why existing solutions are insufficient.]

## Solution
[Proposed AI product solution and how it addresses the problem.]

## Feature Prioritization

| Feature | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|---------|-------|--------|------------|--------|------------|----------|
|         |       |        |            |        |            |          |
|         |       |        |            |        |            |          |
|         |       |        |            |        |            |          |

## Requirements

**Functional Requirements:**
- FR1:
- FR2:
- FR3:

**AI/ML Model Requirements:**
- MR1:
- MR2:
- MR3:

**Non-Functional Requirements:**
- NFR1:
- NFR2:
- NFR3:

## Challenges
[Key product, technical, data, and go-to-market challenges.]

## Positioning

| Use Case | Target User | Key Benefit | Differentiator |
|----------|-------------|-------------|----------------|
|          |             |             |                |
|          |             |             |                |
|          |             |             |                |

## Metrics
[Success metrics and north star metric.]

## Rollout Plan

- **Stakeholders & Communication**
  - [Stakeholder groups and communication plan]

- **Roll-out Strategy**
  - [Launch phases, gating criteria, and post-GA plan]
```

### Step 4: Quality checks before finalizing

Ensure:
- no placeholder fields remain
- RICE rows are populated and prioritized
- metrics include baseline, target, and timeframe
- rollout includes phases and gating criteria
- top risks are explicit

## Output

- Final PRD in the required structure
- A short assumptions list
- Open questions/blockers list

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
