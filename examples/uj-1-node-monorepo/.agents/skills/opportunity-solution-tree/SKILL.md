---
name: opportunity-solution-tree
description: Transform research into Opportunity Solution Tree (Teresa Torres method). Map outcomes, opportunities, solutions, and experiments.
---

# Opportunity Solution Tree (OST)

Transform interview data into a structured Opportunity Solution Tree following Teresa Torres's method.

## When to Use

When synthesizing user research into a structured view of opportunities.

## Key Concepts

**Opportunity:** A customer need, pain, or desire - phrased from user perspective, not a solution.

**Moment in time:** A distinct point in the customer journey.

**Tests:**
- **Distinctness (siblings):** Can we pursue one without addressing the other? If yes, they're distinct.
- **Parent-child:** Does solving the child partially solve the parent? If not, reframe.

## The Process

### 1. Extract Opportunities

From interviews, capture:
- Verbatim quotes
- Reframed user-need statement
- Which journey moment it belongs to

### 2. Organize by Journey Moments

Group opportunities under their primary moment in time.

### 3. Structure Within Each Moment

- Cluster similar opportunities
- Create parent nodes where needed
- Run distinctness checks across siblings
- Run parent-child checks down branches
- Remove generic parents with single children
- Combine near-duplicates

### 4. Track Evidence

For each opportunity, capture:
- Representative quotes
- Frequency count
- Confidence level (low/med/high)

### 5. Prioritize Leaves

Score leaf opportunities:
- Impact (1-5)
- Frequency (1-5)
- Alignment to outcome (1-5)
- Priority = Impact x Frequency x Alignment

## Output Format

**Opportunity Inventory Table:**
| ID | Moment | Opportunity | Parent ID | Quotes | Frequency | Confidence |

**Tree View (per moment):**
```
## [Moment Name]
- [Parent opportunity]
  - [Child opportunity]
    - [Grandchild]
```

**Prioritized Leaf Backlog:**
Ranked list with scores and rationale.

## Rules

- All opportunities from user perspective
- No solutions in the tree
- Keep distinct across siblings
- Prefer specific over generic
- Preserve verbatim quotes for evidence

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
