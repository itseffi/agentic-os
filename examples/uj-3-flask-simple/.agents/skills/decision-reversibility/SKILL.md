---
name: decision-reversibility
description: Classify decisions as Hat/Haircut/Tattoo by reversibility. Use to calibrate how much analysis a decision deserves.
---

# Decision Reversibility Classification

Classify decisions by reversibility to calibrate how much analysis they deserve.

## When to Use

Before making a decision, to determine how much deliberation is warranted.

## The Framework

Classify decisions into three categories:

| Type | Reversibility | Analysis Needed |
|------|---------------|-----------------|
| **Hat** | Easily reversible, minimal consequences | Decide quickly |
| **Haircut** | Reversible with effort/time | Moderate analysis |
| **Tattoo** | Largely irreversible, lasting impact | Deep analysis |

## Analysis Criteria

Consider these factors:

1. **Immediate consequences** - What happens right away?
2. **Long-term effects** - On you, team, users, company?
3. **Reversal effort** - Time, money, resources to undo?
4. **Permanent changes** - What can't be undone?

## Classification Guide

**Hat (decide fast):**
- Can undo with minimal cost
- No lasting consequences
- Examples: Meeting time, doc format, tool choice

**Haircut (moderate deliberation):**
- Reversible but requires time/effort
- Temporary discomfort if wrong
- Examples: Feature scope, team process, pricing test

**Tattoo (deliberate carefully):**
- Largely permanent or very costly to reverse
- Long-lasting consequences
- Examples: Architecture choices, team structure, market positioning

## Output

- Decision classification (Hat/Haircut/Tattoo)
- Key factors driving the classification
- Recommended level of analysis

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
