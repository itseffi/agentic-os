---
name: ost-intake
description: Normalize and collect complete Opportunity Solution Tree inputs before OST synthesis.
---

# OST Intake

Collect high-quality, normalized inputs for OST work.

## Instructions

### Step 1: Parse existing context first
- Use provided context before asking questions.

### Step 2: Collect four required fields
- `business_outcome`
- `journey_nodes_as_list` (JSON array of moments)
- `interview_transcripts_or_story_snippets`
- `constraints_or_principles` (or `None stated`)

### Step 3: Normalize quality
- Reframe solution-flavored outcomes into measurable outcomes.
- Reframe feature-like nodes into moments in time.
- Add minimal attribution to transcript snippets when possible.

### Step 4: Ask only missing critical questions
- Ask concise questions only for missing required inputs.
- Stop when all four fields are complete and clear.

## Output

- Final normalized values for all four required fields.

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
