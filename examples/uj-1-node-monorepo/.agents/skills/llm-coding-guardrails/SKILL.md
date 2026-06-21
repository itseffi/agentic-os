---
name: llm-coding-guardrails
description: Behavioral guardrails to reduce common LLM coding mistakes with a caution-first approach.
---

# LLM Coding Guardrails

Behavioral guidelines to reduce common LLM coding mistakes.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

Do not assume. Do not hide confusion. Surface tradeoffs.

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them. Do not pick silently.
- If a simpler approach exists, say so.
- If something is unclear, stop and ask.

## 2. Simplicity First

Write the minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No configurability that was not requested.
- No error handling for impossible scenarios.
- If code is substantially longer than needed, simplify it.

Quality check:
- Would a senior engineer call this overcomplicated?
- If yes, simplify.

## 3. Surgical Changes

Touch only what is necessary. Clean up only what your change affected.

When editing existing code:
- Do not improve adjacent code, comments, or formatting unless required.
- Do not refactor unrelated working code.
- Match existing style unless asked to change it.
- If you notice unrelated dead code, mention it. Do not delete it.

When your changes create orphans:
- Remove imports/variables/functions made unused by your own change.
- Do not remove pre-existing dead code unless asked.

Test:
- Every changed line must map directly to the request.

## 4. Goal-Driven Execution

Define success criteria and iterate until verified.

Turn requests into verifiable goals:
- "Add validation" -> "Write tests for invalid inputs, then make them pass"
- "Fix the bug" -> "Write a test that reproduces it, then make it pass"
- "Refactor X" -> "Ensure tests pass before and after"

For multi-step tasks, state a brief plan with checks:
1. [Step] -> verify: [check]
2. [Step] -> verify: [check]
3. [Step] -> verify: [check]

Strong success criteria support independent iteration.
Weak criteria (for example, "make it work") require repeated clarification.

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
