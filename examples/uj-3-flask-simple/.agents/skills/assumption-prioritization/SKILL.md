---
name: assumption-prioritization
description: Prioritize assumptions by risk and importance. Use after assumption mapping to decide what to test first.
---

# Assumption Prioritization

Prioritize assumptions to focus validation efforts on what matters most.

## When to Use

After assumption mapping, to decide which assumptions to test first.

## The Framework

Score each assumption on two dimensions:

**Importance (1-5):** Business impact if false
- 5 = Strategy fails, >20% revenue hit
- 4 = Major adoption/cost driver (10-20%)
- 3 = Moderate impact (5-10%)
- 2 = Minor impact (<5%)
- 1 = Negligible

**Certainty (1-5):** Evidence that it's true
- 1 = No evidence, conjecture
- 2 = Anecdotes, untested
- 3 = Early signals, small samples
- 4 = Strong directional data
- 5 = Robust evidence, production proof

**Risk Score = Importance x (6 - Certainty)**

Higher score = riskier assumption = test first

## The Process

### 1. Score Each Assumption

Consider:
- Impact severity from "impact if wrong"
- Blast radius (users/systems affected)
- Irreversibility (cost to fix later)
- Dependencies (does it block others?)
- Evidence quality

### 2. Map to Quadrants

| | Low Certainty | High Certainty |
|---|---|---|
| **High Importance** | TEST FIRST | Monitor |
| **Low Importance** | Deprioritize | Ignore |

### 3. Rank by Risk Score

Focus validation on High Importance / Low Certainty assumptions.

## Output

- 2x2 summary with counts per quadrant
- Top risks ranked by score with rationale
- Full ranked list of all assumptions

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
